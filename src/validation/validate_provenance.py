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

    ref_order = {
        record["source_ref"]: index
        for index, record in enumerate(canonical_records)
    }

    errors = []

    for index, topic in enumerate(topics, start=1):

        topic_name = topic.get(
            "topic",
            f"Topic {index}"
        )

        required_fields = [
            "start_ref",
            "end_ref",
            "evidence_refs",
        ]

        # Check required fields
        for field in required_fields:
            if field not in topic:
                errors.append(
                    f"Topic {index} ({topic_name}): "
                    f"missing field '{field}'"
                )

        if not all(
            field in topic
            for field in required_fields
        ):
            continue

        start_ref = topic["start_ref"]
        end_ref = topic["end_ref"]
        evidence_refs = topic["evidence_refs"]

        # Check start reference
        if start_ref not in valid_refs:
            errors.append(
                f"Topic {index} ({topic_name}): "
                f"invalid start_ref {start_ref}"
            )

        # Check end reference
        if end_ref not in valid_refs:
            errors.append(
                f"Topic {index} ({topic_name}): "
                f"invalid end_ref {end_ref}"
            )

        # Check evidence references
        if not evidence_refs:
            errors.append(
                f"Topic {index} ({topic_name}): "
                f"no evidence references provided"
            )

        for ref in evidence_refs:
            if ref not in valid_refs:
                errors.append(
                    f"Topic {index} ({topic_name}): "
                    f"invalid evidence_ref {ref}"
                )

        # Check boundary ordering
        if (
            start_ref in ref_order
            and end_ref in ref_order
        ):
            if ref_order[start_ref] > ref_order[end_ref]:
                errors.append(
                    f"Topic {index} ({topic_name}): "
                    f"start_ref {start_ref} occurs after "
                    f"end_ref {end_ref}"
                )

        # Check evidence is inside boundaries
        if (
            start_ref in ref_order
            and end_ref in ref_order
        ):
            start_position = ref_order[start_ref]
            end_position = ref_order[end_ref]

            for ref in evidence_refs:

                if ref in ref_order:

                    evidence_position = ref_order[ref]

                    if not (
                        start_position
                        <= evidence_position
                        <= end_position
                    ):
                        errors.append(
                            f"Topic {index} ({topic_name}): "
                            f"evidence_ref {ref} falls outside "
                            f"topic boundaries"
                        )

    return errors


def main():

    canonical_records = load_json(
        CANONICAL_PATH
    )

    refined_data = load_json(
        TOPICS_PATH
    )

    # refined_topics.json contains metadata + topics
    topics = refined_data["topics"]

    errors = validate_provenance(
        canonical_records,
        topics
    )

    print(
        "=== DepoIndex Final Provenance Validation ==="
    )

    print()

    print(
        f"Canonical transcript records: "
        f"{len(canonical_records)}"
    )

    print(
        f"Topics checked: {len(topics)}"
    )

    print(
        f"Errors found: {len(errors)}"
    )

    print()

    if errors:

        print("Validation FAILED")
        print()

        for error in errors:
            print(f"- {error}")

    else:

        print("Validation PASSED")

        print(
            "All final topic provenance references "
            "exist in the canonical transcript."
        )

        print(
            "All topic boundaries are ordered correctly, "
            "and evidence references fall within "
            "their boundaries."
        )


if __name__ == "__main__":
    main()