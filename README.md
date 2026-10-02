# DepoIndex

AI-Powered Deposition Topic Index

## Overview

DepoIndex extracts meaningful topics and topic transitions from a deposition transcript while preserving exact page-and-line provenance.

The project processes the Persis Yu deposition through a provenance-preserving pipeline and produces a validated topic index that can be searched and reviewed through a Streamlit interface.

A key design principle is that **LLM output is treated as a candidate result rather than ground truth**. The generated topics are checked using deterministic provenance validation and semantic grounding validation before being presented to the user.

## Problem

Deposition transcripts contain long discussions that move between subjects, return to earlier subjects, and sometimes contain brief digressions.

The goal of DepoIndex is to:

- Identify meaningful deposition topics and transitions.
- Preserve exact page:line references for every topic.
- Maintain provenance through extraction, preprocessing, chunking, LLM processing, and validation.
- Produce a structured topic index for review.
- Ground LLM-generated topics in the original transcript evidence.
- Evaluate topic quality manually.
- Measure segmentation stability across repeated LLM runs.

## Pipeline

```text
PDF
-> Canonical Transcript Extraction
-> Transcript Cleaning
-> Semantic Preprocessing
-> Provenance-Preserving Chunking
-> Batched LLM Topic Extraction
-> Boundary Refinement
-> Provenance Validation
-> Semantic Grounding Validation
-> Topic Index Generation
-> Streamlit Interface
```

Validation:

```text
Manual Evaluation + Provenance Validation + Boundary Validation
+ Semantic Grounding Validation + Stability Evaluation + Failure Analysis
```

## Architecture

### 1. Transcript Extraction

The deposition PDF is converted into canonical transcript records.

Each record contains:

- PDF page index
- Printed page number
- Line number
- Original transcript text
- Exact `page:line` source reference

The canonical transcript contains **2,027 records**, beginning at `7:11` and ending at `88:13`.

The canonical transcript is treated as the source of truth for downstream provenance validation.

### 2. Transcript Cleaning

Non-substantive procedural transcript records are removed from semantic processing while the original canonical transcript remains unchanged.

This includes procedural records such as:

- Simultaneous speakers
- Record read
- Brief recesses

The cleaning stage preserves the original source references so that the underlying testimony can still be traced back to the canonical transcript.

### 3. Semantic Preprocessing

A separate semantic representation of each transcript record is created before LLM processing.

The preprocessing currently performs lightweight NLP normalization:

- Whitespace normalization
- Removal of `Q` / `A` speaker labels from the semantic copy

The original transcript text is never overwritten.

For example:

```text
Original:
Q    Good afternoon, Ms. Yu.  My name's John Purcell.

Semantic text:
Good afternoon, Ms. Yu. My name's John Purcell.
```

This allows the LLM to work with a cleaner semantic representation while preserving the original text and provenance for verification.

### 4. Provenance-Preserving Chunking

The cleaned transcript is divided into manageable chunks while retaining the original page-and-line references.

- The full transcript produces **51 chunks** using a chunk size of **40 transcript records**.
- Each chunk retains the source references required to map LLM output back to the original deposition.

For LLM requests, chunk metadata such as chunk ID, transcript range, printed-page range, and record count is supplied alongside the transcript records. This helps control context and reference location without replacing transcript evidence with metadata.

### 5. LLM Topic Extraction

Google Gemini is used to identify meaningful topics from groups of transcript chunks.

The implementation processes **up to five chunks per request** to reduce API usage while keeping the LLM context manageable.

The final extraction pipeline produced **39 topic candidates**.

Each candidate contains structured information such as:

- Topic label
- Start reference
- End reference
- Evidence references
- Source chunk IDs
- Related-topic information where available

The LLM is responsible for the semantic task of identifying candidate topics and evidence. Deterministic Python code is responsible for organizing and validating the results.

### 6. Topic Refinement and Boundary Refinement

LLM results are refined and globally ordered using the original transcript references.

Topic source chunks are derived deterministically from the final page-and-line boundaries. Batch-local `related_to` references are converted to global topic IDs before the final index is generated.

Overlapping or semantically misplaced topic boundaries are then refined using transcript context. Failed boundary checks are automatically re-evaluated against the canonical transcript, and the selected start/end references are constrained to valid transcript records.

The final refined topic output contains **39 topics**.

The latest refinement pass corrected **3 failed semantic boundaries** automatically and preserved valid evidence references within the corrected boundaries.

### 7. Provenance Validation

Every final topic is checked against the canonical transcript.

Validation verifies that:

- `start_ref` exists.
- `end_ref` exists.
- Every evidence reference exists.
- The start reference occurs before or at the end reference.
- Evidence references fall within the topic boundaries.

