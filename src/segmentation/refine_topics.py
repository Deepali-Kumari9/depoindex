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
    topics = []

    # Convert batch-local related_to references into
    # temporary references before global sorting.
    #
    # Each related_to value refers to a topic within the
    # same LLM batch. We store the batch ID and local topic
    # index so the relationship can be mapped to the final
    # global topic ID after chronological sorting.

    for batch in batched_results:
        batch_id = batch["batch_id"]

        for local_index, topic in enumerate(
            batch.get("topics", []),
            start=1
        ):
            topic_copy = dict(topic)

            topic_copy["_batch_id"] = batch_id
            topic_copy["_local_index"] = local_index

            topics.append(topic_copy)

    # Keep topics in actual transcript order.
    topics.sort(
        key=lambda topic: parse_ref(topic["start_ref"])
    )

    # Map each batch-local topic reference to its final global topic ID.
    batch_local_to_global = {}

    for global_index, topic in enumerate(topics, start=1):
        batch_local_to_global[
            (topic["_batch_id"], topic["_local_index"])
        ] = global_index

    refined_topics = []

    for global_index, topic in enumerate(topics, start=1):

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

        global_related_to = []

        for local_related_id in topic.get("related_to", []):
            # Ignore invalid local topic IDs such as 0.
            if local_related_id < 1:
                continue

            related_global_id = batch_local_to_global.get(
                (topic["_batch_id"], local_related_id)
            )

            if related_global_id is not None:
                global_related_to.append(related_global_id)

        refined_topic = {
            "topic_id": global_index,
            "topic": topic["topic"],
            "start_ref": topic["start_ref"],
            "end_ref": topic["end_ref"],
            "evidence_refs": topic.get("evidence_refs", []),
            "related_to": sorted(set(global_related_to)),
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