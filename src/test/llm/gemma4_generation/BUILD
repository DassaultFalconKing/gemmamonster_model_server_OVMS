load("//:common_settings.bzl", "COMMON_LOCAL_DEFINES", "COMMON_STATIC_LIBS_LINKOPTS", "COPTS_TESTS")

cc_test(
    name = "gemma4_f10_guard_test",
    srcs = ["gemma4_f10_guard_test.cpp"],
    deps = [
        "@com_google_googletest//:gtest_main",
        "//src/llm:output_parsers",
        "//third_party:genai",
        "//third_party:openvino",
    ],
    copts = COPTS_TESTS,
    local_defines = COMMON_LOCAL_DEFINES,
    linkopts = COMMON_STATIC_LIBS_LINKOPTS,
    linkstatic = 1,
)

cc_test(
    name = "gemma4_f7_contract_test",
    srcs = ["gemma4_f7_contract_test.cpp"],
    deps = [
        "@com_google_googletest//:gtest_main",
        "//src/llm:openai_completions_api_handler",
        "//src/llm:openai_responses_handler",
        "//src/llm:output_parsers",
        "//third_party:genai",
        "//third_party:openvino",
    ],
    copts = COPTS_TESTS,
    local_defines = COMMON_LOCAL_DEFINES,
    linkopts = COMMON_STATIC_LIBS_LINKOPTS,
    linkstatic = 1,
)

cc_test(
    name = "gemma4_generation_policy_test",
    srcs = ["gemma4_generation_policy_test.cpp"],
    deps = [
        "@com_google_googletest//:gtest_main",
        "//src/llm:generation_config_builders",
        "//src/llm:openai_completions_api_handler",
        "//src/llm:openai_responses_handler",
        "//third_party:genai",
    ],
    copts = COPTS_TESTS,
    local_defines = COMMON_LOCAL_DEFINES,
    linkopts = COMMON_STATIC_LIBS_LINKOPTS,
    linkstatic = 1,
)

cc_test(
    name = "gemma4_phantom_tool_call_test",
    srcs = ["gemma4_phantom_tool_call_test.cpp"],
    deps = [
        "@com_google_googletest//:gtest_main",
        "//src/llm:output_parsers",
        "//third_party:genai",
        "//third_party:openvino",
    ],
    copts = COPTS_TESTS,
    local_defines = COMMON_LOCAL_DEFINES,
    linkopts = COMMON_STATIC_LIBS_LINKOPTS,
    linkstatic = 1,
)

cc_test(
    name = "gemma4_chunk_invariance_test",
    srcs = ["gemma4_chunk_invariance_test.cpp"],
    deps = [
        "@com_google_googletest//:gtest_main",
        "//src/llm:output_parsers",
        "//third_party:genai",
        "//third_party:openvino",
    ],
    copts = COPTS_TESTS,
    local_defines = COMMON_LOCAL_DEFINES,
    linkopts = COMMON_STATIC_LIBS_LINKOPTS,
    linkstatic = 1,
)

cc_test(
    name = "gemma4_rendered_prompt_state_test",
    srcs = ["gemma4_rendered_prompt_state_test.cpp"],
    deps = [
        "@com_google_googletest//:gtest_main",
        "//src/llm:generation_config_builders",
        "//src/llm:io_processing_gemma4_rendered_prompt_state",
        "//src/llm:output_parsers",
        "//third_party:genai",
        "//third_party:openvino",
    ],
    copts = COPTS_TESTS,
    local_defines = COMMON_LOCAL_DEFINES,
    linkopts = COMMON_STATIC_LIBS_LINKOPTS,
    linkstatic = 1,
)
