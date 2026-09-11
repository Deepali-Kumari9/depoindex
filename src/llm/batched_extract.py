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

INPUT_PATH = "outputs/transcript_chunks.json"
OUTPUT_PATH = "outputs/batched_topics.json"

# 5 original chunks per Gemini request
BATCH_SIZE = 5


def load_chunks(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_results(results, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)


def build_prompt(chunks):
    sections = []

    for chunk in chunks:
        transcript_text = "\n".join(
            f"{record['source_ref']} | {record['text']}"
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


def extract_batch(chunks):
    prompt = build_prompt(chunks)

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt
    )

    return clean_json_response(interaction.output_text)


def main():
    chunks = load_chunks(INPUT_PATH)

    all_results = []

    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"Total chunks: {len(chunks)}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Total Gemini requests: {total_batches}")
    print()

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        batch_number = (start // BATCH_SIZE) + 1

        print(
            f"Processing batch {batch_number}/{total_batches} "
            f"(chunks {batch[0]['chunk_id']}-{batch[-1]['chunk_id']})...",
            flush=True
        )

        try:
            result = extract_batch(batch)

            batch_result = {
                "batch_id": batch_number,
                "chunk_ids": [chunk["chunk_id"] for chunk in batch],
                "start_ref": batch[0]["start_ref"],
                "end_ref": batch[-1]["end_ref"],
                "topics": result.get("topics", [])
            }

            all_results.append(batch_result)

            save_results(all_results, OUTPUT_PATH)

            print(
                f"Completed batch {batch_number}: "
                f"{len(batch_result['topics'])} topics"
            )

        except Exception as error:
            print(
                f"Error in batch {batch_number}: {error}",
                flush=True
            )

            error_result = {
                "batch_id": batch_number,
                "chunk_ids": [chunk["chunk_id"] for chunk in batch],
                "start_ref": batch[0]["start_ref"],
                "end_ref": batch[-1]["end_ref"],
                "topics": [],
                "error": str(error)
            }

            all_results.append(error_result)

            save_results(all_results, OUTPUT_PATH)

        # Small delay between requests
        time.sleep(2)

    print()
    print(f"Saved batched results to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()