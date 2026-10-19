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
