import json

INPUT_PATH = "outputs/refined_topics.json"
OUTPUT_PATH = "outputs/validated_topic_index.json"


def load_topics(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data["topics"]


def validate_topic(topic, index):
    required_fields = [
        "topic",
        "start_ref",
        "end_ref",
        "evidence_refs",
    ]

    errors = []

    for field in required_fields:
        if field not in topic:
            errors.append(
                f"Topic {index}: missing field '{field}'"
            )

    if not errors:
        if not topic["topic"].strip():
            errors.append(f"Topic {index}: empty topic label")

        if not topic["start_ref"]:
            errors.append(f"Topic {index}: empty start_ref")

        if not topic["end_ref"]:
            errors.append(f"Topic {index}: empty end_ref")

        if not isinstance(topic["evidence_refs"], list):
            errors.append(
                f"Topic {index}: evidence_refs must be a list"
            )

    return errors


def build_topic_index(topics):
    validated_topics = []
    errors = []

    for index, topic in enumerate(topics, start=1):
        topic_errors = validate_topic(topic, index)

        if topic_errors:
            errors.extend(topic_errors)
            continue

        validated_topic = {
            "topic_id": f"T{index:02d}",
            "topic": topic["topic"],
            "start_ref": topic["start_ref"],
            "end_ref": topic["end_ref"],
            "evidence_refs": topic["evidence_refs"],
            "source_chunk_ids": topic.get(
                "source_chunk_ids", []
            ),
        }

        validated_topics.append(validated_topic)

    return validated_topics, errors


def save_output(topics, errors, path):
    output = {
        "metadata": {
            "topic_count": len(topics),
            "validation_status": "PASSED" if not errors else "FAILED",
            "source": INPUT_PATH,
        },
        "topics": topics,
        "validation_errors": errors,
    }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )


def main():
    topics = load_topics(INPUT_PATH)

    validated_topics, errors = build_topic_index(topics)

    save_output(
        validated_topics,
        errors,
        OUTPUT_PATH
    )

    print("=== DepoIndex Validated Topic Index ===")
    print()
    print(f"Input topics: {len(topics)}")
    print(f"Validated topics: {len(validated_topics)}")
    print(f"Validation errors: {len(errors)}")
    print()

    if errors:
        print("Validation FAILED")
        for error in errors:
            print(f"- {error}")
    else:
        print("Validation PASSED")
        print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()