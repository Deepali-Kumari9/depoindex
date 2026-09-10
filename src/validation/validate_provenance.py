import json

CANONICAL_PATH = "outputs/canonical_transcript.json"
TOPICS_PATH = "outputs/refined_topics.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_provenance(canonical_records, topics):
    valid_refs = {
        record["source_ref"]
        for record in canonical_records
    }

    errors = []

    for index, topic in enumerate(topics, start=1):
        topic_name = topic.get("topic", f"Topic {index}")

        # Check required fields
        required_fields = [
            "start_ref",
            "end_ref",
            "evidence_refs",
        ]

        for field in required_fields:
            if field not in topic:
                errors.append(
                    f"Topic {index} ({topic_name}): "
                    f"missing field '{field}'"
                )

        if "start_ref" not in topic:
            continue

        if "end_ref" not in topic:
            continue

        if "evidence_refs" not in topic:
            continue

        start_ref = topic["start_ref"]
        end_ref = topic["end_ref"]
        evidence_refs = topic["evidence_refs"]

        # Validate start and end references
        if start_ref not in valid_refs:
            errors.append(
                f"Topic {index} ({topic_name}): "
                f"invalid start_ref {start_ref}"
            )

        if end_ref not in valid_refs:
            errors.append(
                f"Topic {index} ({topic_name}): "
                f"invalid end_ref {end_ref}"
            )

        # Validate evidence references
        for ref in evidence_refs:
            if ref not in valid_refs:
                errors.append(
                    f"Topic {index} ({topic_name}): "
                    f"invalid evidence_ref {ref}"
                )

    return errors


def main():
    canonical_records = load_json(CANONICAL_PATH)
    refined_data = load_json(TOPICS_PATH)

    topics = refined_data["topics"]

    errors = validate_provenance(
        canonical_records,
        topics
    )

    print("=== DepoIndex Provenance Validation ===")
    print()
    print(f"Canonical transcript records: {len(canonical_records)}")
    print(f"Topics checked: {len(topics)}")
    print(f"Errors found: {len(errors)}")
    print()

    if errors:
        print("Validation FAILED")
        print()

        for error in errors:
            print(f"- {error}")

    else:
        print("Validation PASSED")
        print("All topic provenance references exist in the canonical transcript.")


if __name__ == "__main__":
    main()