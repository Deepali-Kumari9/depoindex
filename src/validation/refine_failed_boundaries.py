import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ---------------------------------------------------------
# Load .env from the project root
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH)


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

CANONICAL_PATH = PROJECT_ROOT / "outputs" / "canonical_transcript.json"
REFINED_TOPICS_PATH = PROJECT_ROOT / "outputs" / "refined_topics.json"
BOUNDARY_VALIDATION_PATH = (
    PROJECT_ROOT / "outputs" / "boundary_validation.json"
)
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "refined_topics.json"


# ---------------------------------------------------------
# Gemini configuration
# ---------------------------------------------------------

MODEL_NAME = "gemini-3.5-flash-lite"

MAX_CONTEXT_RECORDS = 15
MAX_RETRIES = 3
RETRY_DELAYS = [40, 60, 90]


# ---------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


# ---------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------

def build_ref_map(records):
    return {
        record["source_ref"]: index
        for index, record in enumerate(records)
    }


def validate_ref(ref, ref_map):
    if not isinstance(ref, str):
        return False

    if ":" not in ref:
        return False

    page, line = ref.split(":", 1)

    try:
        page = int(page)
        line = int(line)
    except ValueError:
        return False

    return (
        page > 0
        and line > 0
        and ref in ref_map
    )


# ---------------------------------------------------------
# Transcript context
# ---------------------------------------------------------

def get_context(records, ref_map, start_ref, end_ref):
    if (
        start_ref not in ref_map
        or end_ref not in ref_map
    ):
        return []

    start_index = ref_map[start_ref]
    end_index = ref_map[end_ref]

    left = max(
        0,
        start_index - MAX_CONTEXT_RECORDS
    )

    right = min(
        len(records),
        end_index + MAX_CONTEXT_RECORDS + 1
    )

    return records[left:right]


