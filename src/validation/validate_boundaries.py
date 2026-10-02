import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


BASE_DIR = Path(__file__).resolve().parents[2]

CANONICAL_PATH = BASE_DIR / "outputs" / "canonical_transcript.json"
TOPICS_PATH = BASE_DIR / "outputs" / "refined_topics.json"
OUTPUT_PATH = BASE_DIR / "outputs" / "boundary_validation.json"

MODEL_NAME = "gemini-3.5-flash-lite"

CONTEXT_SIZE = 5
BATCH_SIZE = 5

MAX_RETRIES = 3
RETRY_DELAYS = [40, 60, 90]


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def ref_to_position(ref):
    """
    Convert a source reference such as 71:15 into
    a comparable numeric position.
    """
    page, line = ref.split(":")
    return int(page), int(line)


def is_before_or_equal(ref_a, ref_b):
    return ref_to_position(ref_a) <= ref_to_position(ref_b)


def ranges_overlap(topic_a, topic_b):
    """
    Check whether two topic ranges overlap.

    Example:
        Topic A: 71:15 -> 71:22
        Topic B: 71:21 -> 73:13

    These ranges overlap because B starts before A ends.
    """

    a_start = ref_to_position(topic_a["start_ref"])
    a_end = ref_to_position(topic_a["end_ref"])

    b_start = ref_to_position(topic_b["start_ref"])
    b_end = ref_to_position(topic_b["end_ref"])

    return a_start <= b_end and b_start <= a_end


def detect_structural_boundary_errors(topics):
    """
    Deterministic checks that do not depend on the LLM.

    Checks:
    1. Invalid start/end reference format.
    2. Start reference occurring after end reference.
    3. Overlap between topic ranges.
    """

    errors = []

    for index, topic in enumerate(topics, start=1):
        topic_id = topic.get("topic_id", index)
        topic_name = topic.get("topic", f"Topic {topic_id}")

        start_ref = topic.get("start_ref")
        end_ref = topic.get("end_ref")

        if not start_ref or not end_ref:
            errors.append({
                "type": "INVALID_BOUNDARY",
                "topic_id": topic_id,
                "topic": topic_name,
                "reason": "Missing start_ref or end_ref."
            })
            continue

        try:
            start_position = ref_to_position(start_ref)
            end_position = ref_to_position(end_ref)
        except Exception:
            errors.append({
                "type": "INVALID_BOUNDARY",
                "topic_id": topic_id,
                "topic": topic_name,
                "reason": (
                    f"Invalid boundary reference format: "
                    f"{start_ref} -> {end_ref}"
                )
            })
            continue

        if start_position > end_position:
            errors.append({
                "type": "INVALID_BOUNDARY_ORDER",
                "topic_id": topic_id,
                "topic": topic_name,
                "reason": (
                    f"Start {start_ref} occurs after "
                    f"end {end_ref}."
                )
            })

    # Check every pair of topics for overlapping ranges.
    for i in range(len(topics)):
        for j in range(i + 1, len(topics)):
            topic_a = topics[i]
            topic_b = topics[j]

            if ranges_overlap(topic_a, topic_b):
                errors.append({
                    "type": "TOPIC_OVERLAP",
                    "topic_id": topic_a.get("topic_id"),
                    "topic": topic_a.get("topic"),
                    "overlaps_with_topic_id": topic_b.get(
                        "topic_id"
                    ),
                    "overlaps_with_topic": topic_b.get(
                        "topic"
                    ),
                    "range_a": (
                        f"{topic_a['start_ref']} -> "
                        f"{topic_a['end_ref']}"
                    ),
                    "range_b": (
                        f"{topic_b['start_ref']} -> "
                        f"{topic_b['end_ref']}"
                    ),
                    "reason": (
                        "Two topic ranges cover the same "
                        "transcript region."
                    )
                })

    return errors


def get_context(records, ref, direction):
    ref_to_index = {
        record["source_ref"]: index
        for index, record in enumerate(records)
    }

    if ref not in ref_to_index:
        return []

    index = ref_to_index[ref]

    if direction == "start":
        start = index
        end = min(len(records), index + CONTEXT_SIZE)
    else:
        start = max(0, index - CONTEXT_SIZE + 1)
        end = index + 1

    return records[start:end]


def format_context(records):
    lines = []

    for record in records:
        lines.append(
            f"{record['source_ref']} | {record['text']}"
        )

    return "\n".join(lines)


