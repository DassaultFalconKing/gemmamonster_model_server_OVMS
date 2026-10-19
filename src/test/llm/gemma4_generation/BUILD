load("//:common_settings.bzl", "COMMON_LOCAL_DEFINES", "COMMON_STATIC_LIBS_LINKOPTS", "COPTS_TESTS")

cc_test(
    name = "gemma4_native_reader_test",
    srcs = ["gemma4_native_reader_test.cpp"],
    deps = ["@com_google_googletest//:gtest_main", "//src/llm:output_parsers"],
    copts = COPTS_TESTS,
    local_defines = COMMON_LOCAL_DEFINES,
    linkopts = COMMON_STATIC_LIBS_LINKOPTS,
    linkstatic = 1,
)
