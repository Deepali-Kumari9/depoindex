import json

CLEANED_PATH = "outputs/cleaned_transcript.json"
TOPICS_PATH = "outputs/refined_topics.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def position(ref):
    page, line = ref.split(":")
    return int(page) * 1000 + int(line)


def main():
    cleaned = load_json(CLEANED_PATH)
    data = load_json(TOPICS_PATH)
    topics = data["topics"]

    covered = {}
    invalid = []
    
    for topic in topics:
        start = position(topic["start_ref"])
        end = position(topic["end_ref"])

        if start > end:
            invalid.append(
                f"{topic['topic_id']}: {topic['start_ref']} -> {topic['end_ref']}"
            )
            continue

        for record in cleaned:
            p = position(record["source_ref"])
            if start <= p <= end:
                covered.setdefault(record["source_ref"], []).append(
                    topic["topic_id"]
                )

    uncovered = [
        record["source_ref"]
        for record in cleaned
        if record["source_ref"] not in covered
    ]

    overlaps = {
        ref: topic_ids
        for ref, topic_ids in covered.items()
        if len(topic_ids) > 1
    }

    print("=== DepoIndex Coverage Audit ===")
    print(f"Cleaned transcript records: {len(cleaned)}")
    print(f"Topics checked: {len(topics)}")
    print(f"Uncovered cleaned records: {len(uncovered)}")
    print(f"Overlapping covered records: {len(overlaps)}")
    print(f"Invalid topic boundaries: {len(invalid)}")
    print()

    if uncovered:
        print("UNCOVERED:")
        print(", ".join(uncovered))

    if overlaps:
        print()
        print("OVERLAPS:")
        for ref, topic_ids in overlaps.items():
            print(ref, "->", ", ".join(topic_ids))

    if invalid:
        print()
        print("INVALID:")
        for item in invalid:
            print(item)


if __name__ == "__main__":
    main()
