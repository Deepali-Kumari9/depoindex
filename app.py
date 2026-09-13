import json
import streamlit as st

TOPICS_PATH = "outputs/validated_topic_index.json"
TRANSCRIPT_PATH = "outputs/canonical_transcript.json"


# -----------------------------
# Page configuration
# -----------------------------

st.set_page_config(
    page_title="DepoIndex",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------
# Data loading
# -----------------------------

@st.cache_data
def load_topics():
    with open(TOPICS_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data["topics"]


@st.cache_data
def load_transcript():
    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def build_reference_map(records):
    return {
        record["source_ref"]: record
        for record in records
    }


# -----------------------------
# Custom styling
# -----------------------------

st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.4rem;
            font-weight: 700;
            margin-bottom: 0.15rem;
        }

        .subtitle {
            font-size: 1.05rem;
            color: #666;
            margin-bottom: 1.5rem;
        }

        .provenance-box {
            padding: 0.8rem 1rem;
            border-radius: 8px;
            border: 1px solid #ddd;
            background-color: #fafafa;
            margin: 0.5rem 0 1rem 0;
        }

        .ref-label {
            font-size: 0.82rem;
            color: #666;
            margin-bottom: 0.15rem;
        }

        .ref-value {
            font-size: 1.05rem;
            font-weight: 600;
        }

        .evidence-line {
            padding: 0.55rem 0.75rem;
            margin: 0.35rem 0;
            border-left: 3px solid #888;
            background-color: #fafafa;
            border-radius: 4px;
        }

        .selected-line {
            padding: 0.65rem 0.8rem;
            margin: 0.35rem 0;
            border-left: 4px solid #111;
            background-color: #f0f0f0;
            border-radius: 4px;
            font-weight: 600;
        }

        .small-note {
            color: #777;
            font-size: 0.85rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Load data
# -----------------------------

topics = load_topics()
transcript = load_transcript()

reference_map = build_reference_map(transcript)


# -----------------------------
# Header
# -----------------------------

st.markdown(
    '<div class="main-title">📑 DepoIndex</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "AI-powered deposition topic indexing with exact page-line provenance"
    "</div>",
    unsafe_allow_html=True,
)


# -----------------------------
# Summary metrics
# -----------------------------

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric("Indexed Topics", len(topics))

with metric2:
    st.metric("Transcript Records", len(transcript))

with metric3:
    unique_pages = len(
        {
            record["printed_page"]
            for record in transcript
            if record.get("printed_page") is not None
        }
    )
    st.metric("Deposition Pages", unique_pages)


st.divider()


# -----------------------------
# Sidebar
# -----------------------------

with st.sidebar:

    st.header("🔎 Explore")

    search_query = st.text_input(
        "Search topics",
        placeholder="e.g. student loans, ITT, RICO",
    )

    st.caption(
        "Search matches topic names. "
        "Use the transcript viewer below for exact provenance lookup."
    )

    st.divider()

    st.header("📍 Source Testimony")

    reference_input = st.text_input(
        "Enter page:line",
        placeholder="e.g. 25:8",
    )

    context_lines = st.slider(
        "Context lines",
        min_value=1,
        max_value=5,
        value=2,
    )

    st.caption(
        "View the selected testimony line with nearby transcript context."
    )

    st.divider()

    st.markdown("### Dataset")

    st.write(f"**Topics:** {len(topics)}")
    st.write(f"**Transcript records:** {len(transcript)}")
    st.write(f"**Pages:** {unique_pages}")


# -----------------------------
# Filter topics
# -----------------------------

if search_query.strip():

    query = search_query.lower().strip()

    filtered_topics = [
        topic
        for topic in topics
        if query in topic["topic"].lower()
    ]

else:
    filtered_topics = topics


# -----------------------------
# Topic section
# -----------------------------

st.subheader("Topic Index")

st.write(
    f"Showing **{len(filtered_topics)}** of **{len(topics)}** indexed topics."
)

if not filtered_topics:

    st.info(
        "No topics matched your search. "
        "Try a broader keyword such as 'loan', 'servicing', or 'CFPB'."
    )


# -----------------------------
# Topic cards
# -----------------------------

for topic in filtered_topics:

    title = f"{topic['topic_id']}  —  {topic['topic']}"

    with st.expander(title):

        # Provenance
        start_col, end_col = st.columns(2)

        with start_col:
            st.markdown(
                """
                <div class="provenance-box">
                    <div class="ref-label">START</div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="ref-value">{topic["start_ref"]}</div>',
                unsafe_allow_html=True,
            )

            st.markdown("</div>", unsafe_allow_html=True)

        with end_col:
            st.markdown(
                """
                <div class="provenance-box">
                    <div class="ref-label">END</div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="ref-value">{topic["end_ref"]}</div>',
                unsafe_allow_html=True,
            )

            st.markdown("</div>", unsafe_allow_html=True)

        # Overview
        overview_col1, overview_col2 = st.columns(2)

        with overview_col1:
            st.metric(
                "Evidence references",
                len(topic["evidence_refs"]),
            )

        with overview_col2:
            st.metric(
                "Source chunks",
                len(topic.get("source_chunk_ids", [])),
            )

        st.markdown("### Evidence")

        for ref in topic["evidence_refs"]:

            record = reference_map.get(ref)

            if record:

                st.markdown(
                    f"""
                    <div class="evidence-line">
                        <strong>{ref}</strong>
                        &nbsp; — &nbsp;
                        {record["text"]}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                st.warning(
                    f"{ref} — Transcript line not found."
                )

        # Related topics
        related_topics = topic.get("related_to", [])

        if related_topics:

            st.markdown("### Related topics")

            related_names = []

            topic_map = {
                item["topic_id"]: item
                for item in topics
            }

            for related_id in related_topics:

                related_topic = topic_map.get(
                    f"T{int(related_id):02d}"
                    if isinstance(related_id, int)
                    else str(related_id)
                )

                if related_topic:

                    related_names.append(
                        f"{related_topic['topic_id']} — "
                        f"{related_topic['topic']}"
                    )

            if related_names:

                for name in related_names:
                    st.write(f"• {name}")

        # Source chunks
        source_chunks = topic.get("source_chunk_ids", [])

        if source_chunks:

            st.markdown(
                '<div class="small-note">'
                "<strong>Source chunks:</strong> "
                + ", ".join(str(chunk) for chunk in source_chunks)
                + "</div>",
                unsafe_allow_html=True,
            )


# -----------------------------
# Transcript viewer
# -----------------------------

if reference_input.strip():

    reference = reference_input.strip()

    if reference not in reference_map:

        st.sidebar.error(
            f"Reference `{reference}` was not found."
        )

    else:

        target_index = next(
            index
            for index, record in enumerate(transcript)
            if record["source_ref"] == reference
        )

        start_index = max(
            0,
            target_index - context_lines,
        )

        end_index = min(
            len(transcript),
            target_index + context_lines + 1,
        )

        st.sidebar.success(
            f"Source testimony found: {reference}"
        )

        st.sidebar.markdown("### Transcript context")

        for record in transcript[start_index:end_index]:

            if record["source_ref"] == reference:

                st.sidebar.markdown(
                    f"""
                    <div class="selected-line">
                        → {record["source_ref"]} — {record["text"]}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                st.sidebar.markdown(
                    f"""
                    <div class="evidence-line">
                        {record["source_ref"]} — {record["text"]}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# -----------------------------
# Footer
# -----------------------------

st.divider()

st.caption(
    "DepoIndex • AI-assisted topic segmentation • "
    "Exact page-line provenance • Deterministic validation"
)