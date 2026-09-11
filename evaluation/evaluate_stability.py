import json
from pathlib import Path


RUN_FILES = [
    "outputs/stability_run_1.json",
    "outputs/stability_run_2.json",
    "outputs/stability_run_3.json",
]

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


def topic_signature(topic):
    return (
        topic.get("topic", ""),
        topic.get("start_ref", ""),
        topic.get("end_ref", ""),
    )


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
            pairwise_matches[f"run_{i + 1}_vs_run_{j + 1}"] = len(shared)

    provenance_valid = True

    for topics in runs:
        for topic in topics:
            if not topic.get("start_ref") or not topic.get("end_ref"):
                provenance_valid = False

    report = {
        "experiment": {
            "input": "outputs/stability_chunks_19_34.json",
            "pages": "19-34",
            "records": 400,
            "runs": 3
        },
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
        },
        "provenance_structure": (
            "VALID"
            if provenance_valid
            else "INVALID"
        )
    }

    return report


def main():
    missing = [
        path for path in RUN_FILES
        if not Path(path).exists()
    ]

    if missing:
        print("Missing stability run files:")

        for path in missing:
            print(f"- {path}")

        return

    runs = [load_topics(path) for path in RUN_FILES]

    report = compare_runs(runs)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("=== DepoIndex Three-Run Stability Evaluation ===")
    print()

    for index, topics in enumerate(runs, start=1):
        print(f"Run {index}: {len(topics)} topics")

    print()
    print(f"Topic counts: {runs and [len(topics) for topics in runs]}")
    print()
    print(
        f"Topic count stability: "
        f"{report['topic_count_stability']}"
    )
    print()
    print(
        "Topics with identical label + boundary across all runs: "
        f"{report['identical_label_and_boundary_matches']['all_three_runs']}"
    )
    print()

    for pair, count in report["identical_label_and_boundary_matches"]["pairwise"].items():
        print(f"{pair}: {count} identical topics")

    print()
    print(
        f"Provenance structure: "
        f"{report['provenance_structure']}"
    )
    print()
    print(f"Saved report to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()