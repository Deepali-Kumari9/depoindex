# DepoIndex

AI-Powered Deposition Topic Index

## Overview

DepoIndex extracts meaningful topics and topic transitions from a deposition transcript while preserving exact page-and-line provenance.

The project processes the Persis Yu deposition through a provenance-preserving pipeline and produces a validated topic index that can be searched and reviewed through a Streamlit interface.

## Problem

Deposition transcripts contain long discussions that move between subjects, return to earlier subjects, and sometimes contain brief digressions.

The goal of DepoIndex is to:

- Identify meaningful deposition topics and transitions.
- Preserve exact page:line references for every topic.
- Maintain provenance through extraction, chunking, LLM processing, and validation.
- Produce a structured topic index for review.
- Evaluate topic quality manually.
- Measure segmentation stability across repeated LLM runs.

## Pipeline

PDF
→ Canonical Transcript Extraction
→ Provenance-Preserving Chunking
→ LLM Topic Extraction
→ Boundary Refinement
→ Provenance Validation
→ Topic Index Generation
→ Manual Evaluation
→ Three-Run Stability Evaluation
→ Streamlit Interface


## Architecture

### 1. Transcript Extraction

The deposition PDF is converted into canonical transcript records.

Each record contains:

- PDF page index
- Printed page number
- Line number
- Transcript text
- Exact `page:line` source reference

The canonical transcript contains **2,027 records**, beginning at `7:11` and ending at `88:13`.

### 2. Provenance-Preserving Chunking

The canonical transcript is divided into manageable chunks while retaining the original page-and-line references.

The full transcript produces **51 chunks** using a chunk size of 40 records.

### 3. LLM Topic Extraction

Google Gemini is used to identify meaningful topics from groups of transcript chunks.

The implementation processes five consecutive chunks per request to reduce API usage while still allowing topics to span chunk boundaries.

The complete transcript produced **57 raw topic candidates** in the main extraction run.

### 4. Boundary Refinement

LLM results are sorted globally by transcript position and assigned deterministic topic IDs.

Topic source chunks are derived from the actual page-and-line references rather than trusting batch-local relationships returned by the model.

### 5. Provenance Validation

Every topic is checked against the canonical transcript.

Validation verifies that:

- `start_ref` exists.
- `end_ref` exists.
- Every evidence reference exists.
- Start occurs before or at the end.
- Evidence references fall within topic boundaries.

Current validation result:

- Topics checked: 57
- Errors found: 0
- Validation: **PASSED**

## Output

The validated topic index contains **57 topics**.

Each topic includes:

- Topic ID
- Topic label
- Start page:line
- End page:line
- Evidence references
- Source chunk IDs

Example:

```text
Topic: Deposition ground rules and admonitions
Start: 7:15
End: 8:23
```

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

### Three-Run Stability Evaluation

The complete deposition was processed three times using the same transcript, chunking configuration, batch size, and extraction pipeline.

Each run processed:

- 2,027 canonical transcript records
- Printed pages 7–88
- 51 transcript chunks
- Batch size of 5 chunks per LLM request

Results:

| Run | Topics | Provenance |
|---|---|---|
| Run 1 | 43 | Valid |
| Run 2 | 42 | Valid |
| Run 3 | 45 | Valid |

Topic counts varied across runs, showing that LLM-based segmentation is not fully deterministic.

Under a strict comparison of topic label, start reference, and end reference, one topic was identical across all three runs.

Pairwise exact matches were:

- Run 1 vs Run 2: 8
- Run 1 vs Run 3: 3
- Run 2 vs Run 3: 4

Despite segmentation variation, all three runs had valid provenance:

- Run 1: 0 invalid boundary references, 0 invalid evidence references
- Run 2: 0 invalid boundary references, 0 invalid evidence references
- Run 3: 0 invalid boundary references, 0 invalid evidence references

The observed instability is primarily in topic granularity and boundary selection rather than source addressing.

Detailed failure analysis is documented in:
`docs/segmentation_failure_cases.md`

The complete three-run stability report is stored in:
`outputs/stability_report.json`

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

