import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Allow importing the existing semantic-grounding validator
sys.path.append(str(PROJECT_ROOT / "src" / "validation"))

import validate_semantic_grounding as validator


CANONICAL_PATH = PROJECT_ROOT / "outputs" / "canonical_transcript.json"
OUTPUT_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "adversarial_semantic_grounding_results.json"
)


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():

    load_dotenv(PROJECT_ROOT / ".env")

    canonical_records = load_json(CANONICAL_PATH)

    transcript_index = validator.build_transcript_index(
        canonical_records
    )

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY was not found. "
            "Check your .env file."
        )

    from google import genai

    client = genai.Client(
        api_key=api_key
    )

    # ---------------------------------------------------------
    # Three adversarial cases using REAL transcript references.
    #
    # The references are valid, but the claims are intentionally
    # incorrect, materially overstated, or unsupported.
    # ---------------------------------------------------------

    cases = [
        {
            "case_id": "ADV-01",
            "failure_type": "incorrect factual detail",
            "topic": (
                "President Biden's program cancelled "
                "$50,000 of federal student loans for borrowers."
            ),
            "start_ref": "13:8",
            "end_ref": "13:10",
            "evidence_refs": [
                "13:8",
                "13:9",
                "13:10"
            ],
            "expected_result": "FAIL"
        },
        {
            "case_id": "ADV-02",
            "failure_type": "materially overstated claim",
            "topic": (
                "Ms. Yu personally wrote the CARES Act legislation."
            ),
            "start_ref": "16:7",
            "end_ref": "16:10",
            "evidence_refs": [
                "16:7",
                "16:8",
                "16:9",
                "16:10"
            ],
            "expected_result": "FAIL"
        },
        {
            "case_id": "ADV-03",
            "failure_type": "unsupported conclusion",
            "topic": (
                "Ms. Yu concluded that the PEAKS loans "
                "contained no defects."
            ),
            "start_ref": "9:15",
            "end_ref": "9:18",
            "evidence_refs": [
                "9:15",
                "9:16",
                "9:17",
                "9:18"
            ],
            "expected_result": "FAIL"
        }
    ]

    print("=== Adversarial Semantic Grounding Test ===")
    print()
    print(f"Cases: {len(cases)}")
    print()

    # Convert cases into the same topic structure expected
    # by the existing semantic-grounding validator.
    topics = []

    for case in cases:
        topics.append(
            {
                "topic": case["topic"],
                "start_ref": case["start_ref"],
                "end_ref": case["end_ref"],
                "evidence_refs": case["evidence_refs"]
            }
        )

    # Use the EXISTING validator prompt and validation logic.
    results = validator.validate_batch(
        client,
        topics,
        transcript_index
    )

    output_results = []

    for index, (case, result) in enumerate(
        zip(cases, results),
        start=1
    ):

        actual_result = result["result"]

        output_results.append(
            {
                "case_id": case["case_id"],
                "failure_type": case["failure_type"],
                "claim": case["topic"],
                "start_ref": case["start_ref"],
                "end_ref": case["end_ref"],
                "evidence_refs": case["evidence_refs"],
                "expected_result": case["expected_result"],
                "actual_result": actual_result,
                "validator_reason": result["reason"],
                "passed_adversarial_test": (
                    actual_result == case["expected_result"]
                )
            }
        )

        print(
            f"{case['case_id']}: "
            f"Expected={case['expected_result']} | "
            f"Actual={actual_result}"
        )

        print(
            f"Reason: {result['reason']}"
        )

        print()

    passed = sum(
        1
        for result in output_results
        if result["passed_adversarial_test"]
    )

    failed = len(output_results) - passed

    output = {
        "metadata": {
            "test_type": "adversarial semantic grounding",
            "validator": (
                "src/validation/"
                "validate_semantic_grounding.py"
            ),
            "canonical_transcript": (
                "outputs/canonical_transcript.json"
            ),
            "cases": len(cases),
            "adversarial_tests_passed": passed,
            "adversarial_tests_failed": failed
        },
        "results": output_results
    }

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("=== Final Summary ===")
    print(
        f"Adversarial cases: {len(cases)}"
    )
    print(
        f"Correctly rejected: {passed}"
    )
    print(
        f"Not correctly rejected: {failed}"
    )
    print()
    print(
        f"Saved to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()