import json
import streamlit as st

TOPICS_PATH = "outputs/validated_topic_index.json"
TRANSCRIPT_PATH = "outputs/canonical_transcript.json"


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


def parse_ref(source_ref):
    page, line = source_ref.split(":")
    return int(page), int(line)


st.set_page_config(
    page_title="DepoIndex",
    page_icon="📑",
    layout="wide"
)

topics = load_topics()
transcript = load_transcript()
reference_map = build_reference_map(transcript)

st.title("📑 DepoIndex")
st.subheader("AI-Powered Deposition Topic Index")

st.write(
    "Search and explore topics from the Persis Yu deposition "
    "with exact page-line provenance."
)

st.divider()


# Sidebar
with st.sidebar:
    st.header("Topic Search")

    search_query = st.text_input(
        "Search by topic",
        placeholder="e.g. student loans, ITT, RICO"
    )

    st.divider()

    st.header("Transcript Viewer")

    reference_input = st.text_input(
        "Enter page:line",
        placeholder="e.g. 25:8"
    )

    context_lines = st.slider(
        "Context lines",
        min_value=1,
        max_value=5,
        value=2
    )

    st.divider()

    st.metric(
        "Indexed Topics",
        len(topics)
    )

    st.metric(
        "Transcript Records",
        len(transcript)
    )


# Filter topics
if search_query.strip():
    query = search_query.lower()

    filtered_topics = [
        topic
        for topic in topics
        if query in topic["topic"].lower()
    ]
else:
    filtered_topics = topics


st.write(
    f"Showing **{len(filtered_topics)}** of **{len(topics)}** topics"
)

st.divider()


# Topic cards
for topic in filtered_topics:

    title = f"{topic['topic_id']} — {topic['topic']}"

    with st.expander(title):

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Start**")
            st.code(topic["start_ref"])

        with col2:
            st.write("**End**")
            st.code(topic["end_ref"])

        st.write("### Topic Overview")

        overview_col1, overview_col2 = st.columns(2)

        with overview_col1:
            st.metric(
                "Evidence references",
                len(topic["evidence_refs"])
            )

        with overview_col2:
            st.metric(
                "Source chunks",
                len(topic.get("source_chunk_ids", []))
            )

        st.write("### Evidence")

        for ref in topic["evidence_refs"]:

            record = reference_map.get(ref)

            if record:
                st.markdown(
                    f"**{ref}** — {record['text']}"
                )
            else:
                st.markdown(
                    f"**{ref}** — Transcript line not found."
                )

        if topic.get("source_chunk_ids"):
            st.write(
                "**Source chunks:** "
                + ", ".join(
                    str(chunk_id)
                    for chunk_id in topic["source_chunk_ids"]
                )
            )


# Transcript viewer
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
            target_index - context_lines
        )

        end_index = min(
            len(transcript),
            target_index + context_lines + 1
        )

        st.sidebar.success(
            f"Showing transcript around {reference}"
        )

        for record in transcript[start_index:end_index]:

            if record["source_ref"] == reference:

                st.sidebar.markdown(
                    f"**→ {record['source_ref']} — {record['text']}**"
                )

            else:

                st.sidebar.write(
                    f"{record['source_ref']} — {record['text']}"
                )