import json
import os
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# 60-second timeout so a single request cannot hang indefinitely
client = genai.Client(
    api_key=api_key,
    http_options={"timeout": 60000}
)

INPUT_PATH = "outputs/transcript_chunks.json"
OUTPUT_PATH = "outputs/baseline_topics.json"


def load_chunks(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_existing_results(path):
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return []


def save_results(results, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)


def build_prompt(chunk):
    transcript_text = "\n".join(
        f"{record['source_ref']} | {record['text']}"
        for record in chunk["records"]
    )

    return f"""
You are analyzing a legal deposition transcript.

Identify the meaningful topic or topics discussed in this transcript chunk.

Rules:
1. Use only the supplied transcript.
2. Do not invent information.
3. Preserve exact page:line references.
4. A topic should represent a meaningful subject of discussion.
5. If there are multiple meaningful topics, return multiple topics.
6. start_ref and end_ref must be exact references from the supplied transcript.
7. evidence_refs must also be exact references from the supplied transcript.
8. Do not include references that are not present in the transcript.

Return ONLY valid JSON in this format:

{{
  "topics": [
    {{
      "topic": "short meaningful topic label",
      "start_ref": "page:line",
      "end_ref": "page:line",
      "evidence_refs": ["page:line", "page:line"]
    }}
  ]
}}

Transcript chunk:

{transcript_text}
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


def extract_chunk(chunk):
    prompt = build_prompt(chunk)

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt
    )

    return clean_json_response(interaction.output_text)


def main():
    chunks = load_chunks(INPUT_PATH)

    # Load previously completed chunks if the script is resumed
    all_results = load_existing_results(OUTPUT_PATH)

    completed_ids = {
        result["chunk_id"]
        for result in all_results
        if "error" not in result
    }

    print(f"Total chunks: {len(chunks)}")
    print(f"Already completed: {len(completed_ids)}")
    print()

    for index, chunk in enumerate(chunks, start=1):

        chunk_id = chunk["chunk_id"]

        if chunk_id in completed_ids:
            print(f"Skipping chunk {index}/{len(chunks)} - already completed")
            continue

        print(
            f"Processing chunk {index}/{len(chunks)}...",
            flush=True
        )

        try:
            result = extract_chunk(chunk)

            chunk_result = {
                "chunk_id": chunk_id,
                "start_ref": chunk["start_ref"],
                "end_ref": chunk["end_ref"],
                "topics": result.get("topics", [])
            }

            all_results.append(chunk_result)

            # Save immediately after every successful chunk
            save_results(all_results, OUTPUT_PATH)

            print(
                f"Completed chunk {index}/{len(chunks)} "
                f"({len(chunk_result['topics'])} topics)"
            )

        except Exception as error:

            print(
                f"Error in chunk {index}: {error}",
                flush=True
            )

            error_result = {
                "chunk_id": chunk_id,
                "start_ref": chunk["start_ref"],
                "end_ref": chunk["end_ref"],
                "topics": [],
                "error": str(error)
            }

            all_results.append(error_result)

            # Save even failed chunks so the failure is documented
            save_results(all_results, OUTPUT_PATH)

        time.sleep(1)

    print()
    print(f"Saved baseline results to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()