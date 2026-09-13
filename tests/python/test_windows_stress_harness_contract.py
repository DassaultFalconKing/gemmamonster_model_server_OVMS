from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "src" / "test" / "stress_test_utils.hpp"


def extract_function(text: str, name: str) -> str:
    marker = f"void {name}("
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
    raise AssertionError(f"unterminated function: {name}")


class WindowsStressHarnessContractTest(unittest.TestCase):
    def test_async_worker_does_not_call_googletest_from_worker_threads(self):
        body = extract_function(
            HEADER.read_text(encoding="utf-8"),
            "triggerCApiAsyncInferenceInALoop",
        )
        forbidden = ("ASSERT_", "EXPECT_", "::testing::Test::HasFailure")
        hits = [token for token in forbidden if token in body]
        self.assertEqual(
            [],
            hits,
            "GoogleTest assertions are unsupported from concurrent worker "
            f"threads on Windows: {hits}",
        )


if __name__ == "__main__":
    unittest.main()
