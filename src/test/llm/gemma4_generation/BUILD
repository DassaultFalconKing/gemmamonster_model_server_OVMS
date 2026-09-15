load("//:common_settings.bzl", "COMMON_LOCAL_DEFINES", "COMMON_STATIC_LIBS_LINKOPTS", "COPTS_TESTS")

cc_test(
    name = "gemma4_generation_policy_test",
    srcs = ["gemma4_generation_policy_test.cpp"],
    deps = [
        "@com_google_googletest//:gtest_main",
        "//src/llm:generation_config_builders",
        "//src/llm:openai_completions_api_handler",
        "//third_party:genai",
    ],
    copts = COPTS_TESTS,
    local_defines = COMMON_LOCAL_DEFINES,
    linkopts = COMMON_STATIC_LIBS_LINKOPTS,
    linkstatic = 1,
)
