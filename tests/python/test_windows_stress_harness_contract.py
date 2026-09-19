from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "test" / "c_api_stress_tests.cpp"
ENSEMBLE_SOURCE = ROOT / "src" / "test" / "ensemble_config_change_stress.cpp"


def extract_function(text: str, name: str) -> str:
    marker = f"{name}("
    name_start = text.index(marker)
    start = text.rfind("\n", 0, name_start) + 1
    body_start = text.index("{", name_start)
    depth = 0
    for index in range(body_start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise AssertionError(f"unterminated function: {name}")


def extract_class(text: str, name: str) -> str:
    marker = f"class {name} "
    start = text.index(marker)
    body_start = text.index("{", start)
    depth = 0
    for index in range(body_start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise AssertionError(f"unterminated class: {name}")


class WindowsStressHarnessContractTest(unittest.TestCase):
    def test_async_worker_does_not_call_googletest_from_worker_threads(self):
        text = SOURCE.read_text(encoding="utf-8")
        body = extract_function(text, "runWindowsSafeAsyncWorker")
        forbidden = ("ASSERT_", "EXPECT_", "::testing::Test::HasFailure")
        hits = [token for token in forbidden if token in body]
        self.assertEqual(
            [],
            hits,
            "GoogleTest assertions are unsupported from concurrent worker "
            f"threads on Windows: {hits}",
        )

    def test_async_stress_tests_do_not_use_legacy_worker(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn(
            "&ConfigChangeStressTest::triggerCApiAsyncInferenceInALoop",
            text,
        )
        self.assertGreaterEqual(text.count("runWindowsSafeAsyncStress("), 5)

    def test_capi_status_helper_releases_owned_statuses(self):
        text = SOURCE.read_text(encoding="utf-8")
        body = extract_function(text, "consumeCapiStatus")
        self.assertIn("OVMS_StatusDelete(status);", body)
        self.assertIn("OVMS_StatusDelete(codeStatus);", body)

    def test_windows_cvs176244_capi_skips_use_fixture_setup(self):
        text = SOURCE.read_text(encoding="utf-8")
        for fixture in (
            "StressCapiConfigChanges",
            "ConfigChangeStressTestSingleModel",
        ):
            with self.subTest(fixture=fixture):
                body = extract_class(text, fixture)
                self.assertIn("void SetUp() override", body)
                self.assertIn("GTEST_SKIP()", body)
                self.assertNotIn("SetUpTestSuite", body)

    def test_windows_cvs176244_mediapipe_skips_use_fixture_setup(self):
        text = ENSEMBLE_SOURCE.read_text(encoding="utf-8")
        base = extract_class(text, "StressPipelineConfigChanges")
        self.assertNotIn("SetUpTestSuite", base)
        for fixture in (
            "StressMediapipeChanges",
            "StressMediapipeQueueChanges",
        ):
            with self.subTest(fixture=fixture):
                body = extract_class(text, fixture)
                self.assertIn("void SetUp() override", body)
                self.assertIn("GTEST_SKIP()", body)


if __name__ == "__main__":
    unittest.main()
