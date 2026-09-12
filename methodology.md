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
7. Refine topic boundaries and merge related segments.
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

The canonical extraction currently contains 2,027 transcript records and ends at page 88, line 13, where the deposition testimony concludes.

## 4. Transcript Chunking

The canonical transcript is divided into sequential chunks to make LLM processing manageable.

The current baseline uses chunks of 40 transcript records.

This produced 51 chunks.

Each chunk retains:
- chunk ID,
- starting source reference,
- ending source reference,
- all original transcript records.

No transcript line is rewritten or assigned a new artificial source reference during chunking.

## 5. Baseline LLM Extraction

The baseline uses Google Gemini 3.6 Flash.

The LLM receives transcript text together with its exact source references.

It is instructed to return structured JSON containing:

- topic
- start_ref
- end_ref
- evidence_refs

The baseline experiment demonstrated that the LLM can identify meaningful deposition topics while preserving exact page:line references.

However, processing each chunk independently requires too many API requests.

## 6. Baseline Findings

The baseline attempted all 51 chunks.

Four chunks were successfully processed before the available API request quota was reached.

The successful chunks produced nine topic entries.

The baseline revealed several areas for improvement:

- independent chunks can fragment a topic across chunk boundaries;
- some topic labels can be verbose or closely related;
- evidence lists can contain more lines than are necessary;
- repeated LLM calls can produce small differences in labels or evidence selection;
- one-request-per-chunk processing is inefficient for the available API quota.

These findings motivate the refinement stage.

## 7. Refinement Strategy

The improved pipeline will reduce dependence on independent chunk-level decisions.

Candidate topic segments will be refined using the surrounding transcript context.

Related or fragmented segments can be merged when they represent the same continuous subject.

If a topic meaningfully reappears after an intervening discussion, it should normally be represented as a separate topic entry and linked to the earlier entry rather than incorrectly extending the original boundary.

All refinements must preserve the original page:line references.
Brief digressions are handled by evaluating the surrounding transcript context
during topic refinement. Short interruptions or side discussions may remain
within a topic when they do not represent a meaningful subject transition.
The current pipeline does not use a dedicated deterministic digression
detector, so borderline cases are treated as a known limitation and are
included in failure analysis when they affect boundary quality.

Closely related or overlapping topics are reviewed for redundancy during
evaluation. When two segments represent the same continuous subject, they
may be merged. When a topic meaningfully reappears after an intervening
discussion, it may remain a separate entry and be linked to the earlier topic
rather than being merged solely because the subject is similar.

## 8. Provenance Validation

Provenance validation will be deterministic.

For every generated topic:

- `start_ref` must exist in the canonical transcript;
- `end_ref` must exist in the canonical transcript;
- every `evidence_ref` must exist;
- references must belong to the supplied transcript;
- the start reference must not occur after the end reference.

The validator will operate independently of the LLM so that source-addressability does not depend solely on model behavior.

## 9. Evaluation

The final system will be evaluated using:

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
The complete pipeline will be executed three times using the same deposition,
transcript, chunking configuration, batch size, and extraction process. Topic
counts, labels, boundaries, and provenance references will be compared across
runs. The evaluation will distinguish exact label-and-boundary agreement from
broader topic similarity and will document meaningful differences between
runs.

### Observed Validation Results

The manual review covered 20 topic entries.

Observed results were:

- Location accuracy: 20/20 (100%)
- Topic relevance: 20/20 (100%)
- Boundary quality: 17/20 (85%)
- Coverage: 20/20 (100%)
- Redundancy: 19/20 (95%)
- Overall manual review: 20/20 (100%)

The 57-topic validated index described above is the main generated index.
The following three runs are independent executions used specifically to
measure segmentation stability and are not replacements for the main index.

The complete deposition was processed three times using the same transcript,
chunking configuration, batch size, and extraction pipeline.

The three runs produced 43, 42, and 45 topics respectively. All three runs
passed deterministic provenance validation with zero invalid boundary
references and zero invalid evidence references.

The variation in topic counts reflects differences in LLM topic granularity
and boundary selection rather than failures in source addressability.

## 10. Failure Analysis

At least three difficult or failed cases will be documented.

For each case, the evaluation will describe:

- the system output,
- the expected result,
- why the system struggled,
- the improvement applied or proposed.

## 11. Reproducibility

The repository will contain:

- source code,
- dependency information,
- execution instructions,
- generated outputs required for evaluation,
- validation results,
- AI usage documentation,
- Git history showing meaningful development stages.

The final README will identify the final submission commit SHA and a meaningful earlier commit used as a comparison point.