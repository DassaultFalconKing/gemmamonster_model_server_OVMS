//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//*****************************************************************************

// Guards GenAiServableInitializer::loadChatTemplate when the Minja basic-render
// probe fails. The production seam reads chat_template.jinja, probes, and must
// still assign inputProcessorContext. The identity check below fails while the
// context tokenizer is default-constructed, before any method call on it.

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <utility>

#include <gtest/gtest.h>
#include <openvino/genai/tokenizer.hpp>

#include "../../llm/io_processing/input_processor.hpp"
#include "../../llm/io_processing/input_request.hpp"
#include "../../llm/servable_initializer.hpp"
#include "../../status.hpp"
#include "../platform_utils.hpp"
#include "../test_with_temp_dir.hpp"

using namespace ovms;

namespace {

// Same Minja parse class as the on-disk Gemma template: adjacent string literals
// inside a call. minja throws std::runtime_error "Expected closing parenthesis in call args".
constexpr const char* kInvalidAdjacentLiterals =
    "{{ raise_exception(\"chat_template: tool_calls[].function.arguments must be a \" "
    "\"JSON object (mapping), not a string. Deserialize arguments \" "
    "\"before passing to the template.\") }}";

constexpr const char* kValidMinjaTemplate =
    "{%- for message in messages -%}{{ message.role }}: {{ message.content }}\n{%- endfor -%}";

constexpr const char* kChatUserContent = "f005-context-token";
constexpr const char* kCompletionPrompt = "f005 completion only";

const char* kTokenizerFiles[] = {
    "openvino_tokenizer.xml",
    "openvino_tokenizer.bin",
    "openvino_detokenizer.xml",
    "openvino_detokenizer.bin",
};

absl::Status ProcessChat(InputProcessorContext& context) {
    InputRequest request;
    ov::genai::ChatHistory history;
    history.push_back(ov::genai::JsonContainer::from_json_string(
        std::string("{\"role\":\"user\",\"content\":\"") + kChatUserContent + "\"}"));
    request.input = std::move(history);
    InputProcessor processor(context, request);
    return processor.process(request);
}

absl::Status ProcessCompletion(InputProcessorContext& context, InputRequest& request) {
    request.input = std::string(kCompletionPrompt);
    InputProcessor processor(context, request);
    return processor.process(request);
}

}  // namespace

class InvalidTemplateContextSafetyTest : public TestWithTempDir {
protected:
    void CopyCpuTokenizerFixture() {
        const char* configured = std::getenv("OVMS_TEST_TOKENIZER_PATH");
        const std::string source = configured && *configured ? configured : getGenericFullPathForSrcTest("/ovms/src/test/llm_testing/facebook/opt-125m");
        const std::filesystem::path sourceDir(source);
        ASSERT_TRUE(std::filesystem::exists(sourceDir / "openvino_tokenizer.xml"))
            << "CPU tokenizer fixture missing at " << source
            << ". Prepare with ovms/windows_prepare_llm_models.bat. This test loads the tokenizer IR only.";
        for (const char* name : kTokenizerFiles) {
            std::filesystem::copy_file(sourceDir / name,
                std::filesystem::path(directoryPath) / name,
                std::filesystem::copy_options::overwrite_existing);
        }
    }

    void WriteChatTemplateFile(const std::string& contents) {
        std::ofstream out(std::filesystem::path(directoryPath) / "chat_template.jinja", std::ios::binary);
        ASSERT_TRUE(out.is_open());
        out << contents;
    }

    std::shared_ptr<GenAiServableProperties> LoadMinjaProperties() {
        auto properties = std::make_shared<GenAiServableProperties>();
        properties->chatTemplateEngine = ChatTemplateEngine::MINJA;
        properties->tokenizer = ov::genai::Tokenizer(directoryPath);
        return properties;
    }

    // Fails on the pre-fix early return without calling methods on the default tokenizer.
    void ExpectInitializedContext(const std::shared_ptr<GenAiServableProperties>& properties) {
        const ov::genai::Tokenizer defaultTokenizer;
        ASSERT_NE(properties->inputProcessorContext.tokenizer, defaultTokenizer)
            << "inputProcessorContext.tokenizer is still default-constructed";
        ASSERT_EQ(properties->inputProcessorContext.tokenizer, properties->tokenizer);
        if (HasFatalFailure()) {
            return;
        }
    }
};