Run locally with:

```bash
streamlit run app.py
```

Then open:

http://localhost:8501


## Project Structure

depoindex/
├── app.py
├── docs/
│ └── segmentation_failure_cases.md
├── evaluation/
│ ├── evaluate_baseline.py
│ ├── evaluate_manual.py
│ ├── evaluate_stability.py
│ └── manual_evaluation.json
├── outputs/
│ ├── canonical_transcript.json
│ ├── transcript_chunks.json
│ ├── batched_topics.json
│ ├── refined_topics.json
│ ├── validated_topic_index.json
│ ├── deposition_topic_index.md
│ ├── stability_subset_19_34.json
│ ├── stability_chunks_19_34.json
│ ├── stability_run_1.json
│ ├── stability_run_2.json
│ ├── stability_run_3.json
│ └── stability_report.json
├── src/
│ ├── extraction/
│ ├── llm/
│ ├── segmentation/
│ └── validation/
├── .gitignore
├── llm_usage.md
├── methodology.md
├── requirements.txt
└── README.md


## Setup

### Requirements

- Python 3.10+
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

GEMINI_API_KEY=your_api_key_here


The API key is kept outside version control.

## Reproducibility

A fresh-clone reproducibility test was performed from the GitHub repository.

The test verified:

- Repository cloning
- Fresh virtual environment creation
- Dependency installation
- Dependency consistency using `pip check`
- Provenance validation against the canonical transcript
- Streamlit application startup

The fresh-clone environment successfully installed all dependencies declared in `requirements.txt`.

`pip check` reported:

No broken requirements found.


Provenance validation in the fresh clone reported:

- Canonical transcript records: 2,027
- Batches checked: 11
- Topics checked: 57
- Errors found: 0

The Streamlit application also started successfully at:
`http://localhost:8501`

The reproducibility test previously identified a missing Streamlit dependency in `requirements.txt`. This was fixed in:

3e61f80 fix: declare streamlit dependency for reproducible setup


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

This covers:

- Transcript extraction
- Provenance preservation
- Chunking
- Topic segmentation
- Boundary refinement
- Provenance validation
- Manual evaluation
- Stability testing
- Failure analysis

## Git Engineering History

The project was developed incrementally rather than as a single final commit.

Important milestones include:

181572d test: add manual topic index evaluation
9e4f7a5 test: measure three-run pipeline stability
cf67e30 docs: document segmentation failure cases
77d3770 feat: add attorney-facing topic index interface
3e61f80 fix: declare streamlit dependency for reproducible setup
ead75a0 docs: complete reproducibility and AI usage documentation
26b631c docs: update segmentation failure analysis
d889052 test: update complete-deposition stability evaluation


The history records meaningful implementation, testing, failure analysis, interface development, reproducibility fixes, and complete-deposition stability evaluation.

### Meaningful Earlier Commit

Earlier validation milestone:

9e4f7a5 test: measure three-run pipeline stability


This commit is meaningful because it established an initial empirical finding that LLM topic segmentation varied across repeated runs and motivated treating LLM output as non-deterministic rather than assuming identical results.

The stability experiment was subsequently expanded and corrected to cover the complete deposition, with the final complete-deposition evaluation captured in commit:

d889052 test: update complete-deposition stability evaluation


### Final Submission Commit

To be filled after the final submission documentation and packaging commits are completed:

FINAL_SUBMISSION_SHA


## Limitations

- LLM topic segmentation can vary between runs.
- Topic boundaries may occasionally be broader or narrower than ideal.
- Manual evaluation was performed on a 20-topic sample rather than the complete 57-topic index.
- The current system focuses on a single deposition.
- Topic re-entry and closely related topics may require further refinement.
- The application is intended as a working technical prototype rather than a production legal system.

## Future Improvements

Potential improvements include:

- More systematic topic-boundary scoring
- Better detection of topic re-entry
- Hierarchical parent/child topic relationships
- Semantic relationships between related topics
- Larger-scale evaluation across depositions
- More advanced source navigation
- Improved attorney-facing search and review workflows