The validator does not silently repair invalid references. Invalid references are treated as validation failures.

Current final validation result:

| Check | Result |
|---|---|
| Canonical transcript records | 2,027 |
| Topics checked | 39 |
| Errors found | 0 |
| Validation | **PASSED** |

### 8. Semantic Grounding Validation

Structural provenance alone does not guarantee that a topic is actually supported by its evidence.

DepoIndex therefore performs a second validation step using Gemini. For each topic, the selected evidence references are checked against the topic description to determine whether the evidence supports the generated topic.

The final validation result was:

| Check | Result |
|---|---|
| Topics validated | 39 |
| Passed | 39 |
| Failed | 0 |

Therefore, **39/39 final topics passed semantic grounding validation**.

This provides an additional check beyond simply verifying that the referenced page-and-line numbers exist.

## Boundary Validation

A separate boundary validator checks whether each topic begins and ends at semantically appropriate transcript locations. The validator combines structural checks with transcript-context review and does not accept invalid references.

Final result:

| Check | Result |
|---|---|
| Topics validated | 39 |
| LLM boundary checks passed | 39 |
| LLM boundary checks failed | 0 |
| Structural boundary errors | 0 |
| Topic overlaps | 0 |

When semantic boundary checks fail, `src/validation/refine_failed_boundaries.py` automatically re-evaluates the affected topic using surrounding canonical transcript context and updates the boundary only to valid source references.

## Output

The final validated topic index contains **39 topics**.

Each topic includes:

- Topic ID
- Topic label
- Start page:line
- End page:line
- Evidence references
- Source chunk IDs

Example:

```text
Topic: Deposition ground rules and introductory instructions
Start: 7:11
End: 8:23
```

Output files:

- Validated topic index: `outputs/validated_topic_index.json`
- Semantic grounding validation report: `outputs/semantic_grounding_validation.json`
- Human-readable topic index: `outputs/deposition_topic_index.md`

## Evaluation

### Manual Evaluation

The first 20 topic entries were manually reviewed using:

- Location accuracy
- Topic relevance
- Boundary quality
- Coverage
- Redundancy

Results:

| Metric | Result |
|---|---|
| Location accuracy | 20/20 (100%) |
| Topic relevance | 20/20 (100%) |
| Boundary quality | 17/20 (85%) |
| Coverage | 20/20 (100%) |
| Redundancy | 19/20 (95%) |

The main boundary observations involved reporter interruptions, topic transitions, and broad topics containing potential subthemes.

### Stability Evaluation

An earlier complete-deposition stability experiment processed the same deposition three times using the same transcript, chunking configuration, batch size, and extraction pipeline.

Each run processed:

- 2,027 canonical transcript records
- Printed pages 7-88
- 51 transcript chunks
- Batch size of 5 chunks per LLM request

Results from that evaluation were:

| Run | Topics | Provenance |
|---|---:|---|
| Run 1 | 43 | Valid |
| Run 2 | 42 | Valid |
| Run 3 | 45 | Valid |

Topic counts varied across runs, showing that LLM-based segmentation is not fully deterministic.

Under a strict comparison of topic label, start reference, and end reference, **one topic was identical across all three runs**.

Pairwise exact matches:

| Comparison | Exact matches |
|---|---:|
| Run 1 vs Run 2 | 8 |
| Run 1 vs Run 3 | 3 |
| Run 2 vs Run 3 | 4 |

Despite segmentation variation, all three runs had valid provenance:

- Run 1: 0 invalid boundary references, 0 invalid evidence references
- Run 2: 0 invalid boundary references, 0 invalid evidence references
- Run 3: 0 invalid boundary references, 0 invalid evidence references

This experiment demonstrates that LLM segmentation can vary in topic granularity and boundary selection even when the underlying source addressing remains valid.

Detailed failure analysis is documented in [`docs/segmentation_failure_cases.md`](docs/segmentation_failure_cases.md).

The stability report is stored in:

`outputs/stability_report.json`

> **Note:** the three-run stability experiment is an earlier evaluation artifact and is not presented as a new post-preprocessing stability measurement.

## Streamlit Interface

DepoIndex includes an attorney-facing Streamlit interface for exploring the validated topic index.

The interface provides:

- Topic search
- Topic start/end references
- Evidence references
- Source chunk information
- Transcript evidence lines
- Page-and-line transcript navigation
- Configurable transcript context

The current validated topic index contains **39 topics**.

Run locally with:

```bash
python -m streamlit run app.py
```

Then open:

`http://localhost:8501`

Live demo:

https://deepali-kumari9-depoindex-app-ew2v6l.streamlit.app/

### Bonus: Attorney-Facing Source Navigation