def build_prompt(topics, records):
    topic_blocks = []

    for topic in topics:
        start_ref = topic["start_ref"]
        end_ref = topic["end_ref"]

        start_context = get_context(
            records,
            start_ref,
            "start"
        )

        end_context = get_context(
            records,
            end_ref,
            "end"
        )

        topic_blocks.append(
            f"""
TOPIC_ID: {topic.get("topic_id")}
TOPIC: {topic["topic"]}

PROPOSED START: {start_ref}
START CONTEXT:
{format_context(start_context)}

PROPOSED END: {end_ref}
END CONTEXT:
{format_context(end_context)}
"""
        )

    return f"""
You are validating topic boundaries extracted from a legal
deposition transcript.

The topic label and proposed start/end references were produced
by an LLM. Do NOT assume that they are correct.

For each topic:

1. Check whether the proposed START reference is a reasonable
   beginning of the stated topic.

2. Check whether the proposed END reference is a reasonable
   ending of the stated topic.

3. Check whether the boundary cuts through another topic or
   discussion.

4. Check whether the surrounding transcript suggests that the
   topic starts earlier or ends later.

5. Do not invent transcript content.

Return ONLY valid JSON:

{{
  "results": [
    {{
      "topic_id": 1,
      "boundary_result": "PASS",
      "start_result": "PASS",
      "end_result": "PASS",
      "reason": "Short explanation"
    }}
  ]
}}

Allowed values:

- boundary_result: PASS or FAIL
- start_result: PASS or FAIL
- end_result: PASS or FAIL

Use FAIL when the proposed boundary is clearly inappropriate.

Keep the reason concise and grounded only in the supplied transcript.

Topics to validate:
{"".join(topic_blocks)}
"""


def validate_batch(client, topics, records):
    prompt = build_prompt(topics, records)

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={
                    "temperature": 0,
                    "response_mime_type": "application/json",
                },
            )

            data = json.loads(response.text)

            if "results" not in data:
                raise ValueError(
                    "Gemini response does not contain 'results'."
                )

            return data["results"]

        except Exception as error:
            print(
                f"Boundary validation attempt "
                f"{attempt + 1}/{MAX_RETRIES} failed: {error}"
            )

            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                print(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)

    raise RuntimeError(
        "Boundary validation failed after all retries."
    )


def main():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not found. "
            "Add it to the .env file."
        )

    client = genai.Client(api_key=api_key)

    canonical_records = load_json(CANONICAL_PATH)

    refined_data = load_json(TOPICS_PATH)
    topics = refined_data["topics"]

    print("=== DepoIndex Boundary Validation ===")
    print()
    print(
        f"Canonical transcript records: "
        f"{len(canonical_records)}"
    )
    print(f"Topics available: {len(topics)}")
    print()

    # ---------------------------------------------------------
    # STEP 1: Deterministic structural boundary validation
    # ---------------------------------------------------------

    structural_errors = detect_structural_boundary_errors(
        topics
    )

    overlap_errors = [
        error
        for error in structural_errors
        if error["type"] == "TOPIC_OVERLAP"
    ]

    invalid_boundary_errors = [
        error
        for error in structural_errors
        if error["type"] != "TOPIC_OVERLAP"
    ]

    print(
        f"Structural boundary errors: "
        f"{len(structural_errors)}"
    )

    print(
        f"Topic overlaps detected: "
        f"{len(overlap_errors)}"
    )

    # ---------------------------------------------------------
    # STEP 2: LLM-assisted semantic boundary validation
    # ---------------------------------------------------------

    all_results = []

    for batch_start in range(0, len(topics), BATCH_SIZE):

        batch = topics[
            batch_start:batch_start + BATCH_SIZE
        ]

        batch_number = (
            batch_start // BATCH_SIZE
        ) + 1

        print(
            f"Validating boundary batch {batch_number}: "
            f"{len(batch)} topics"
        )

        results = validate_batch(
            client,
            batch,
            canonical_records,
        )

        result_map = {
            result.get("topic_id"): result
            for result in results
        }

        for topic in batch:
            topic_id = topic.get("topic_id")

            result = result_map.get(topic_id)

            if result is None:
                result = {
                    "boundary_result": "FAIL",
                    "start_result": "FAIL",
                    "end_result": "FAIL",
                    "reason": (
                        "No validation result returned "
                        "by the model."
                    ),
                }

            all_results.append(
                {
                    "topic_id": topic_id,
                    "topic": topic["topic"],
                    "start_ref": topic["start_ref"],
                    "end_ref": topic["end_ref"],
                    "boundary_result": result.get(
                        "boundary_result",
                        "FAIL"
                    ),
                    "start_result": result.get(
                        "start_result",
                        "FAIL"
                    ),
                    "end_result": result.get(
                        "end_result",
                        "FAIL"
                    ),
                    "reason": result.get(
                        "reason",
                        "No reason provided."
                    ),
                }
            )

        # Incremental save.
        output = {
            "metadata": {
                "topic_count": len(topics),
                "validated_topics": len(all_results),
                "model": MODEL_NAME,
                "context_size": CONTEXT_SIZE,
                "batch_size": BATCH_SIZE,
                "structural_error_count": len(
                    structural_errors
                ),
                "overlap_count": len(overlap_errors),
            },
            "structural_errors": structural_errors,
            "results": all_results,
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

    semantic_passed = sum(
        result["boundary_result"] == "PASS"
        for result in all_results
    )

    semantic_failed = (
        len(all_results) - semantic_passed
    )

    print()
    print("=== Boundary Validation Summary ===")
    print(
        f"Topics validated: "
        f"{len(all_results)}"
    )
    print(
        f"LLM boundary checks passed: "
        f"{semantic_passed}"
    )
    print(
        f"LLM boundary checks failed: "
        f"{semantic_failed}"
    )
    print(
        f"Structural errors: "
        f"{len(structural_errors)}"
    )
    print(
        f"Topic overlaps: "
        f"{len(overlap_errors)}"
    )
    print()
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()