# DepoIndex Validation Report

## 1. Purpose

This report documents the validation of the DepoIndex AI-powered deposition topic
index for the supplied Persis Yu deposition.

The validation focuses on:

- topic relevance
- topic boundary quality
- exact page-line provenance
- transcript coverage
- redundancy
- repeated-run stability
- difficult segmentation cases
- reproducibility

The validation uses the complete extracted deposition transcript rather than a
subset of the source.

---

## 2. Validation Methodology

The complete deposition is first converted into a canonical transcript containing
numbered testimony records with exact printed page and line references.

The canonical transcript contains:

- 2,027 transcript records
- printed pages 7 through 88
- 82 unique printed pages
- 51 provenance-preserving chunks
- 40 transcript records per chunk

The LLM processes five chunks per request. Topic extraction produces structured
topic records containing:

- topic label
- start page and line
- end page and line
- supporting evidence references
- source chunk information
- related-topic references where available

The resulting topics are then processed by deterministic validation code.

The validation checks that:

1. every referenced page-line exists in the canonical transcript;
2. every topic has an ordered start and end boundary;
3. evidence references fall within the topic boundary;
4. topic records remain chronologically ordered;
5. source references remain addressable to the original transcript.

This separates semantic topic generation from deterministic provenance validation.

---

## 3. Manual Evaluation

A manual review was performed on the first 20 indexed topics.

Each topic was evaluated using five criteria:

- location accuracy
- topic relevance
- boundary quality
- coverage
- redundancy

The scores were:

| Criterion | Result |
|---|---:|
| Location accuracy | 20/20 (100%) |
| Topic relevance | 20/20 (100%) |
| Boundary quality | 17/20 (85%) |
| Coverage | 20/20 (100%) |
| Redundancy | 19/20 (95%) |

The overall manual review passed for all 20 reviewed topics.

### Manual review observations

Three boundary-related observations were recorded:

- One topic had a slightly loose boundary because of a reporter interruption.
- One topic had a minor transition-related boundary issue.
- One broad topic contained potentially separable subthemes.

No invalid provenance references or obvious duplicate topics were found in the
20 manually reviewed entries.

The complete manual evaluation data is stored in:

`evaluation/manual_evaluation.json`

---

## 4. Deterministic Provenance Validation

The final validated topic index contains 57 topics.

The deterministic provenance validator checked:

- 2,027 canonical transcript records
- 11 LLM batches
- 57 topic records

Result:

- validation errors: 0
- invalid topic boundaries: 0
- invalid evidence references: 0

Therefore, all indexed topic references are addressable to the canonical transcript,
and all topic boundaries are ordered correctly.

The validated output is stored in:

`outputs/validated_topic_index.json`

The human-readable topic index is stored in:

`outputs/deposition_topic_index.md`

---

## 5. Complete-Deposition Three-Run Stability

The complete deposition was processed independently three times using the same
pipeline configuration.

Each run used:

- 2,027 transcript records
- 51 chunks
- 40 records per chunk
- 5 chunks per LLM request
- 11 LLM requests per run
- printed pages 7 through 88

### Results

| Metric | Run 1 | Run 2 | Run 3 |
|---|---:|---:|---:|
| Topic count | 43 | 42 | 45 |
| Invalid boundary references | 0 | 0 | 0 |
| Invalid evidence references | 0 | 0 | 0 |

Topic counts therefore varied slightly between runs.

Strict identical topic label + boundary matches:

- identical across all three runs: 1 topic
- Run 1 vs Run 2: 8 identical topics
- Run 1 vs Run 3: 3 identical topics
- Run 2 vs Run 3: 4 identical topics

### Interpretation

The provenance layer remained stable across all three runs: no invalid boundary
or evidence references were produced.

The main source of variation was semantic segmentation granularity. In some cases,
the LLM grouped a longer discussion into one topic in one run and split the same
discussion into two related topics in another run.

This is expected for an LLM-based semantic segmentation system and is an important
reliability finding rather than something hidden or artificially normalized.

The complete stability results are stored in:

`outputs/stability_report.json`

---

## 6. Failure and Difficult Segmentation Cases

Three representative difficult cases were investigated.

### Case 1 — Student-loan portfolio transfers

One run represented the discussion from approximately `19:15` to `23:6` as a
single topic.

Another run divided it into:

- `19:15` to `21:8`
- `21:9` to `23:6`

The underlying testimony was continuous, but the LLM chose different semantic
granularities.

**Expected behavior:** either a coherent single topic or clearly justified
subtopics with accurate boundaries.

**Cause:** semantic boundary ambiguity in a long discussion.