The interface provides direct navigation from a `page:line` reference to the corresponding deposition testimony, with configurable surrounding context.

This is useful because an indexed topic can be verified against the underlying testimony without manually searching the full deposition.

The feature directly supports the auditability requirement of the topic index.

## Submission Artifacts

- [Validation Report](docs/validation_report.md)
- [5-Slide Presentation](docs/DepoIndex_Presentation.pdf)
- [Human-Readable Topic Index](outputs/deposition_topic_index.md)
- [Validated Topic Index JSON](outputs/validated_topic_index.json)
- [Semantic Grounding Validation](outputs/semantic_grounding_validation.json)

## Project Structure

```text
depoindex/
|-- app.py
|-- data/
|   `-- Persis_Yu_Deposition_Problem_statement.pdf
|      (supplied assignment PDF; not committed)
|-- docs/
|   |-- DepoIndex_Presentation.pdf
|   |-- segmentation_failure_cases.md
|   `-- validation_report.md
|-- evaluation/
|   |-- evaluate_baseline.py
|   |-- evaluate_manual.py
|   |-- evaluate_stability.py
|   `-- manual_evaluation.json
|-- outputs/
|   |-- canonical_transcript.json
|   |-- cleaned_transcript.json
|   |-- cleaning_report.json
|   |-- transcript_chunks.json
|   |-- batched_topics.json
|   |-- refined_topics.json
|   |-- validated_topic_index.json
|   |-- semantic_grounding_validation.json
|   |-- boundary_validation.json
|   |-- deposition_topic_index.md
|   |-- stability_run_1.json
|   |-- stability_run_2.json
|   |-- stability_run_3.json
|   `-- stability_report.json
|-- src/
|   |-- extraction/
|   |-- nlp/
|   |   `-- preprocess_transcript.py
|   |-- llm/
|   |-- segmentation/
|   `-- validation/
|       |-- build_topic_index.py
|       |-- validate_provenance.py
|       |-- validate_semantic_grounding.py
|       |-- validate_boundaries.py
|       |-- refine_failed_boundaries.py
|       `-- generate_markdown_index.py
|-- .gitignore
|-- llm_usage.md
|-- methodology.md
|-- requirements.txt
`-- README.md
```

## Setup

### Requirements

- Python 3.10+ (tested with Python 3.11)
- Google Gemini API key
- Dependencies listed in `requirements.txt`

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```text
GEMINI_API_KEY=your_api_key_here
```

The API key is kept outside version control.

### Source Deposition PDF

The original deposition PDF is not included in this repository because it was provided as assignment material.

To re-run extraction from scratch, place the supplied PDF at:

```text
data/Persis_Yu_Deposition_Problem_statement.pdf
```

The pre-extracted canonical transcript and downstream outputs are included in `outputs/`, so the completed results can be reviewed without the original PDF.

## Running the Full Pipeline

The committed outputs in `outputs/` contain the results of the completed extraction, segmentation, validation, and evaluation workflow.

To regenerate the pipeline from the supplied deposition PDF, first place the PDF at:

```text
data/Persis_Yu_Deposition_Problem_statement.pdf
```

Run the processing stages in order:

```bash
# 1. Extract canonical transcript records with page:line provenance
python src/extraction/extract_transcript.py

# 2. Clean transcript and create semantic representations
python src/extraction/clean_transcript.py

# 3. Create provenance-preserving transcript chunks
python src/segmentation/chunk_transcript.py

# 4. Run batched LLM topic extraction
#    Requires GEMINI_API_KEY in .env
python src/llm/batched_extract.py

# 5. Refine and globally order extracted topics
python src/segmentation/refine_topics.py

# 6. Validate final topic provenance
python src/validation/validate_provenance.py

# 7. Validate topic boundaries against transcript context
#    Requires GEMINI_API_KEY in .env
python src/validation/validate_boundaries.py

# 8. Refine any failed semantic boundaries automatically
#    Requires GEMINI_API_KEY in .env
python src/validation/refine_failed_boundaries.py

# 9. Validate semantic grounding of topic evidence
#    Requires GEMINI_API_KEY in .env
python src/validation/validate_semantic_grounding.py

# 10. Build the validated topic index for the application
python src/validation/build_topic_index.py

# 11. Generate the human-readable Markdown topic index
python src/validation/generate_markdown_index.py
```

The manual evaluation and stability results included in this repository are evaluation artifacts from the completed validation process.

They are documented in:

- [`docs/validation_report.md`](docs/validation_report.md)
- [`docs/segmentation_failure_cases.md`](docs/segmentation_failure_cases.md)

The full pipeline requires a valid Gemini API key for the LLM extraction and semantic grounding stages.

## Reproducibility

