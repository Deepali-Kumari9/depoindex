import json
import re
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from nlp.preprocess_transcript import preprocess_record


INPUT_FILE = Path("outputs/canonical_transcript.json")
OUTPUT_FILE = Path("outputs/cleaned_transcript.json")
REPORT_FILE = Path("outputs/cleaning_report.json")


# These transcript records are procedural/non-substantive
# and should not be sent to the semantic topic extraction stage.
PROCEDURAL_PATTERNS = [
    r"^\(Simultaneous speakers\.\)$",
    r"^\(A brief recess was taken\.\)$",
    r"^\(Record read\.\)$",
]


def is_procedural_record(text):
    """Return True if the record is only a procedural event."""
    text = text.strip()

    for pattern in PROCEDURAL_PATTERNS:
        if re.fullmatch(pattern, text, re.IGNORECASE):
            return True

    return False


def clean_transcript(records):
    cleaned = []
    excluded = []

    for record in records:
        text = record.get("text", "").strip()

        if is_procedural_record(text):
            excluded.append({
                "source_ref": record.get("source_ref"),
                "text": text,
                "reason": "procedural_non_substantive"
            })
        else:
            cleaned.append(preprocess_record(record))

    return cleaned, excluded


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    cleaned, excluded = clean_transcript(records)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    report = {
        "input_records": len(records),
        "kept_records": len(cleaned),
        "excluded_records": len(excluded),
        "excluded": excluded
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("=== Transcript Cleaning ===")
    print(f"Input records    : {len(records)}")
    print(f"Kept records     : {len(cleaned)}")
    print(f"Excluded records : {len(excluded)}")

    if excluded:
        print("\nExcluded records:")
        for item in excluded:
            print(
                f" - {item['source_ref']}: "
                f"{item['text']}"
            )

    print(f"\nCreated: {OUTPUT_FILE}")
    print(f"Created: {REPORT_FILE}")


if __name__ == "__main__":
    main()