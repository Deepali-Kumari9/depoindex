import pymupdf
import re
import json


PDF_PATH = "data/Persis_Yu_Deposition_Problem_statement.pdf"
OUTPUT_PATH = "outputs/canonical_transcript.json"


def get_printed_page_number(text):
    """
    Extract the printed transcript page number from the page footer.
    Example: 'Page 7' -> 7
    """
    match = re.search(r"Page\s+(\d+)\s*$", text, re.MULTILINE)

    if match:
        return int(match.group(1))

    return None


def extract_transcript(pdf_path):
    doc = pymupdf.open(pdf_path)

    records = []
    testimony_started = False
    testimony_ended = False
    end_marker_found = False

    for pdf_page_index, page in enumerate(doc):

        if testimony_ended:
            break

        text = page.get_text("text", sort=True)

        printed_page = get_printed_page_number(text)

        if printed_page is None:
            continue

        for raw_line in text.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            # Start collecting from the actual examination
            if not testimony_started:
                if "BY MR. PURCELL:" in line:
                    testimony_started = True
                else:
                    continue

            # Ignore page footer
            if re.fullmatch(r"Page\s+\d+", line):
                continue

            # Detect transcript line number
            line_match = re.match(r"^(\d{1,2})\s+(.*)$", line)

            if not line_match:
                continue

            line_number = int(line_match.group(1))
            content = line_match.group(2).strip()

            if not content:
                continue

            # Remove timestamp from the end of the line
            content = re.sub(
                r"\s+\d{2}:\d{2}$",
                "",
                content
            ).strip()

            # Save the record
            records.append({
                "pdf_page_index": pdf_page_index,
                "printed_page": printed_page,
                "line": line_number,
                "text": content,
                "source_ref": f"{printed_page}:{line_number}"
            })

            # The PDF splits the ending sentence across two lines.
            # Line 12 contains "this concludes today's testimony".
            if end_marker_found:
                testimony_ended = True
                break
            if "this concludes today's testimony" in content.lower():
                end_marker_found = True

    doc.close()

    return records


if __name__ == "__main__":

    records = extract_transcript(PDF_PATH)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            records,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Extracted records: {len(records)}")
    print(f"Saved to: {OUTPUT_PATH}")