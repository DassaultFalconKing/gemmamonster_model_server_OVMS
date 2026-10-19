load("//:common_settings.bzl", "COMMON_LOCAL_DEFINES", "COMMON_STATIC_LIBS_LINKOPTS", "COPTS_TESTS")

cc_test(
    name = "gemma_argument_boundary_test",
    srcs = ["gemma_argument_boundary_test.cpp"],
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
    name = "history_copy_test",
    srcs = ["history_copy_test.cpp"],
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
    name = "parallel_request_test",
    srcs = ["parallel_request_test.cpp"],
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
    name = "policy_history_schema_test",
    srcs = ["policy_history_schema_test.cpp"],
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

