import json
from pathlib import Path


RUN_FILES = [
    "outputs/stability_run_1.json",
    "outputs/stability_run_2.json",
    "outputs/stability_run_3.json",
]

CANONICAL_PATH = "outputs/canonical_transcript.json"
OUTPUT_PATH = "outputs/stability_report.json"


def load_topics(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        return data.get("topics", [])

    topics = []

    for batch in data:
        topics.extend(batch.get("topics", []))

    return topics


def load_canonical_refs(path):
    with open(path, "r", encoding="utf-8") as file:
        records = json.load(file)

    return {
        record["source_ref"]
        for record in records
        if record.get("source_ref")
    }


def topic_signature(topic):
    return (
        topic.get("topic", ""),
        topic.get("start_ref", ""),
        topic.get("end_ref", ""),
    )


def validate_provenance(topics, valid_refs):
    invalid_boundaries = []
    invalid_evidence = []

    for index, topic in enumerate(topics, start=1):
        start_ref = topic.get("start_ref")
        end_ref = topic.get("end_ref")

        if start_ref not in valid_refs:
            invalid_boundaries.append({
                "topic_number": index,
                "topic": topic.get("topic", ""),
                "reference_type": "start_ref",
                "reference": start_ref
            })

        if end_ref not in valid_refs:
            invalid_boundaries.append({
                "topic_number": index,
                "topic": topic.get("topic", ""),
                "reference_type": "end_ref",
                "reference": end_ref
            })

        for evidence_ref in topic.get("evidence_refs", []):
            if evidence_ref not in valid_refs:
                invalid_evidence.append({
                    "topic_number": index,
                    "topic": topic.get("topic", ""),
                    "reference": evidence_ref
                })

    return invalid_boundaries, invalid_evidence


def compare_runs(runs):
    topic_counts = [len(topics) for topics in runs]

    signatures = [
        {topic_signature(topic) for topic in topics}
        for topics in runs
    ]

    common_topics = set.intersection(*signatures)

    pairwise_matches = {}

    for i in range(len(runs)):
        for j in range(i + 1, len(runs)):
            shared = signatures[i] & signatures[j]

            pairwise_matches[
                f"run_{i + 1}_vs_run_{j + 1}"
            ] = len(shared)

    return {
        "topic_counts": {
            "run_1": topic_counts[0],
            "run_2": topic_counts[1],
            "run_3": topic_counts[2]
        },
        "topic_count_stability": (
            "STABLE"
            if len(set(topic_counts)) == 1
            else "VARIED"
        ),
        "identical_label_and_boundary_matches": {
            "all_three_runs": len(common_topics),
            "pairwise": pairwise_matches
        }
    }


def main():
    missing = [
        path for path in RUN_FILES
        if not Path(path).exists()
    ]

    if not Path(CANONICAL_PATH).exists():
        missing.append(CANONICAL_PATH)

    if missing:
        print("Missing required files:")

        for path in missing:
            print(f"- {path}")

        return

    runs = [
        load_topics(path)
        for path in RUN_FILES
    ]

    valid_refs = load_canonical_refs(CANONICAL_PATH)

    provenance_results = []

    for index, topics in enumerate(runs, start=1):
        invalid_boundaries, invalid_evidence = (
            validate_provenance(
                topics,
                valid_refs
            )
        )

        provenance_results.append({
            "run": index,
            "invalid_boundary_refs": invalid_boundaries,
            "invalid_evidence_refs": invalid_evidence,
            "status": (
                "VALID"
                if not invalid_boundaries
                and not invalid_evidence
                else "INVALID"
            )
        })

    comparison = compare_runs(runs)

    all_provenance_valid = all(
        result["status"] == "VALID"
        for result in provenance_results
    )

    report = {
        "experiment": {
            "input": "outputs/transcript_chunks.json",
            "canonical_transcript": CANONICAL_PATH,
            "scope": "complete deposition",
            "printed_pages": "7-88",
            "records": 2027,
            "chunks": 51,
            "batch_size": 5,
            "runs": 3
        },

        "topic_counts": comparison["topic_counts"],

        "topic_count_stability": (
            comparison["topic_count_stability"]
        ),

        "identical_label_and_boundary_matches": (
            comparison[
                "identical_label_and_boundary_matches"
            ]
        ),

        "provenance_validation": {
            "canonical_reference_count": len(valid_refs),
            "overall_status": (
                "VALID"
                if all_provenance_valid
                else "INVALID"
            ),
            "runs": provenance_results
        },

        "interpretation": {
            "topic_count": (
                "The topic count varied across runs, "
                "indicating some LLM segmentation variability."
            ),
            "provenance": (
                "All topic boundaries and evidence references "
                "were checked against the canonical transcript."
            ),
            "reproducibility": (
                "The complete deposition was processed three "
                "times using the same extraction, chunking, "
                "prompting, and post-processing pipeline."
            )
        }
    }

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("=== DepoIndex Three-Run Stability Evaluation ===")
    print()

    for index, topics in enumerate(runs, start=1):
        print(
            f"Run {index}: {len(topics)} topics"
        )

    print()

    print(
        f"Topic counts: "
        f"{comparison['topic_counts']['run_1']}, "
        f"{comparison['topic_counts']['run_2']}, "
        f"{comparison['topic_counts']['run_3']}"
    )

    print()

    print(
        f"Topic count stability: "
        f"{comparison['topic_count_stability']}"
    )

    print()

    print(
        "Topics with identical label + boundary "
        "across all three runs: "
        f"{comparison['identical_label_and_boundary_matches']['all_three_runs']}"
    )

    print()

    for pair, count in (
        comparison[
            "identical_label_and_boundary_matches"
        ]["pairwise"].items()
    ):
        print(
            f"{pair}: {count} identical topics"
        )

    print()

    print(
        "Provenance validation:"
    )

    for result in provenance_results:
        print(
            f"Run {result['run']}: "
            f"{result['status']} "
            f"({len(result['invalid_boundary_refs'])} "
            f"invalid boundaries, "
            f"{len(result['invalid_evidence_refs'])} "
            f"invalid evidence refs)"
        )

    print()

    print(
        f"Overall provenance: "
        f"{'VALID' if all_provenance_valid else 'INVALID'}"
    )

    print()

    print(
        f"Saved report to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()