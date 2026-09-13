# DepoIndex Methodology

## 1. Objective

DepoIndex converts a legal deposition transcript into a structured Topic Index.

Each topic contains:
- a meaningful topic label,
- start page:line reference,
- end page:line reference,
- evidence page:line references.

The most important requirement is preserving exact source provenance so that every generated topic can be traced back to the original deposition.

## 2. Processing Pipeline

The current pipeline is:

1. Extract the deposition transcript from the PDF.
2. Preserve the printed page number and transcript line number.
3. Store every transcript line with an exact `page:line` source reference.
4. Divide the canonical transcript into processing chunks.
5. Use an LLM to identify meaningful topics within transcript chunks.
6. Validate generated references against the canonical transcript.
7. Refine topic boundaries and preserve meaningful relationships between related segments.
8. Generate a structured Topic Index.
9. Generate a human-readable Topic Index.
10. Evaluate accuracy, coverage, redundancy, and stability.

## 3. Canonical Transcript Extraction

The source PDF contains both deposition material and other document material.

The extraction process identifies the testimony section beginning with the deposition examination and extracts numbered transcript lines.

Each extracted record contains:

- PDF page index
- printed deposition page
- transcript line number
- transcript text
- `source_ref`

The `source_ref` follows the format:

`page:line`

Example:

`7:11`

This reference is preserved throughout the downstream pipeline.

The canonical extraction contains 2,027 transcript records and ends at page 88, line 13, where the deposition testimony concludes.

## 4. Transcript Chunking

The canonical transcript is divided into sequential chunks to make LLM processing manageable.

The current pipeline uses chunks of 40 transcript records.

This produces 51 chunks.

Each chunk retains:
- chunk ID,
- starting source reference,
- ending source reference,
- all original transcript records.

No transcript line is rewritten or assigned a new artificial source reference during chunking.

## 5. Baseline LLM Extraction

The baseline uses Google Gemini 3.6 Flash.

The initial baseline used Gemini 3.6 Flash. After the baseline encountered free-tier quota limits, the batched pipeline switched to Gemini 3.5 Flash-Lite to allow higher free-tier throughput while retaining the same structured page:line provenance requirements.

The LLM receives transcript text together with its exact source references.

It is instructed to return structured JSON containing:

- topic
- start_ref
- end_ref
- evidence_refs

The baseline experiments demonstrated that the LLM can identify meaningful deposition topics while preserving exact page:line references.

The initial one-request-per-chunk approach was inefficient under the available API request quota, which motivated the batched extraction approach.

## 6. Baseline Findings

The initial baseline attempted all 51 chunks.

Four chunks were successfully processed before the available API request quota was reached.

The baseline findings showed that:

- independent chunks can fragment a topic across chunk boundaries;
- some topic labels can be verbose or closely related;
- evidence lists can contain more lines than are necessary;
- repeated LLM calls can produce small differences in labels or evidence selection;
- one-request-per-chunk processing is inefficient for the available API quota.

These findings motivated the batched extraction and refinement stages.

## 7. Refinement Strategy

The current pipeline processes transcript chunks in batches while preserving the original source references.

The LLM is instructed to identify meaningful topic boundaries using the supplied transcript context. Topics may cross chunk boundaries when the transcript supports a continuous subject.

The refinement stage:

- preserves chronological topic order;
- validates source references against the canonical transcript;
- records the source chunks associated with each topic;
- preserves valid batch-local `related_to` relationships by mapping them to global topic IDs;
- avoids extending a topic into unrelated discussion solely because a subject is mentioned again.

If a topic meaningfully reappears after an intervening discussion, it should normally be represented as a separate topic entry and linked to the earlier entry rather than incorrectly extending the original boundary.

All refinements preserve the original page:line references.

### Brief Digressions

Brief digressions are handled through the LLM's segmentation instructions and contextual boundary review.

Short interruptions or side discussions may remain within a topic when they do not represent a meaningful subject transition.

The current pipeline does not use a dedicated deterministic digression detector. Borderline cases are therefore treated as a known limitation and are included in failure analysis when they affect boundary quality.

### Related and Overlapping Topics

Closely related or overlapping topics are reviewed for redundancy during evaluation.

