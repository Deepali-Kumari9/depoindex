import json

BATCHED_TOPICS_PATH = "outputs/batched_topics.json"
CHUNKS_PATH = "outputs/transcript_chunks.json"
CANONICAL_PATH = "outputs/canonical_transcript.json"
OUTPUT_PATH = "outputs/refined_topics.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def build_reference_order(canonical_records):
    return {
        record["source_ref"]: index
        for index, record in enumerate(canonical_records)
    }


def flatten_topics(batched_data):
    topics = []

    for batch in batched_data:
        for topic in batch.get("topics", []):
            topics.append(dict(topic))

    return topics


def sort_topics(topics, ref_order):
    return sorted(
        topics,
        key=lambda topic: ref_order.get(
            topic.get("start_ref"),
            float("inf")
        )
    )


def assign_topic_ids(topics):
    for index, topic in enumerate(topics, start=1):
        topic["topic_id"] = index


def normalize_related_to(topics):
    valid_topic_ids = {
        topic["topic_id"]
        for topic in topics
    }

    for topic in topics:
        related = topic.get("related_to", [])

        if not isinstance(related, list):
            topic["related_to"] = []
            continue

        normalized = []

        for related_id in related:
            if related_id in valid_topic_ids:
                normalized.append(related_id)

        topic["related_to"] = sorted(
            set(normalized)
        )


def refine_overlapping_boundaries(
    topics,
    canonical_records,
    ref_order
):
    refinements = []

    # ---------------------------------------------------------
    # STEP 1:
    # Detect overlaps between consecutive topics and trim
    # the previous topic so that it ends before the next topic.
    # ---------------------------------------------------------

    for index in range(len(topics) - 1):

        current = topics[index]
        next_topic = topics[index + 1]

        current_start = current.get("start_ref")
        current_end = current.get("end_ref")
        next_start = next_topic.get("start_ref")

        if (
            current_start not in ref_order
            or current_end not in ref_order
            or next_start not in ref_order
        ):
            continue

        current_end_position = ref_order[current_end]
        next_start_position = ref_order[next_start]

        # Overlap exists when the current topic reaches
        # or passes the start of the next topic.
        if current_end_position >= next_start_position:

            # Cannot move before the first transcript record.
            if next_start_position == 0:
                continue

            # Find the canonical reference immediately
            # before the next topic starts.
            new_current_end = canonical_records[
                next_start_position - 1
            ]["source_ref"]

            if new_current_end != current_end:

                refinements.append({
                    "topic_id": current.get("topic_id"),
                    "old_end_ref": current_end,
                    "new_end_ref": new_current_end,
                    "next_topic_start_ref": next_start
                })

                current["end_ref"] = new_current_end

    # ---------------------------------------------------------
    # STEP 2:
    # IMPORTANT:
    # Clean evidence references for EVERY topic according
    # to its FINAL start/end boundaries.
    #
    # This fixes cases such as:
    #
    # Topic 30:
    # start = 71:23
    # end   = 73:13
    #
    # evidence contained 71:21
    #
    # 71:21 is outside the final boundary, so it is removed.
    # ---------------------------------------------------------

    for topic in topics:

        start_ref = topic.get("start_ref")
        end_ref = topic.get("end_ref")

        if (
            start_ref not in ref_order
            or end_ref not in ref_order
        ):
            continue

        start_position = ref_order[start_ref]
        end_position = ref_order[end_ref]

        original_evidence = topic.get(
            "evidence_refs",
            []
        )

        if not isinstance(
            original_evidence,
            list
        ):
            original_evidence = []

        topic["evidence_refs"] = [
            ref
            for ref in original_evidence
            if (
                ref in ref_order
                and start_position
                <= ref_order[ref]
                <= end_position
            )
        ]

    return refinements


def main():

    # ---------------------------------------------------------
    # Load all required inputs.
    # ---------------------------------------------------------

    batched_data = load_json(
        BATCHED_TOPICS_PATH
    )

    chunks = load_json(
        CHUNKS_PATH
    )

    canonical_records = load_json(
        CANONICAL_PATH
    )

    # ---------------------------------------------------------
    # Flatten topics from all Gemini batches.
    # ---------------------------------------------------------

    topics = flatten_topics(
        batched_data
    )

    raw_topic_count = len(topics)

    # ---------------------------------------------------------
    # Build canonical transcript reference ordering.
    # ---------------------------------------------------------

    ref_order = build_reference_order(
        canonical_records
    )

    # ---------------------------------------------------------
    # Sort topics chronologically according to the canonical
    # transcript rather than trusting batch order.
    # ---------------------------------------------------------

    topics = sort_topics(
        topics,
        ref_order
    )

    # ---------------------------------------------------------
    # Assign final sequential topic IDs.
    # ---------------------------------------------------------

    assign_topic_ids(
        topics
    )

    # ---------------------------------------------------------
    # Normalize related_to references.
    # ---------------------------------------------------------

    normalize_related_to(
        topics
    )

    # ---------------------------------------------------------
    # Refine overlapping boundaries and clean evidence refs.
    # ---------------------------------------------------------

    refinements = refine_overlapping_boundaries(
        topics,
        canonical_records,
        ref_order
    )

    # ---------------------------------------------------------
    # Save final refined topic index.
    # ---------------------------------------------------------

    output = {
        "metadata": {
            "source": BATCHED_TOPICS_PATH,
            "chunk_count": len(chunks),
            "raw_topic_count": raw_topic_count,
            "refined_topic_count": len(topics),
            "boundary_refinement_count": len(
                refinements
            ),
            "boundary_refinements": refinements
        },
        "topics": topics
    }

    save_json(
        output,
        OUTPUT_PATH
    )

    # ---------------------------------------------------------
    # Console summary.
    # ---------------------------------------------------------

    print(
        "=== DepoIndex Topic Refinement ==="
    )
    print()

    print(
        f"Batches processed: "
        f"{len(batched_data)}"
    )

    print(
        f"Raw topics: "
        f"{raw_topic_count}"
    )

    print(
        f"Refined topics: "
        f"{len(topics)}"
    )

    print(
        f"Boundary refinements: "
        f"{len(refinements)}"
    )

    if refinements:

        print()
        print(
            "Boundary refinements:"
        )

        for refinement in refinements:

            print(
                f"Topic "
                f"{refinement['topic_id']}: "
                f"{refinement['old_end_ref']} "
                f"-> "
                f"{refinement['new_end_ref']} "
                f"(next topic starts at "
                f"{refinement['next_topic_start_ref']})"
            )

    print()
    print(
        f"Saved to: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()