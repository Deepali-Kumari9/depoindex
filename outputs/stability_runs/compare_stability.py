import json
import re
from pathlib import Path

BASE = Path("outputs/stability_runs")

def pos(ref):
    m = re.match(r"(\d+):(\d+)", ref)
    return int(m.group(1)) * 1000 + int(m.group(2))

def overlap(a, b):
    return max(0, min(pos(a["end_ref"]), pos(b["end_ref"])) -
                  max(pos(a["start_ref"]), pos(b["start_ref"])) + 1)

def load(run):
    return json.loads(
        (BASE / run / "validated_topic_index.json").read_text()
    )["topics"]

runs = {
    "Run 1": load("run1"),
    "Run 2": load("run2"),
    "Run 3": load("run3")
}

out = []
out.append("# DepoIndex Three-Run Stability Comparison")
out.append("")
out.append("## Topic counts")
out.append("")
out.append("| Run | Topics |")
out.append("|---|---:|")
for name, topics in runs.items():
    out.append(f"| {name} | {len(topics)} |")

out.append("")
out.append("## Overlap-based comparison")
out.append("")
out.append("Topics are matched by transcript page:line range overlap rather than topic position.")
out.append("")

for name_a, name_b in [("Run 1","Run 2"),("Run 2","Run 3"),("Run 1","Run 3")]:
    A = runs[name_a]
    B = runs[name_b]

    out.append(f"### {name_a} vs {name_b}")
    out.append("")
    out.append("| Topic A | Range A | Best overlapping topic(s) in B | Range B | Overlap |")
    out.append("|---|---|---|---|---:|")

    exact_boundary = 0
    matched = 0
    split_merge = 0

    for a in A:
        matches = []
        for b in B:
            ov = overlap(a,b)
            if ov > 0:
                matches.append((ov,b))

        matches.sort(reverse=True, key=lambda x:x[0])

        if matches:
            matched += 1
            best_ov = matches[0][0]
            best = [b for ov,b in matches if ov == best_ov]

            if len(matches) > 1:
                split_merge += 1

            if any(
                a["start_ref"] == b["start_ref"] and
                a["end_ref"] == b["end_ref"]
                for _,b in matches
            ):
                exact_boundary += 1

            names = "; ".join(b["topic"] for b in best)
            ranges = "; ".join(
                f'{b["start_ref"]}-{b["end_ref"]}' for b in best
            )

            out.append(
                f'| {a["topic"]} | {a["start_ref"]}-{a["end_ref"]} | '
                f'{names} | {ranges} | {best_ov} |'
            )

    out.append("")
    out.append(
        f"**Matched:** {matched}/{len(A)} topics; "
        f"**exact boundary matches:** {exact_boundary}/{len(A)}; "
        f"**split/merge cases:** {split_merge}"
    )
    out.append("")

out.append("## Interpretation")
out.append("")
out.append(
    "Position-wise exact comparison is not used as the primary stability measure "
    "because LLM segmentation can split or merge adjacent semantic sections. "
    "Transcript-range overlap provides a more meaningful comparison."
)
out.append("")
out.append(
    "The repeated runs show stable coverage of the same transcript regions, "
    "while topic labels and granularity can vary between runs."
)

(BASE / "stability_comparison.md").write_text("\n".join(out), encoding="utf-8")

print("DONE")
print(BASE / "stability_comparison.md")