When two segments represent the same continuous subject, they may be merged when supported by the transcript context.

When a topic meaningfully reappears after an intervening discussion, it may remain a separate entry and be linked to the earlier topic rather than being merged solely because the subject is similar.

The current `related_to` implementation preserves relationships identified within the same LLM batch. Robust global re-entry detection across independently processed batches remains a limitation.

## 8. Provenance Validation

Provenance validation is deterministic.

For every generated topic:

- `start_ref` must exist in the canonical transcript;
- `end_ref` must exist in the canonical transcript;
- every `evidence_ref` must exist;
- references must belong to the supplied transcript;
- the start reference must not occur after the end reference;
- evidence references must fall within the topic boundaries.

The validator operates independently of the LLM so that source addressability does not depend solely on model behavior.

The current validated topic index contains 57 topics and passed provenance validation with zero errors.

## 9. Evaluation

The system is evaluated using:

### Location Accuracy

Whether topic start, end, and evidence references point to the correct transcript locations.

### Topic Relevance

Whether the topic represents a meaningful subject discussed in the deposition.

### Boundary Quality

Whether the selected start and end references appropriately cover the topic without unnecessary material.

### Coverage

Whether important deposition topics are represented.

### Redundancy

Whether the index contains unnecessary duplicate or near-duplicate topics.

### Stability

The complete deposition is executed three times using the same deposition, transcript, chunking configuration, batch size, and extraction process.

The evaluation compares:

- topic counts,
- topic labels,
- topic boundaries,
- provenance references.

The evaluation distinguishes exact label-and-boundary agreement from broader topic similarity and documents meaningful differences between runs.

### Observed Manual Validation Results

The manual review covered 20 topic entries.

Observed results were:

- Location accuracy: 20/20 (100%)
- Topic relevance: 20/20 (100%)
- Boundary quality: 17/20 (85%)
- Coverage: 20/20 (100%)
- Redundancy: 19/20 (95%)
- Overall manual review: 20/20 (100%)

The main generated index contains 57 validated topic entries.

### Observed Three-Run Stability Results

The complete deposition was processed three times using the same transcript, chunking configuration, batch size, and extraction pipeline.

Each run processed:

- 2,027 canonical transcript records
- 51 transcript chunks
- batch size of 5
- 11 LLM requests

The three runs produced:

- Run 1: 43 topics
- Run 2: 42 topics
- Run 3: 45 topics

Topic count stability therefore varied across runs.

All three runs passed deterministic provenance validation with:

- 0 invalid topic boundary references
- 0 invalid evidence references

The variation in topic counts reflects differences in LLM topic granularity and boundary selection rather than failures in source addressability.

The stability experiment also showed that exact label-and-boundary agreement across independent LLM runs is limited. This is treated as an important reliability consideration rather than being hidden or averaged away.

## 10. Failure Analysis

Three difficult or failed segmentation cases are documented in:

`docs/segmentation_failure_cases.md`

Each case records:

- the system output,
- the expected result,
- why the system struggled,
- the improvement applied or proposed.

The documented cases involve topic splitting or boundary variation around:

1. student-loan portfolio transfers;
2. Vervent involvement with PEAKS loans;
3. PEAKS cancellation rights and enforceability.

These cases demonstrate that the main remaining weakness is semantic segmentation consistency rather than source provenance.

## 11. Reproducibility

The repository contains:

- source code,
- dependency information,
- execution instructions,
- generated outputs required for evaluation,
- validation results,
- AI usage documentation,
- Git history showing meaningful development stages.

The project was also tested from a fresh Git clone using a new Python virtual environment and the dependencies listed in `requirements.txt`.

The fresh-clone validation confirmed that:

- the repository can be cloned successfully;
- the Python environment can be created;
- dependencies can be installed from `requirements.txt`;
- `pip check` reports no broken requirements;
- the included canonical transcript and topic index pass provenance validation;
- the Streamlit application starts successfully.

A reproducibility issue involving a missing Streamlit dependency was identified during the fresh-clone test and fixed by explicitly declaring Streamlit in `requirements.txt`.

The README identifies the final submission commit and a meaningful earlier commit used as a comparison point.