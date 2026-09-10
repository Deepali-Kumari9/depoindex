import json
import re


INPUT_PATH = "outputs/baseline_topics.json"
OUTPUT_PATH = "outputs/refined_topics.json"

# Topics separated by at most this many transcript records
# can be considered adjacent for merging.
MAX_GAP = 3

# Minimum lexical similarity required before two nearby topics
# are considered related.
SIMILARITY_THRESHOLD = 0.40


def load_results(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_results(results, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)


def normalize_text(text):
    """
    Normalize a topic label for lexical comparison.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    stop_words = {
        "and",
        "the",
        "a",
        "an",
        "of",
        "to",
        "as",
        "for",
        "on",
        "in",
        "regarding",
        "discussion",
        "discussed",
    }

    words = [
        word
        for word in text.split()
        if word not in stop_words
    ]

    return set(words)


def lexical_similarity(topic_a, topic_b):
    """
    Calculate Jaccard similarity between two topic labels.
    """
    words_a = normalize_text(topic_a)
    words_b = normalize_text(topic_b)

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def parse_ref(source_ref):
    """
    Convert page:line into a sortable tuple.
    """
    page, line = source_ref.split(":")
    return int(page), int(line)


def ref_distance(ref_a, ref_b):
    """
    Approximate distance between two page:line references.

    This is used only to determine whether two topics are
    close enough to consider merging.
    """
    page_a, line_a = parse_ref(ref_a)
    page_b, line_b = parse_ref(ref_b)

    if page_a == page_b:
        return abs(line_b - line_a)

    # Keep the calculation simple and deterministic.
    return abs(page_b - page_a) * 100 + abs(line_b - line_a)


def should_merge(topic_a, topic_b):
    """
    Decide whether two nearby topics represent the same subject.
    """

    similarity = lexical_similarity(
        topic_a["topic"],
        topic_b["topic"]
    )

    distance = ref_distance(
        topic_a["end_ref"],
        topic_b["start_ref"]
    )

    return (
        distance <= MAX_GAP
        and similarity >= SIMILARITY_THRESHOLD
    )


def merge_topics(topic_a, topic_b):
    """
    Merge two related topic entries while preserving provenance.
    """

    evidence_refs = []

    for ref in topic_a.get("evidence_refs", []):
        if ref not in evidence_refs:
            evidence_refs.append(ref)

    for ref in topic_b.get("evidence_refs", []):
        if ref not in evidence_refs:
            evidence_refs.append(ref)

    return {
        "topic": topic_a["topic"],
        "start_ref": topic_a["start_ref"],
        "end_ref": topic_b["end_ref"],
        "evidence_refs": evidence_refs,
    }


def refine_topics(results):
    """
    Refine successful baseline results.

    Failed API calls are preserved separately and do not produce
    fabricated topic entries.
    """

    successful_topics = []

    for result in results:
        if "error" in result:
            continue

        for topic in result.get("topics", []):
            topic_copy = dict(topic)
            topic_copy["source_chunk_id"] = result["chunk_id"]
            successful_topics.append(topic_copy)

    # Sort topics by their original transcript location.
    successful_topics.sort(
        key=lambda topic: parse_ref(topic["start_ref"])
    )

    refined_topics = []

    for topic in successful_topics:

        if not refined_topics:
            refined_topics.append(topic)
            continue

        previous = refined_topics[-1]

        if should_merge(previous, topic):
            merged = merge_topics(previous, topic)
            merged["source_chunk_ids"] = sorted(
                set(
                    previous.get(
                        "source_chunk_ids",
                        [previous["source_chunk_id"]]
                    )
                    + [topic["source_chunk_id"]]
                )
            )

            refined_topics[-1] = merged

        else:
            topic["source_chunk_ids"] = [
                topic["source_chunk_id"]
            ]
            refined_topics.append(topic)

    # Remove internal helper field from final output.
        # Ensure every topic has a consistent source_chunk_ids field.
    for topic in refined_topics:
        if "source_chunk_ids" not in topic:
            topic["source_chunk_ids"] = [
                topic["source_chunk_id"]
            ]

        topic.pop("source_chunk_id", None)
    return refined_topics


def main():
    results = load_results(INPUT_PATH)

    successful_chunks = sum(
        1 for result in results
        if "error" not in result
    )

    failed_chunks = sum(
        1 for result in results
        if "error" in result
    )

    baseline_topic_count = sum(
        len(result.get("topics", []))
        for result in results
        if "error" not in result
    )

    refined_topics = refine_topics(results)

    output = {
        "metadata": {
            "input": INPUT_PATH,
            "successful_chunks": successful_chunks,
            "failed_chunks": failed_chunks,
            "baseline_topic_count": baseline_topic_count,
            "refined_topic_count": len(refined_topics),
            "max_gap": MAX_GAP,
            "similarity_threshold": SIMILARITY_THRESHOLD,
        },
        "topics": refined_topics,
    }

    save_results(output, OUTPUT_PATH)

    print("=== DepoIndex Topic Refinement ===")
    print()
    print(f"Successful chunks: {successful_chunks}")
    print(f"Failed chunks: {failed_chunks}")
    print(f"Baseline topics: {baseline_topic_count}")
    print(f"Refined topics: {len(refined_topics)}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()