TEST_F(InvalidTemplateContextSafetyTest, InvalidMinjaProbeInitializesContextAndRejectsChat) {
    CopyCpuTokenizerFixture();
    if (HasFatalFailure()) {
        return;
    }
    WriteChatTemplateFile(kInvalidAdjacentLiterals);
    if (HasFatalFailure()) {
        return;
    }

    auto properties = LoadMinjaProperties();
    const auto status = GenAiServableInitializer::loadChatTemplate(properties, directoryPath);
    ASSERT_TRUE(status.ok()) << status.string();
    EXPECT_EQ(properties->chatTemplateEngine, ChatTemplateEngine::MINJA);

    ExpectInitializedContext(properties);
    if (HasFatalFailure()) {
        return;
    }

    EXPECT_EQ(properties->tokenizer.get_chat_template(), kInvalidAdjacentLiterals);
    EXPECT_EQ(properties->inputProcessorContext.templateProcessor, nullptr);

    const absl::Status chatStatus = ProcessChat(properties->inputProcessorContext);
    EXPECT_EQ(chatStatus.code(), absl::StatusCode::kInvalidArgument);
    EXPECT_NE(std::string(chatStatus.message()).find("Failed to apply chat template"), std::string::npos) << chatStatus.ToString();

    InputRequest completion;
    const absl::Status completionStatus = ProcessCompletion(properties->inputProcessorContext, completion);
    EXPECT_TRUE(completionStatus.ok()) << completionStatus.ToString();
    EXPECT_GT(completion.inputIds.get_size(), 0);
}

TEST_F(InvalidTemplateContextSafetyTest, ValidMinjaTemplatePopulatesContextAndRendersChat) {
    CopyCpuTokenizerFixture();
    if (HasFatalFailure()) {
        return;
    }
    WriteChatTemplateFile(kValidMinjaTemplate);
    if (HasFatalFailure()) {
        return;
    }

    auto properties = LoadMinjaProperties();
    const auto status = GenAiServableInitializer::loadChatTemplate(properties, directoryPath);
    ASSERT_TRUE(status.ok()) << status.string();

    ExpectInitializedContext(properties);
    if (HasFatalFailure()) {
        return;
    }
    EXPECT_EQ(properties->tokenizer.get_chat_template(), kValidMinjaTemplate);
    EXPECT_EQ(properties->inputProcessorContext.templateProcessor, nullptr);

    InputRequest request;
    ov::genai::ChatHistory history;
    history.push_back(ov::genai::JsonContainer::from_json_string(
        std::string("{\"role\":\"user\",\"content\":\"") + kChatUserContent + "\"}"));
    request.input = std::move(history);
    InputProcessor processor(properties->inputProcessorContext, request);
    const absl::Status chatStatus = processor.process(request);
    EXPECT_TRUE(chatStatus.ok()) << chatStatus.ToString();
    EXPECT_NE(request.promptText.find(kChatUserContent), std::string::npos) << request.promptText;
}

TEST_F(InvalidTemplateContextSafetyTest, EmptyTemplateCompletionOnlyContextStaysInitialized) {
    CopyCpuTokenizerFixture();
    if (HasFatalFailure()) {
        return;
    }

    auto properties = LoadMinjaProperties();
    properties->tokenizer.set_chat_template("");
    const auto status = GenAiServableInitializer::loadChatTemplate(properties, directoryPath);
    ASSERT_TRUE(status.ok()) << status.string();
    EXPECT_TRUE(properties->tokenizer.get_chat_template().empty());

    ExpectInitializedContext(properties);
    if (HasFatalFailure()) {
        return;
    }

    const absl::Status chatStatus = ProcessChat(properties->inputProcessorContext);
    EXPECT_EQ(chatStatus.code(), absl::StatusCode::kInvalidArgument) << chatStatus.ToString();

    InputRequest completion;
    const absl::Status completionStatus = ProcessCompletion(properties->inputProcessorContext, completion);
    EXPECT_TRUE(completionStatus.ok()) << completionStatus.ToString();
    EXPECT_GT(completion.inputIds.get_size(), 0);
}
