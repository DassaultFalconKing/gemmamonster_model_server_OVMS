from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "test" / "c_api_stress_tests.cpp"


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


if __name__ == "__main__":
    unittest.main()
