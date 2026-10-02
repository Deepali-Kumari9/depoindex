import re


def normalize_text(text):
    """
    Normalize transcript text for semantic processing.

    The original transcript text is never modified.
    """

    text = text.strip()

    # Normalize repeated whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove speaker labels from the semantic copy.
    # Example:
    # "Q    Did you receive the document?"
    # becomes:
    # "Did you receive the document?"
    text = re.sub(
        r"^(Q|A)\s+",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text.strip()


def preprocess_record(record):
    """
    Create a semantic version of one transcript record
    while preserving the original provenance.
    """

    processed = dict(record)

    original_text = record.get("text", "")
    processed["semantic_text"] = normalize_text(original_text)

    return processed