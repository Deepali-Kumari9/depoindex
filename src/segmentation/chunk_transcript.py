import json


INPUT_PATH = "outputs/cleaned_transcript.json"
OUTPUT_PATH = "outputs/transcript_chunks.json"

CHUNK_SIZE = 40


def load_transcript(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def create_chunks(records, chunk_size=CHUNK_SIZE):
    chunks = []

    for i in range(0, len(records), chunk_size):

        chunk_records = records[i:i + chunk_size]

        if not chunk_records:
            continue

        start_record = chunk_records[0]
        end_record = chunk_records[-1]

        chunk = {
            "chunk_id": len(chunks) + 1,

            # Stable transcript references
            "start_ref": start_record["source_ref"],
            "end_ref": end_record["source_ref"],

            # Document location metadata
            "start_page": start_record["printed_page"],
            "end_page": end_record["printed_page"],

            # Number of transcript records in this chunk
            "record_count": len(chunk_records),

            # Actual transcript records
            "records": chunk_records
        }

        chunks.append(chunk)

    return chunks


def save_chunks(chunks, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False
        )


if __name__ == "__main__":

    records = load_transcript(INPUT_PATH)

    chunks = create_chunks(records)

    save_chunks(chunks, OUTPUT_PATH)

    print("=== DepoIndex Transcript Chunking ===")
    print()
    print(f"Transcript records: {len(records)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Chunk size: {CHUNK_SIZE}")
    print(f"Source: {INPUT_PATH}")
    print(f"Saved to: {OUTPUT_PATH}")