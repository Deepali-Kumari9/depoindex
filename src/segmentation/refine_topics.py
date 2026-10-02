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
    """
    Flatten topics while preserving the batch-local topic position.

    related_to values produced by the LLM are batch-local because each
    Gemini request sees only its own batch of chunks. Therefore we keep
    the originating batch and local topic index so those relationships
    can be converted to final global topic IDs later.
    """

    topics = []

    for batch_index, batch in enumerate(batched_data, start=1):

        batch_topics = batch.get("topics", [])

        for local_index, topic in enumerate(
            batch_topics,
            start=1
        ):
            topic_copy = dict(topic)

            topic_copy["_batch_index"] = batch_index
            topic_copy["_batch_topic_index"] = local_index

            topics.append(topic_copy)

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
    for index, topic in enumerate(
        topics,
        start=1
    ):
        topic["topic_id"] = index


def normalize_related_to(topics):
    """
    Convert LLM batch-local related_to IDs into final global topic IDs.

    Example:

        Batch 2:
            local topic 2 -> related_to [1]

    becomes:

        global topic 4 -> related_to [3]

    if batch 2's local topic 1 became global topic 3.

    Invalid local IDs are ignored.
    Cross-batch relationships are not inferred because the LLM did not
    receive the other batch's topic list.
    """

    batch_local_to_global = {}

    for topic in topics:

        batch_index = topic.get("_batch_index")
        local_index = topic.get(
            "_batch_topic_index"
        )

        if (
            batch_index is None
            or local_index is None
        ):
            continue

        batch_local_to_global[
            (batch_index, local_index)
        ] = topic["topic_id"]

    for topic in topics:

        batch_index = topic.get(
            "_batch_index"
        )

        related = topic.get(
            "related_to",
            []
        )

        if not isinstance(
            related,
            list
        ):
            topic["related_to"] = []
            continue

        normalized = []

        for related_id in related:

            if not isinstance(
                related_id,
                int
            ):
                continue

            global_id = batch_local_to_global.get(
                (
                    batch_index,
                    related_id
                )
            )

            if global_id is not None:
                normalized.append(
                    global_id
                )

        topic["related_to"] = sorted(
            set(normalized)
        )


def assign_source_chunk_ids(
    topics,
    chunks,
    ref_order
):
    """
    Derive source chunk IDs deterministically from final topic
    page:line boundaries.

    A chunk is associated with a topic when the transcript ranges
    overlap.
    """

    for topic in topics:

        start_ref = topic.get(
            "start_ref"
        )

        end_ref = topic.get(
            "end_ref"
        )

        if (
            start_ref not in ref_order
            or end_ref not in ref_order
        ):
            topic["source_chunk_ids"] = []
            continue

        start_position = ref_order[
            start_ref
        ]

        end_position = ref_order[
            end_ref
        ]

        if start_position > end_position:
            topic["source_chunk_ids"] = []
            continue

        source_chunk_ids = []

        for chunk in chunks:

            chunk_start = chunk.get(
                "start_ref"
            )

            chunk_end = chunk.get(
                "end_ref"
            )

            if (
                chunk_start not in ref_order
                or chunk_end not in ref_order
            ):
                continue

            chunk_start_position = ref_order[
                chunk_start
            ]

            chunk_end_position = ref_order[
                chunk_end
            ]

            # Ranges overlap when:
            #
            # topic_start <= chunk_end
            # AND
            # chunk_start <= topic_end
            #
            if (
                start_position
                <= chunk_end_position
                and
                chunk_start_position
                <= end_position
            ):
                source_chunk_ids.append(
                    chunk["chunk_id"]
                )

        topic["source_chunk_ids"] = sorted(
            set(source_chunk_ids)
        )


def remove_internal_fields(topics):
    """
    Remove internal bookkeeping fields before saving the final
    refined topic file.
    """

    for topic in topics:

        topic.pop(
            "_batch_index",
            None
        )

        topic.pop(
            "_batch_topic_index",
            None
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

    for index in range(
        len(topics) - 1
    ):

        current = topics[index]
        next_topic = topics[
            index + 1
        ]

        current_start = current.get(
            "start_ref"
        )

        current_end = current.get(
            "end_ref"
        )

        next_start = next_topic.get(
            "start_ref"
        )

        if (
            current_start not in ref_order
            or current_end not in ref_order
            or next_start not in ref_order
        ):
            continue

        current_end_position = ref_order[
            current_end
        ]

        next_start_position = ref_order[
            next_start
        ]

        if (
            current_end_position
            >= next_start_position
        ):

            if next_start_position == 0:
                continue

            new_current_end = canonical_records[
                next_start_position - 1
            ]["source_ref"]

            if (
                new_current_end
                != current_end
            ):

                refinements.append({
                    "topic_id": current.get(
                        "topic_id"
                    ),
                    "old_end_ref": current_end,
                    "new_end_ref": new_current_end,
                    "next_topic_start_ref": next_start
                })

                current["end_ref"] = (
                    new_current_end
                )

    # ---------------------------------------------------------
    # STEP 2:
    # Remove evidence references that fall outside the final
    # topic boundaries.
    # ---------------------------------------------------------

    for topic in topics:

        start_ref = topic.get(
            "start_ref"
        )

        end_ref = topic.get(
            "end_ref"
        )

        if (
            start_ref not in ref_order
            or end_ref not in ref_order
        ):
            continue

        start_position = ref_order[
            start_ref
        ]

        end_position = ref_order[
            end_ref
        ]

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
                and
                start_position
                <= ref_order[ref]
                <= end_position
            )
        ]

    return refinements


def main():

    batched_data = load_json(
        BATCHED_TOPICS_PATH
    )

    chunks = load_json(
        CHUNKS_PATH
    )

    canonical_records = load_json(
        CANONICAL_PATH
    )

    topics = flatten_topics(
        batched_data
    )

    raw_topic_count = len(
        topics
    )

    ref_order = build_reference_order(
        canonical_records
    )

    topics = sort_topics(
        topics,
        ref_order
    )

    assign_topic_ids(
        topics
    )

    # Convert batch-local LLM relationships into global IDs.
    normalize_related_to(
        topics
    )

    # Refine boundaries first because source chunk IDs must be
    # calculated from the FINAL boundaries.
    refinements = (
        refine_overlapping_boundaries(
            topics,
            canonical_records,
            ref_order
        )
    )

    # Derive source chunks from final transcript boundaries.
    assign_source_chunk_ids(
        topics,
        chunks,
        ref_order
    )

    # Remove internal bookkeeping fields before saving.
    remove_internal_fields(
        topics
    )

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

    topics_with_chunks = sum(
        1
        for topic in topics
        if topic.get(
            "source_chunk_ids"
        )
    )

    print(
        f"Topics with source chunks: "
        f"{topics_with_chunks}/{len(topics)}"
    )

    print()

    if refinements:

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