import json
from collections import Counter


INPUT_PATH = "outputs/baseline_topics.json"


def load_results(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    results = load_results(INPUT_PATH)

    total_chunks = len(results)
    successful_chunks = sum(
        1 for result in results if "error" not in result
    )
    failed_chunks = total_chunks - successful_chunks

    successful_topics = [
        topic
        for result in results
        if "error" not in result
        for topic in result.get("topics", [])
    ]

    topic_count = len(successful_topics)

    labels = [
        topic["topic"].strip().lower()
        for topic in successful_topics
        if topic.get("topic")
    ]

    duplicate_labels = [
        label
        for label, count in Counter(labels).items()
        if count > 1
    ]

    print("=== DepoIndex Baseline Evaluation ===")
    print()
    print(f"Total chunks attempted: {total_chunks}")
    print(f"Successful chunks: {successful_chunks}")
    print(f"Failed chunks: {failed_chunks}")
    print(f"Topics extracted: {topic_count}")
    print()

    if total_chunks:
        success_rate = successful_chunks / total_chunks * 100
        print(f"Chunk success rate: {success_rate:.2f}%")

    print()

    if duplicate_labels:
        print("Duplicate topic labels:")
        for label in duplicate_labels:
            print(f"- {label}")
    else:
        print("Duplicate topic labels: none")

    print()

    print("=== Successful Chunk Summary ===")

    for result in results:
        if "error" in result:
            continue

        print(
            f"Chunk {result['chunk_id']}: "
            f"{len(result.get('topics', []))} topics "
            f"({result['start_ref']} -> {result['end_ref']})"
        )

    print()
    print("=== Baseline Observations ===")
    print("1. The baseline preserved page:line references in successful outputs.")
    print("2. Some topic labels were verbose or closely related.")
    print("3. Some evidence lists contained many transcript lines.")
    print("4. Independent chunk processing can create topic fragmentation.")
    print("5. The baseline encountered API quota limitations.")
    print("6. A more efficient batching strategy is required for the final pipeline.")


if __name__ == "__main__":
    main()