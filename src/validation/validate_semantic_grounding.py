import json
import os
import time

from google import genai
from dotenv import load_dotenv


CANONICAL_PATH = "outputs/canonical_transcript.json"
TOPICS_PATH = "outputs/refined_topics.json"
OUTPUT_PATH = "outputs/semantic_grounding_validation.json"

MODEL_NAME = "gemini-3.5-flash-lite"

BATCH_SIZE = 5

MAX_RETRIES = 3
RETRY_DELAYS = [40, 60, 90]


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


def build_transcript_index(records):
    return {
        record["source_ref"]: record["text"]
        for record in records
    }


def build_batch_prompt(batch, transcript_index):
    topic_blocks = []

    for index, topic in enumerate(batch, start=1):

        evidence_text = []

        for ref in topic.get("evidence_refs", []):
            if ref in transcript_index:
                evidence_text.append(
                    f"{ref} | {transcript_index[ref]}"
                )

        evidence = "\n".join(evidence_text)

        topic_blocks.append(
            f"""
TOPIC {index}

Topic:
{topic["topic"]}

Topic boundaries:
{topic["start_ref"]} to {topic["end_ref"]}

Evidence:
{evidence}
"""
        )

    topics_text = "\n".join(topic_blocks)

    return f"""
You are validating AI-generated topics from a legal deposition transcript.

For each topic, determine whether the supplied evidence substantively
supports the topic.

Rules:
1. Return PASS only if the evidence substantively supports the topic.
2. Return FAIL if the topic is unsupported, misleading, or unrelated
   to the supplied evidence.
3. Do not judge whether the topic name is perfectly written.
4. Use ONLY the supplied evidence.
5. Give a short reason.
6. Return exactly one result for every topic.
7. Keep the topic number unchanged.

{topics_text}

Return JSON only in this exact structure:

{{
  "results": [
    {{
      "topic_number": 1,
      "result": "PASS",
      "reason": "short explanation"
    }},
    {{
      "topic_number": 2,
      "result": "FAIL",
      "reason": "short explanation"
    }}
  ]
}}
"""


def parse_validator_response(response_text):
    text = response_text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)

        if not isinstance(result, dict):
            raise ValueError(
                "Validator response is not a JSON object."
            )

        if "results" not in result:
            raise ValueError(
                "Validator response is missing results."
            )

        if not isinstance(result["results"], list):
            raise ValueError(
                "Validator results must be a list."
            )

        for item in result["results"]:

            if not isinstance(item, dict):
                raise ValueError(
                    "Invalid result item."
                )

            if item.get("result") not in {"PASS", "FAIL"}:
                raise ValueError(
                    "Result must be PASS or FAIL."
                )

            if "topic_number" not in item:
                raise ValueError(
                    "Missing topic_number."
                )

            if "reason" not in item:
                raise ValueError(
                    "Missing reason."
                )

        return result

    except (json.JSONDecodeError, ValueError) as error:

        return {
            "results": [],
            "error": f"Invalid validator JSON: {error}"
        }


def validate_batch(
    client,
    batch,
    transcript_index
):
    prompt = build_batch_prompt(
        batch,
        transcript_index
    )

    for attempt in range(MAX_RETRIES):

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            result = parse_validator_response(
                response.text
            )

            if len(result.get("results", [])) != len(batch):
                raise ValueError(
                    "Validator returned an incorrect "
                    "number of topic results."
                )

            return result["results"]

        except Exception as error:

            print(
                f"Batch request failed "
                f"(attempt {attempt + 1}/{MAX_RETRIES}):"
            )

            print(error)
            print()

            if attempt < MAX_RETRIES - 1:

                delay = RETRY_DELAYS[attempt]

                print(
                    f"Waiting {delay} seconds before retry..."
                )

                time.sleep(delay)

            else:

                raise RuntimeError(
                    "Semantic validation batch failed "
                    "after all retries."
                ) from error


def load_previous_results():

    if not os.path.exists(OUTPUT_PATH):
        return {}

    try:
        data = load_json(OUTPUT_PATH)

        if isinstance(data, dict):
            return data.get("results", {})

    except Exception:
        print(
            "Warning: existing validation file "
            "could not be read. Starting fresh."
        )

    return {}


def main():

    load_dotenv()

    canonical_records = load_json(
        CANONICAL_PATH
    )

    topics = load_json(
        TOPICS_PATH
    )["topics"]

    transcript_index = build_transcript_index(
        canonical_records
    )

    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY was not found. "
            "Check your .env file."
        )

    client = genai.Client(
        api_key=api_key
    )

    print(
        "=== Semantic Grounding Validation ==="
    )

    print(
        f"Topics available: {len(topics)}"
    )

    print(
        f"Batch size: {BATCH_SIZE}"
    )

    print()

    # IMPORTANT:
    # The previous run saved incorrect batch-local
    # topic numbers (1-5 repeatedly).
    #
    # Therefore we intentionally start fresh here.
    results = {}

    total_batches = (
        len(topics) + BATCH_SIZE - 1
    ) // BATCH_SIZE

    for batch_number, start in enumerate(
        range(0, len(topics), BATCH_SIZE),
        start=1
    ):

        batch = topics[
            start:start + BATCH_SIZE
        ]

        print(
            f"Checking batch "
            f"{batch_number}/{total_batches}"
        )

        print(
            f"Topics "
            f"{start + 1}-{start + len(batch)}"
        )

        print()

        batch_results = validate_batch(
            client,
            batch,
            transcript_index
        )

        for item in batch_results:

            # Gemini gives a number local to the batch:
            # 1, 2, 3, 4, 5
            local_number = int(
                item["topic_number"]
            )

            # Convert it to the actual global topic number.
            global_number = (
                start + local_number
            )

            if global_number < 1:
                continue

            if global_number > len(topics):
                continue

            topic = topics[
                global_number - 1
            ]

            results[str(global_number)] = {
                "topic_number": global_number,
                "topic": topic["topic"],
                "start_ref": topic["start_ref"],
                "end_ref": topic["end_ref"],
                "evidence_refs": topic.get(
                    "evidence_refs",
                    []
                ),
                "result": item["result"],
                "reason": item["reason"]
            }

            print(
                f"Topic {global_number}: "
                f"{item['result']}"
            )

            print(
                f"Reason: {item['reason']}"
            )

        print()

        # Save after every batch.
        output_data = {
            "metadata": {
                "model": MODEL_NAME,
                "batch_size": BATCH_SIZE,
                "topics_available": len(topics),
                "topics_validated": len(results)
            },
            "results": results
        }

        save_json(
            OUTPUT_PATH,
            output_data
        )

        print(
            f"Saved progress: "
            f"{len(results)}/{len(topics)} topics"
        )

        print()

    passed = 0
    failed = 0

    for result in results.values():

        if result["result"] == "PASS":
            passed += 1

        elif result["result"] == "FAIL":
            failed += 1

    print(
        "=== Final Summary ==="
    )

    print(
        f"Topics available: {len(topics)}"
    )

    print(
        f"Topics validated: {len(results)}"
    )

    print(
        f"Passed: {passed}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"Saved to: {OUTPUT_PATH}"
    )

    if len(results) < len(topics):

        print()

        print(
            "Validation is incomplete."
        )

        print(
            "Run the same command again later "
            "to continue from the saved progress."
        )


if __name__ == "__main__":
    main()