A fresh-clone reproducibility test was previously performed from the GitHub repository.

The test verified:

- Repository cloning
- Fresh virtual environment creation
- Dependency installation
- Dependency consistency using `pip check`
- Provenance validation against the canonical transcript
- Streamlit application startup

The fresh-clone environment successfully installed all dependencies declared in `requirements.txt`.

`pip check` reported:

```text
No broken requirements found.
```

The repository also contains the final validated topic index and semantic grounding validation report generated from the current pipeline.

The Streamlit application can be started with:

```bash
python -m streamlit run app.py
```

The reproducibility test previously identified a missing Streamlit dependency in `requirements.txt`. This was fixed in:

```text
3e61f80 fix: declare streamlit dependency for reproducible setup
```

After the fix, the declared dependencies successfully supported the Streamlit application.

## AI Usage

AI-assisted development is documented in:

`llm_usage.md`

The document records:

- AI tools used
- AI-generated suggestions
- Implementation decisions
- Changes made to suggestions
- Validation performed
- Baseline experiments
- Batched LLM processing
- API errors and their handling

No fabricated successful results were used from failed API experiments.

## Methodology

The overall technical methodology is documented in:

`methodology.md`

It covers:

- Transcript extraction
- Transcript cleaning
- Semantic preprocessing
- Provenance preservation
- Chunking
- Topic segmentation
- Boundary refinement
- Provenance validation
- Semantic grounding validation
- Manual evaluation
- Stability testing
- Failure analysis

## Git Engineering History

The project was developed incrementally rather than as a single final commit.

Important milestones include:

```text
42dbffb feat: add provenance-preserving transcript chunking
7837e6c feat: add baseline LLM topic extraction
06fdbc2 test: evaluate baseline topic segmentation
14b6056 feat: refine topic boundaries and merge related segments
3303704 test: add deterministic provenance validation
17a5384 feat: add validated topic index schema and output generation
44c7cd3 feat: generate human-readable deposition topic index
911a395 feat: improve LLM extraction with batched requests
181572d test: add manual topic index evaluation
9e4f7a5 test: measure three-run pipeline stability
cf67e30 docs: document segmentation failure cases
77d3770 feat: add attorney-facing topic index interface
3e61f80 fix: declare streamlit dependency for reproducible setup
ead75a0 docs: complete reproducibility and AI usage documentation
26b631c docs: update segmentation failure analysis
d889052 test: update complete-deposition stability evaluation
936c2f1 docs: clarify model usage and clean submission README
0ec4d6c docs: improve README formatting and Git history
59b7095 fix: add transcript cleaning and strict provenance validation
aadc0cc feat: add semantic transcript preprocessing
ec70767 feat: add semantic grounding validation
d8d6bb8 fix: refresh validated topic index
```

### Latest Commit

```text
e446ac2 Finalize validated topic extraction pipeline
```

This commit added the final batched extraction, boundary validation/refinement, refreshed validation artifacts, and updated the final topic outputs.

### Meaningful Earlier Commit

Earlier validation milestone:

```text
9e4f7a5 test: measure three-run pipeline stability
```

This commit is meaningful because it established an empirical finding that LLM topic segmentation varied across repeated runs and motivated treating LLM output as non-deterministic rather than assuming identical results.

The stability experiment was subsequently expanded and corrected to cover the complete deposition, with the complete-deposition evaluation captured in:

```text
d889052 test: update complete-deposition stability evaluation
```

## Latest Project State

The latest repository state includes:

- Lightweight semantic transcript preprocessing
- Metadata-controlled, provenance-preserving chunking
- Batched Gemini topic extraction
- Strict provenance validation
- Automatic boundary refinement
- Boundary validation against transcript context
- Semantic grounding validation
- 39-topic validated index
- Updated Streamlit output

Latest commit:

```text
e446ac2 Finalize validated topic extraction pipeline
```

The latest changes were pushed to `origin/main`.

## Limitations

- LLM topic segmentation can vary between runs.
- Topic boundaries may occasionally be broader or narrower than ideal.
- Manual evaluation was performed on a 20-topic sample rather than the complete 39-topic index.
- The current system has been evaluated on a single deposition.
- Topic re-entry and closely related topics may require further refinement.
- The current semantic preprocessing is lightweight NLP normalization rather than a full NLP pipeline.
- The application is intended as a working technical prototype rather than a production legal system.

## Future Improvements

- More systematic topic-boundary scoring
- Better detection of topic re-entry
- Hierarchical parent/child topic relationships
- Semantic relationships between related topics
- Larger-scale evaluation across depositions
- More advanced source navigation
- Improved attorney-facing search and review workflows
- More comprehensive automated boundary-quality evaluation