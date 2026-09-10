import json

INPUT_PATH = "outputs/validated_topic_index.json"
OUTPUT_PATH = "outputs/deposition_topic_index.md"


def load_index(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def generate_markdown(data):
    topics = data["topics"]

    lines = [
        "# DepoIndex — Deposition Topic Index",
        "",
        f"Total topics: **{len(topics)}**",
        "",
        "---",
        "",
    ]

    for topic in topics:
        topic_id = topic["topic_id"]
        label = topic["topic"]
        start_ref = topic["start_ref"]
        end_ref = topic["end_ref"]
        evidence_refs = topic["evidence_refs"]

        lines.append(f"## {topic_id} — {label}")
        lines.append("")
        lines.append(f"**Range:** `{start_ref}` → `{end_ref}`")
        lines.append("")

        lines.append("**Evidence:**")
        lines.append("")

        for ref in evidence_refs:
            lines.append(f"- `{ref}`")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    data = load_index(INPUT_PATH)

    markdown = generate_markdown(data)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        file.write(markdown)

    print("=== DepoIndex Human-Readable Topic Index ===")
    print()
    print(f"Topics: {len(data['topics'])}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()