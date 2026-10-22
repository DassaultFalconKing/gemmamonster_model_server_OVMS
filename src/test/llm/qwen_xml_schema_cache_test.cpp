#include <gtest/gtest.h>

#include "src/llm/io_processing/qwen3coder/tool_schema_profile.hpp"

using namespace ovms;

TEST(QwenXmlSchemaCache, OneCompileServesRepeatedArgumentChecks) {
    const char* schema =
        R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"]})";
    const auto before = qwenXmlToolSchemaCompileCount();
    const auto compiled = compileQwenXmlToolSchema(schema);
    ASSERT_TRUE(compiled);
    EXPECT_EQ(qwenXmlToolSchemaCompileCount(), before + 1);
    for (int i = 0; i < 100; ++i) {
        EXPECT_TRUE(compiled->validateArguments(R"({"city":"Paris"})"));
        EXPECT_FALSE(compiled->validateArguments("{}"));
        EXPECT_FALSE(compiled->validateArguments("[]"));
    }
    EXPECT_EQ(qwenXmlToolSchemaCompileCount(), before + 1);
    EXPECT_FALSE(static_cast<bool>(compileQwenXmlToolSchema("")));
    EXPECT_EQ(qwenXmlToolSchemaCompileCount(), before + 1);
}
