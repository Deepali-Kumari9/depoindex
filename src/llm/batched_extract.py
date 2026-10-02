import json
import os
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(
    api_key=api_key,
    http_options={"timeout": 60000}
)

INPUT_PATH = os.getenv(
    "DEPOINDEX_INPUT_PATH",
    "outputs/transcript_chunks.json"
)

OUTPUT_PATH = os.getenv(
    "DEPOINDEX_OUTPUT_PATH",
    "outputs/batched_topics.json"
)

# 5 original chunks per Gemini request
BATCH_SIZE = 5


def load_chunks(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def build_valid_reference_set(chunks):
    """
    Build a set containing every real page:line reference
    present in the canonical transcript.

    This is used only for validation.

    IMPORTANT:
    We do NOT modify or repair an invalid LLM reference.
    """

    valid_refs = set()

    for chunk in chunks:
        for record in chunk["records"]:
            valid_refs.add(record["source_ref"])

    return valid_refs


def validate_ref_format(ref):
    """
    Check whether a reference has the basic page:line format.

    Examples:
        25:8  -> valid format
        69:0  -> invalid
        abc   -> invalid
    """

    if not ref or ":" not in ref:
        return False

    page_str, line_str = ref.split(":", 1)

    try:
        page = int(page_str)
        line = int(line_str)
    except ValueError:
        return False

    # Page and transcript line numbers start from 1.
    return page > 0 and line > 0


def validate_topic_references(result, valid_refs):
    """
    Validate all provenance references produced by the LLM.

    Invalid references are reported instead of silently repaired.
    """

    errors = []

    topics = result.get("topics", [])

    if not isinstance(topics, list):
        errors.append(
            "'topics' must be a list"
        )
        return errors

    for topic_index, topic in enumerate(topics, start=1):

        # -----------------------------
        # Validate start_ref
        # -----------------------------
        start_ref = topic.get("start_ref")

        if not validate_ref_format(start_ref):
            errors.append(
                f"Topic {topic_index}: "
                f"invalid start_ref '{start_ref}'"
            )
        elif start_ref not in valid_refs:
            errors.append(
                f"Topic {topic_index}: "
                f"start_ref '{start_ref}' "
                f"does not exist in transcript"
            )

        # -----------------------------
        # Validate end_ref
        # -----------------------------
        end_ref = topic.get("end_ref")

        if not validate_ref_format(end_ref):
            errors.append(
                f"Topic {topic_index}: "
                f"invalid end_ref '{end_ref}'"
            )
        elif end_ref not in valid_refs:
            errors.append(
                f"Topic {topic_index}: "
                f"end_ref '{end_ref}' "
                f"does not exist in transcript"
            )

        # -----------------------------
        # Validate evidence_refs
        # -----------------------------
        evidence_refs = topic.get(
            "evidence_refs",
            []
        )

        if not isinstance(evidence_refs, list):
            errors.append(
                f"Topic {topic_index}: "
                "'evidence_refs' must be a list"
            )
            continue

        for ref in evidence_refs:

            if not validate_ref_format(ref):
                errors.append(
                    f"Topic {topic_index}: "
                    f"invalid evidence_ref '{ref}'"
                )

            elif ref not in valid_refs:
                errors.append(
                    f"Topic {topic_index}: "
                    f"evidence_ref '{ref}' "
                    f"does not exist in transcript"
                )

    return errors


def save_results(results, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False
        )


def build_prompt(chunks):
    sections = []

    for chunk in chunks:
        transcript_text = "\n".join(
            f"{record['source_ref']} | {record['semantic_text']}"
            for record in chunk["records"]
        )

        sections.append(
            f"===== CHUNK {chunk['chunk_id']} "
            f"({chunk['start_ref']} to {chunk['end_ref']}) =====\n"
            f"{transcript_text}"
        )

    combined_transcript = "\n\n".join(sections)

    return f"""
You are analyzing a legal deposition transcript for a topic index.

The transcript is divided into several consecutive chunks.
Each transcript line has an exact page:line reference.

Your task is to identify meaningful topics discussed across the supplied
chunks.

IMPORTANT PROVENANCE RULES:

1. Use only the supplied transcript.
2. Do not invent information.
3. Every start_ref and end_ref MUST be an exact page:line reference
   appearing in the supplied transcript.
4. Every evidence_ref MUST be an exact page:line reference appearing
   in the supplied transcript.
5. Preserve the actual boundaries of the discussion.
6. Do not extend a topic into unrelated discussion.
7. If a topic meaningfully reappears after another topic, create a
   separate topic entry and use related_to to link it to the earlier
   topic when appropriate.
8. Do not create duplicate topics merely because a chunk boundary occurs.
9. Topics may begin in one chunk and end in another.
10. Use the page:line references to determine boundaries, not chunk numbers.
11. NEVER use a page:0 reference.
12. If you cannot identify a valid existing page:line reference,
    do not invent or approximate one.

Return ONLY valid JSON.

Required format:

{{
  "topics": [
    {{
      "topic": "short meaningful topic label",
      "start_ref": "page:line",
      "end_ref": "page:line",
      "evidence_refs": ["page:line", "page:line"],
      "related_to": []
    }}
  ]
}}

If a topic is a continuation or meaningful re-entry of an earlier topic,
use the earlier topic's index in related_to, for example:

"related_to": [2]

Otherwise use:

"related_to": []

Do not include any explanation outside the JSON.

TRANSCRIPT:

{combined_transcript}
"""


def clean_json_response(result):
    result = result.strip()

    if result.startswith("```json"):
        result = result[len("```json"):].strip()

    if result.startswith("```"):
        result = result[3:].strip()

    if result.endswith("```"):
        result = result[:-3].strip()

    return json.loads(result)


def extract_batch(chunks, valid_refs):
    prompt = build_prompt(chunks)

    max_retries = 3
    retry_delays = [20, 40, 60]

    last_validation_errors = []

    for attempt in range(max_retries):
        try:

            # ---------------------------------------
            # If a previous attempt produced invalid
            # provenance, tell the model exactly what
            # needs to be corrected.
            # ---------------------------------------
            retry_prompt = prompt

            if last_validation_errors:
                retry_prompt += f"""

IMPORTANT CORRECTION FROM PREVIOUS ATTEMPT:

The previous response contained invalid provenance references.

The following references were invalid:

{chr(10).join(last_validation_errors)}

Generate the JSON again.

Do NOT repair these references yourself.
Use only exact page:line references that actually
appear in the supplied transcript.

Return ONLY valid JSON.
"""

            interaction = client.interactions.create(
                model="gemini-3.5-flash-lite",
                input=retry_prompt
            )

            result = clean_json_response(
                interaction.output_text
            )

            # ---------------------------------------
            # Validate the ORIGINAL LLM output.
            #
            # IMPORTANT:
            # We do NOT normalize or silently repair
            # invalid references.
            # ---------------------------------------
            validation_errors = validate_topic_references(
                result,
                valid_refs
            )

            if validation_errors:

                last_validation_errors = validation_errors

                if attempt == max_retries - 1:
                    raise ValueError(
                        "LLM produced invalid provenance "
                        "references after all retries:\n"
                        + "\n".join(validation_errors)
                    )

                print(
                    f"Invalid provenance detected "
                    f"(attempt {attempt + 1}/{max_retries}):",
                    flush=True
                )

                for error in validation_errors:
                    print(
                        f"  - {error}",
                        flush=True
                    )

                print(
                    f"Retrying after "
                    f"{retry_delays[attempt]} seconds...",
                    flush=True
                )

                time.sleep(
                    retry_delays[attempt]
                )

                continue

            # ---------------------------------------
            # Only validated output reaches here.
            # ---------------------------------------
            return result

        except ValueError:
            # Validation errors are handled above.
            # Re-raise only after final retry.
            if attempt == max_retries - 1:
                raise

        except Exception as error:

            if attempt == max_retries - 1:
                raise

            print(
                f"Request failed "
                f"(attempt {attempt + 1}/{max_retries}): "
                f"{error}",
                flush=True
            )

            print(
                f"Waiting {retry_delays[attempt]} "
                f"seconds before retry...",
                flush=True
            )

            time.sleep(
                retry_delays[attempt]
            )


def main():

    chunks = load_chunks(INPUT_PATH)

    # Build the set of REAL references from the
    # canonical transcript.
    #
    # This is used for validation only.
    valid_refs = build_valid_reference_set(
        chunks
    )

    all_results = []

    total_batches = (
        len(chunks) + BATCH_SIZE - 1
    ) // BATCH_SIZE

    print(
        f"Total chunks: {len(chunks)}"
    )

    print(
        f"Batch size: {BATCH_SIZE}"
    )

    print(
        f"Total Gemini requests: {total_batches}"
    )

    print()

    for start in range(
        0,
        len(chunks),
        BATCH_SIZE
    ):

        batch = chunks[
            start:start + BATCH_SIZE
        ]

        batch_number = (
            start // BATCH_SIZE
        ) + 1

        print(
            f"Processing batch "
            f"{batch_number}/{total_batches} "
            f"(chunks "
            f"{batch[0]['chunk_id']}-"
            f"{batch[-1]['chunk_id']})...",
            flush=True
        )

        try:

            result = extract_batch(
                batch,
                valid_refs
            )

            batch_result = {
                "batch_id": batch_number,

                "chunk_ids": [
                    chunk["chunk_id"]
                    for chunk in batch
                ],

                "start_ref": batch[0]["start_ref"],

                "end_ref": batch[-1]["end_ref"],

                "topics": result.get(
                    "topics",
                    []
                )
            }

            all_results.append(
                batch_result
            )

            save_results(
                all_results,
                OUTPUT_PATH
            )

            print(
                f"Completed batch "
                f"{batch_number}: "
                f"{len(batch_result['topics'])} topics"
            )

        except Exception as error:

            print(
                f"Error in batch "
                f"{batch_number}: {error}",
                flush=True
            )

            error_result = {
                "batch_id": batch_number,

                "chunk_ids": [
                    chunk["chunk_id"]
                    for chunk in batch
                ],

                "start_ref": batch[0]["start_ref"],

                "end_ref": batch[-1]["end_ref"],

                "topics": [],

                "error": str(error)
            }

            all_results.append(
                error_result
            )

            save_results(
                all_results,
                OUTPUT_PATH
            )

        # Small delay between requests
        time.sleep(2)

    print()

    print(
        f"Saved batched results to: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()