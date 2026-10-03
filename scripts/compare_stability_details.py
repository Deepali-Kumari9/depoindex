import json
from pathlib import Path

ROOT = Path("outputs/stability_runs")
RUNS = ["run1", "run2", "run3"]


def load_topics(run_name):
    path = ROOT / run_name / "batched_topics.json"

    with open(path, "r", encoding="utf-8") as f:
        batches = json.load(f)

    topics = []

    for batch in batches:
        for topic in batch.get("topics", []):
            topics.append({
                "label": topic.get("topic", ""),
                "start": topic.get("start_ref", ""),
                "end": topic.get("end_ref", ""),
                "evidence": topic.get("evidence_refs", []),
                "related_to": topic.get("related_to", [])
            })

    return topics


runs = {}

for run in RUNS:
    runs[run] = load_topics(run)
    print(f"{run}: {len(runs[run])} topics")


def ref_to_tuple(ref):
    try:
        page, line = ref.split(":")
        return int(page), int(line)
    except Exception:
        return (9999, 9999)


def boundary_distance(a, b):
    a_start = ref_to_tuple(a["start"])
    b_start = ref_to_tuple(b["start"])

    a_end = ref_to_tuple(a["end"])
    b_end = ref_to_tuple(b["end"])

    return (
        abs(a_start[0] - b_start[0]) * 100
        + abs(a_start[1] - b_start[1])
        + abs(a_end[0] - b_end[0]) * 100
        + abs(a_end[1] - b_end[1])
    )


def match_topic(topic, candidates):
    best = None
    best_score = float("-inf")

    for candidate in candidates:
        score = 0

        # Same label is strong evidence.
        if topic["label"].strip().lower() == candidate["label"].strip().lower():
            score += 100

        # Same start/end is very strong evidence.
        if topic["start"] == candidate["start"]:
            score += 50

        if topic["end"] == candidate["end"]:
            score += 50

        # Nearby boundaries are better than completely unrelated ones.
        distance = boundary_distance(topic, candidate)
        score -= distance * 0.1

        # Evidence overlap helps identify the same semantic topic.
        a_evidence = set(topic["evidence"])
        b_evidence = set(candidate["evidence"])

        if a_evidence and b_evidence:
            overlap = len(a_evidence & b_evidence)
            score += min(overlap, 20)

        # related_to similarity.
        if topic["related_to"] == candidate["related_to"]:
            score += 5

        if score > best_score:
            best_score = score
            best = candidate

    return best


output = []

output.append("# Detailed Stability Comparison\n")

for a, b in [
    ("run1", "run2"),
    ("run2", "run3"),
    ("run1", "run3")
]:

    output.append(f"## {a} vs {b}\n")

    output.append(
        "| A topic | B topic | Label match | Boundary match | Evidence overlap | related_to match |\n"
        "|---|---|---|---|---|---|\n"
    )

    for topic in runs[a]:

        match = match_topic(topic, runs[b])

        if match is None:
            continue

        label_match = (
            topic["label"].strip().lower()
            == match["label"].strip().lower()
        )

        boundary_match = (
            topic["start"] == match["start"]
            and topic["end"] == match["end"]
        )

        # Compare evidence using Jaccard overlap instead of exact list equality.
        a_evidence = set(topic["evidence"])
        b_evidence = set(match["evidence"])

        if a_evidence or b_evidence:
            evidence_overlap = len(a_evidence & b_evidence) / max(
                len(a_evidence | b_evidence), 1
            )
        else:
            evidence_overlap = 1.0

        related_match = topic["related_to"] == match["related_to"]

        output.append(
            f'| {topic["label"]} '
            f'({topic["start"]}→{topic["end"]}) | '
            f'{match["label"]} '
            f'({match["start"]}→{match["end"]}) | '
            f'{"YES" if label_match else "NO"} | '
            f'{"YES" if boundary_match else "NO"} | '
            f'{evidence_overlap:.0%} | '
            f'{"YES" if related_match else "NO"} |\n'
        )

    output.append("\n")


out_path = ROOT / "stability_detail_comparison.md"

with open(out_path, "w", encoding="utf-8") as f:
    f.write("".join(output))

print(f"\nSaved: {out_path}")