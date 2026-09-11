# LLM Usage

## AI Tools Used

This project used AI assistance during development and validation.

### ChatGPT

ChatGPT was used for:
- Understanding and breaking down the DepoIndex problem statement.
- Designing the overall pipeline and provenance-preserving architecture.
- Reviewing Python implementation decisions.
- Debugging extraction, chunking, JSON parsing, and API execution issues.
- Suggesting testing and validation strategies.
- Reviewing Git workflow and documentation requirements.

### Google Gemini API

Google Gemini was used as the LLM component for baseline deposition topic extraction.

Model used:
- Gemini 3.6 Flash

The model received transcript chunks containing exact `page:line` source references and was instructed to return structured JSON containing:
- topic
- start_ref
- end_ref
- evidence_refs

## AI Suggestions and Implementation Decisions

| AI suggestion | Decision | Validation / reason |
|---|---|---|
| Preserve exact page:line references during extraction | Accepted | Verified against the source transcript and canonical extraction output. |
| Use structured JSON for topic extraction | Accepted | Makes downstream validation and processing deterministic. |
| Strip Markdown code fences before JSON parsing | Accepted | Initial Gemini responses sometimes returned JSON inside code fences. |
| Save LLM results incrementally | Accepted | Prevents losing completed work if a later API request fails. |
| Add request timeout | Accepted | A previous API request remained pending for several minutes, so a bounded timeout was added. |
| Resume processing from previously completed chunks | Accepted | Avoids unnecessarily repeating successful API requests. |
| Use one LLM request per small transcript chunk as the final architecture | Rejected as the final approach | The baseline experiment produced too many API requests and hit the free-tier daily request limit. A more efficient batched architecture will be evaluated. |

## Baseline Experiment

The initial baseline divided the canonical transcript into 51 chunks.

The baseline LLM extraction was executed using the Gemini API. Four chunks were successfully processed before the free-tier daily request limit was reached. The remaining requests returned HTTP 429 quota errors.

The successful outputs demonstrated that the model could:
- identify meaningful deposition topics,
- produce structured topic records,
- preserve exact page:line references.

The baseline also showed areas requiring improvement:
- some topic labels were overly verbose or similar,
- evidence references could include almost every line rather than only the most useful evidence,
- repeated runs of the same small chunk produced slight differences in topic wording and evidence selection,
- processing every chunk independently is inefficient for the available API quota.

The quota failure was treated as an engineering constraint rather than hidden or worked around by fabricating results.

## Changes Made to AI-Generated Suggestions

AI-generated implementation suggestions were reviewed before being incorporated into the project.

The implementation was adjusted to:
- use the Google GenAI Interactions API,
- validate returned JSON before saving results,
- preserve source references throughout processing,
- checkpoint successful and failed chunks,
- use a bounded HTTP timeout,
- record actual API failures in the baseline output.

Future iterations will reduce the number of LLM requests by combining provenance-preserving transcript sections into larger batches and using deterministic validation after LLM extraction.

## Validation Approach

AI-generated code and suggestions were not treated as automatically correct.

Validation included:
- running Python syntax checks,
- verifying extracted transcript boundaries against the source PDF,
- checking that generated JSON can be parsed,
- inspecting successful LLM outputs manually,
- verifying that API failures were recorded rather than silently ignored,
- comparing repeated baseline outputs to observe model variability.

## Batched LLM Experiment

After the baseline experiment reached the free-tier daily request limit, the LLM pipeline was redesigned to reduce the number of API requests.

Instead of sending one Gemini request for each of the 51 transcript chunks, the new experiment combines 5 consecutive provenance-preserving chunks into one Gemini request.

This reduced the number of Gemini requests from 51 to 11.

The batched pipeline:
- preserved the original `page:line` references,
- allowed topics to span multiple original chunks,
- instructed Gemini to avoid duplicate topics caused by chunk boundaries,
- required structured JSON output,
- saved results incrementally after each batch.

The batched experiment successfully processed all 11 requests and produced 57 raw topic entries.

The output was then passed through deterministic refinement and provenance validation. The validation checked that:
- every `start_ref` exists in the canonical transcript,
- every `end_ref` exists in the canonical transcript,
- every `evidence_ref` exists in the canonical transcript,
- topic boundaries are correctly ordered,
- evidence references fall within the topic boundaries.

The validation completed with 57 topics checked and 0 provenance errors.

### What changed from the baseline

| Change | Reason |
|---|---|
| Combine 5 transcript chunks per LLM request | Reduce API request count and work within the free-tier quota |
| Preserve individual chunk IDs in the input | Maintain traceability even when multiple chunks are processed together |
| Allow topics to cross chunk boundaries | Avoid artificial topic boundaries caused by chunking |
| Deterministically assign global topic IDs after extraction | Avoid unreliable batch-local topic numbering |
| Derive source chunk IDs from actual page:line references | Preserve accurate provenance |
| Clear untrusted `related_to` values from the raw LLM output | Some model-generated relationship indices were inconsistent across batches; relationships will be established only after global topic evaluation |

The batching approach was accepted as an engineering improvement because it reduced API usage while preserving provenance and enabling the complete transcript to be processed.