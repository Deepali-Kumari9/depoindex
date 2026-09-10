import json


INPUT_PATH = "outputs/canonical_transcript.json"
OUTPUT_PATH = "outputs/transcript_chunks.json"

CHUNK_SIZE = 40


def load_transcript(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def create_chunks(records, chunk_size=CHUNK_SIZE):
    chunks = []

    for i in range(0, len(records), chunk_size):
        chunk_records = records[i:i + chunk_size]

        chunks.append({
            "chunk_id": len(chunks) + 1,
            "start_ref": chunk_records[0]["source_ref"],
            "end_ref": chunk_records[-1]["source_ref"],
            "records": chunk_records
        })

    return chunks


def save_chunks(chunks, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(chunks, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    records = load_transcript(INPUT_PATH)
    chunks = create_chunks(records)

    save_chunks(chunks, OUTPUT_PATH)

    print(f"Transcript records: {len(records)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Chunk size: {CHUNK_SIZE}")
    print(f"Saved to: {OUTPUT_PATH}")