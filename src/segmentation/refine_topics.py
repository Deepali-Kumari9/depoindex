import json


INPUT_PATH = "outputs/batched_topics.json"
CHUNKS_PATH = "outputs/transcript_chunks.json"
OUTPUT_PATH = "outputs/refined_topics.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def parse_ref(source_ref):
    page, line = source_ref.split(":")
    return int(page), int(line)


def build_reference_to_chunk_map(chunks):
    reference_to_chunk = {}

    for chunk in chunks:
        chunk_id = chunk["chunk_id"]

        for record in chunk["records"]:
            reference_to_chunk[record["source_ref"]] = chunk_id

    return reference_to_chunk


def flatten_topics(batched_results):
    topics = []

    for batch in batched_results:
        for topic in batch.get("topics", []):
            topics.append(dict(topic))

    return topics


def refine_topics(batched_results, reference_to_chunk):
    topics = flatten_topics(batched_results)

    # Keep topics in actual transcript order.
    topics.sort(
        key=lambda topic: parse_ref(topic["start_ref"])
    )

    refined_topics = []

    for index, topic in enumerate(topics, start=1):

        all_refs = [
            topic["start_ref"],
            topic["end_ref"],
            *topic.get("evidence_refs", [])
        ]

        source_chunk_ids = sorted(
            {
                reference_to_chunk[ref]
                for ref in all_refs
                if ref in reference_to_chunk
            }
        )

        refined_topic = {
            "topic_id": index,
            "topic": topic["topic"],
            "start_ref": topic["start_ref"],
            "end_ref": topic["end_ref"],
            "evidence_refs": topic.get("evidence_refs", []),
            "related_to": [],
            "source_chunk_ids": source_chunk_ids,
        }

        refined_topics.append(refined_topic)

    return refined_topics


def main():
    batched_results = load_json(INPUT_PATH)
    chunks = load_json(CHUNKS_PATH)

    reference_to_chunk = build_reference_to_chunk_map(chunks)

    refined_topics = refine_topics(
        batched_results,
        reference_to_chunk
    )

    raw_topic_count = sum(
        len(batch.get("topics", []))
        for batch in batched_results
    )

    output = {
        "metadata": {
            "input": INPUT_PATH,
            "batches_processed": len(batched_results),
            "raw_topic_count": raw_topic_count,
            "refined_topic_count": len(refined_topics),
            "refinement": (
                "Deterministic normalization of batched LLM topics. "
                "Topic boundaries and provenance are preserved. "
                "Source chunk IDs are derived from actual transcript references."
            ),
        },
        "topics": refined_topics,
    }

    save_json(output, OUTPUT_PATH)

    print("=== DepoIndex Topic Refinement ===")
    print()
    print(f"Batches processed: {len(batched_results)}")
    print(f"Raw topics: {raw_topic_count}")
    print(f"Refined topics: {len(refined_topics)}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()