**Improvement:** a future boundary-scoring or hierarchical segmentation stage
could compare neighboring topic candidates before finalizing boundaries.

---

### Case 2 — Vervent involvement with PEAKS loans

One run produced a single topic covering approximately `42:5` to `44:11/12`.

Another run divided the discussion into:

- `42:5` to `43:7`
- `43:8` to `44:12`

Again, provenance remained valid, but semantic granularity differed.

**Expected behavior:** preserve the underlying discussion while avoiding arbitrary
splits or merges.

**Cause:** closely related subthemes within the same testimony sequence.

**Improvement:** future versions could use hierarchical topic refinement and
neighboring-topic comparison.

---

### Case 3 — PEAKS cancellation rights and enforceability

One run produced a topic from approximately `55:14` to `60:1`.

Other runs divided this material into multiple segments, including boundaries
around pages 58 and 60.

**Expected behavior:** maintain meaningful topic boundaries while preserving exact
source references.

**Cause:** a long discussion containing multiple closely related legal concepts.

**Improvement:** a future boundary scorer could evaluate topic continuity,
semantic similarity, and transition evidence before accepting a split.

---

## 7. Re-entry and Digression Handling

The extraction prompt instructs the LLM to create a new topic when a meaningful
topic reappears after another topic and to provide a related-topic reference where
appropriate.

The current refinement stage preserves valid batch-local related-topic references
and maps them to global topic IDs.

However, the implementation does **not** reliably detect and link every global
topic re-entry across separate LLM batches.

Brief digressions are handled through contextual segmentation instructions and
boundary review. There is currently no dedicated deterministic digression detector.

These are documented limitations rather than claims of complete automated
resolution.

---

## 8. Silent Transcript-Skip Protection

The pipeline uses a canonical transcript as the addressable source for all
downstream processing.

The complete extracted transcript contains 2,027 records and is divided into
51 chunks. The complete set of chunks is processed by the batched extraction
pipeline.

Downstream deterministic validation verifies that generated topic and evidence
references exist in the canonical transcript.

This provides protection against silent invalid references or topic references
pointing outside the extracted source.

No invalid provenance references were observed in the complete-deposition
three-run stability evaluation.

---

## 9. Reproducibility

The repository includes the code and generated outputs required to reproduce
the validation stages.

Dependencies are pinned in:

`requirements.txt`

The final environment uses:

- Python 3.11
- google-genai 2.22.0
- PyMuPDF 1.28.2
- python-dotenv 1.2.3
- streamlit 1.63.0

A fresh-clone test was performed using the repository from GitHub.

The fresh clone successfully:

1. cloned the repository;
2. created a Python virtual environment;
3. installed the pinned dependencies;
4. passed `pip check`;
5. ran deterministic provenance validation successfully;
6. started the Streamlit application successfully.

The fresh-clone test therefore confirmed that the repository setup is reproducible
for the included outputs and validation pipeline.

---

## 10. LLM Stability and Professional Reliability

The final topic extraction stage is intentionally treated as nondeterministic.

Instead of assuming identical LLM outputs, the project measures variation across
three complete runs.

The results show:

- topic counts varied from 42 to 45;
- provenance validation remained valid in every run;
- semantic topic boundaries sometimes varied;
- difficult cases were explicitly investigated.

This means the current system provides strong source addressability and deterministic
validation, while semantic segmentation should still be treated as an AI-assisted
indexing process requiring review for high-stakes professional use.

---

## 11. Limitations

Current limitations include:

- LLM-generated topic segmentation is nondeterministic.
- Boundary quality is not perfect, as shown by the 85% manual boundary score.
- Manual evaluation covers 20 topics rather than all 57 topics.
- Global re-entry detection across separate batches is not fully automated.
- Brief digressions do not have a dedicated deterministic detector.
- The current system processes one deposition and has not been evaluated across a
  larger multi-deposition corpus.
- The application is a technical prototype and is not a production legal system.

---

## 12. Validation Conclusion

The DepoIndex pipeline successfully processes the complete supplied deposition and
produces a validated chronological topic index with exact page-line provenance.

The final validated index contains 57 topics.

The most important validation result is that deterministic provenance validation
reported zero invalid boundary references and zero invalid evidence references
across all three complete-deposition stability runs.

The three-run experiment also identified genuine semantic segmentation variation.
Rather than hiding this variation, the project records and analyzes representative
failure cases and identifies concrete future improvements.

Overall, the validation demonstrates that the current system provides a reproducible,
source-addressable foundation for deposition topic indexing while clearly identifying
the remaining reliability limitations of LLM-based semantic segmentation.