def format_context(records):
    lines = []

    for record in records:
        lines.append(
            f"{record['source_ref']} | {record['text']}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------
# Gemini boundary correction
# ---------------------------------------------------------

def ask_gemini(client, topic, context_text):

    prompt = f"""
You are correcting the boundaries of a deposition topic index.

The original transcript is authoritative.

TOPIC:
{topic["topic"]}

CURRENT START:
{topic["start_ref"]}

CURRENT END:
{topic["end_ref"]}

CURRENT EVIDENCE:
{json.dumps(topic.get("evidence_refs", []))}

TRANSCRIPT CONTEXT:
{context_text}

Your task is to determine the best semantic boundary for this topic.

Rules:

1. Choose start_ref as the FIRST transcript line that actually belongs
   to this topic.

2. Choose end_ref as the LAST transcript line that actually belongs
   to this topic.

3. Do NOT include deposition logistics, reporter interruptions,
   exhibit instructions, reading-speed instructions, or unrelated
   procedural discussion merely because they occur between substantive
   lines.

4. Do NOT remove substantive testimony that belongs to the topic.

5. Preserve the original transcript references exactly.

6. References must come ONLY from the transcript context supplied above.

7. The topic boundary must remain chronological.

8. Return ONLY valid JSON.

Required JSON:

{{
    "start_ref": "page:line",
    "end_ref": "page:line",
    "reason": "short explanation"
}}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={
            "temperature": 0,
            "response_mime_type": "application/json",
        },
    )

    return json.loads(response.text)


# ---------------------------------------------------------
# Repair one failed topic
# ---------------------------------------------------------

def repair_topic(client, topic, records, ref_map):

    context = get_context(
        records,
        ref_map,
        topic["start_ref"],
        topic["end_ref"],
    )

    if not context:
        return None

    context_text = format_context(context)

    for attempt in range(MAX_RETRIES):

        try:

            result = ask_gemini(
                client,
                topic,
                context_text,
            )

            new_start = result.get("start_ref")
            new_end = result.get("end_ref")

            if not validate_ref(
                new_start,
                ref_map
            ):
                raise ValueError(
                    f"Invalid start_ref returned: "
                    f"{new_start}"
                )

            if not validate_ref(
                new_end,
                ref_map
            ):
                raise ValueError(
                    f"Invalid end_ref returned: "
                    f"{new_end}"
                )

            if ref_map[new_start] > ref_map[new_end]:
                raise ValueError(
                    f"Invalid boundary order: "
                    f"{new_start} > {new_end}"
                )

            return {
                "start_ref": new_start,
                "end_ref": new_end,
                "reason": result.get(
                    "reason",
                    ""
                )
            }

        except Exception as error:

            print(
                f"  Attempt {attempt + 1} failed: "
                f"{error}"
            )

            if attempt < MAX_RETRIES - 1:

                delay = RETRY_DELAYS[attempt]

                print(
                    f"  Retrying after "
                    f"{delay} seconds..."
                )

                time.sleep(delay)

    return None


# ---------------------------------------------------------
# Evidence cleanup
# ---------------------------------------------------------

def update_evidence(topic, ref_map):

    start_ref = topic["start_ref"]
    end_ref = topic["end_ref"]

    if (
        start_ref not in ref_map
        or end_ref not in ref_map
    ):
        return

    start_index = ref_map[start_ref]
    end_index = ref_map[end_ref]

    evidence = topic.get(
        "evidence_refs",
        []
    )

    if not isinstance(evidence, list):
        evidence = []

    topic["evidence_refs"] = [
        ref
        for ref in evidence
        if (
            ref in ref_map
            and start_index
            <= ref_map[ref]
            <= end_index
        )
    ]


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print(
        "=== DepoIndex Failed Boundary Refinement ==="
    )
    print()

    print(
        f"Project root: {PROJECT_ROOT}"
    )

    print(
        f".env path: {ENV_PATH}"
    )

    print(
        f".env exists: {ENV_PATH.exists()}"
    )

    print()

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY was not loaded from .env"
        )

    print(
        "Gemini API key loaded successfully."
    )
    print()

    client = genai.Client(
        api_key=api_key
    )

    canonical_records = load_json(
        CANONICAL_PATH
    )

    refined_data = load_json(
        REFINED_TOPICS_PATH
    )

    boundary_data = load_json(
        BOUNDARY_VALIDATION_PATH
    )

    topics = refined_data["topics"]

    ref_map = build_ref_map(
        canonical_records
    )

    failed_topic_ids = []

    for result in boundary_data.get(
        "results",
        []
    ):

        if result.get(
            "boundary_result"
        ) == "FAIL":

            topic_id = result.get(
                "topic_id"
            )

            if topic_id is not None:
                failed_topic_ids.append(
                    topic_id
                )

    print(
        f"Topics available: {len(topics)}"
    )

    print(
        f"Failed boundaries: "
        f"{len(failed_topic_ids)}"
    )

    print()

    refinements = []

    for topic in topics:

        topic_id = topic["topic_id"]

        if topic_id not in failed_topic_ids:
            continue

        print(
            f"Refining Topic {topic_id}: "
            f"{topic['topic']}"
        )

        old_start = topic["start_ref"]
        old_end = topic["end_ref"]

        correction = repair_topic(
            client,
            topic,
            canonical_records,
            ref_map,
        )

        if correction is None:

            print(
                "  Could not refine this topic."
            )
            print()

            continue

        topic["start_ref"] = (
            correction["start_ref"]
        )

        topic["end_ref"] = (
            correction["end_ref"]
        )

        update_evidence(
            topic,
            ref_map
        )

        refinement = {
            "topic_id": topic_id,
            "topic": topic["topic"],
            "old_start_ref": old_start,
            "old_end_ref": old_end,
            "new_start_ref": correction[
                "start_ref"
            ],
            "new_end_ref": correction[
                "end_ref"
            ],
            "reason": correction[
                "reason"
            ],
        }

        refinements.append(
            refinement
        )

        print(
            f"  Start: {old_start} -> "
            f"{correction['start_ref']}"
        )

        print(
            f"  End: {old_end} -> "
            f"{correction['end_ref']}"
        )

        print(
            f"  Reason: "
            f"{correction['reason']}"
        )

        print()

    refined_data.setdefault(
        "metadata",
        {}
    )

    refined_data["metadata"][
        "failed_boundary_refinements"
    ] = refinements

    save_json(
        refined_data,
        OUTPUT_PATH
    )

    print(
        "=== Completed ==="
    )

    print(
        f"Topics refined: "
        f"{len(refinements)}"
    )

    print(
        f"Saved to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()