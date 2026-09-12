# Segmentation Failure Analysis

## Overview

The DepoIndex pipeline was run three times on the complete deposition using the
same input transcript, chunking configuration, batch size, and extraction
pipeline.

The three runs produced:

| Run | Topic count | Provenance |
|---|---:|---|
| Run 1 | 43 | Valid |
| Run 2 | 42 | Valid |
| Run 3 | 45 | Valid |

The topic counts varied across runs, while all reported start, end, and
evidence references remained valid against the canonical transcript.

This indicates that the main source of instability is not source addressing,
but the LLM's interpretation of topic granularity and topic boundaries.

The following cases represent three meaningful types of segmentation
instability observed across the runs.

---

## Case 1 — Student-loan portfolio transfers: merged vs. split topics

### What the runs produced

**Run 1**

- Experience with student loan portfolio transfers between servicers
- **19:15 → 23:6**

**Run 2**

- Experience with student loan portfolio transfers between servicers
- **19:15 → 23:6**

**Run 3**

- Experience with student loan portfolio transfers between servicers
- **19:15 → 21:8**
- Mechanics, data transfer processes, and risks of servicer transitions
- **21:9 → 23:6**

### What should have been produced

A useful attorney-facing segmentation is the Run 3 structure:

1. Experience with student loan portfolio transfers
2. Mechanics, data-transfer processes, and risks of servicer transitions

The second topic represents a meaningful shift from the witness's prior
experience to the operational process and risks involved in a servicer
transition.

### Why the model failed

The two discussions are closely related and occur as a continuous line of
questioning. There is no strong structural break between them. As a result,
the model sometimes treated the entire discussion as one broad topic and
sometimes recognized the shift in topic focus.

### Improvement

A future segmentation stage should explicitly score candidate boundaries using:

- change in question intent,
- semantic change between adjacent transcript windows,
- introduction of a new subtopic,
- and sustained change rather than a short-lived digression.

A hierarchical representation could also retain the broader portfolio-transfer
topic while representing the mechanics and risks as a related subtopic.

---

## Case 2 — Vervent involvement with PEAKS loans: broad vs. granular segmentation

### What the runs produced

**Run 1**

- Vervent defendants' involvement with PEAKS loans and origination timeline
- **42:5 → 44:12**

**Run 2**

- Vervent defendants' involvement with PEAKS loans and origination
- **42:5 → 43:7**
- Vervent defendants' role regarding student recruitment
- **43:8 → 44:12**

**Run 3**

- Vervent defendants' involvement and role with the PEAKS loan portfolio
- **42:5 → 44:11**

### What should have been produced

The Run 2 segmentation is more useful for navigation because the questioning
moves from Vervent's involvement/origination to a distinct discussion of
student recruitment around **43:8**.

The two topics are still related under the broader subject of Vervent's
involvement with PEAKS loans.

### Why the model failed

The discussion has a strong overall semantic connection. The model can
therefore reasonably interpret the recruitment discussion as either:

- part of the broader Vervent/PEAKS involvement topic, or
- a separate attorney-relevant subtopic.

This produces different levels of granularity across runs.

### Improvement

A hierarchical segmentation strategy would reduce this ambiguity:

**Parent topic:** Vervent's involvement with PEAKS loans

Possible child topics:

- involvement/origination
- student recruitment role

This preserves the relationship while allowing attorneys to navigate directly
to the more specific discussion.

---

## Case 3 — PEAKS cancellation rights and loan enforceability: boundary drift

### What the runs produced

**Run 1**

- PEAKS borrowers final disclosures and right to cancel loans
- **55:14 → 60:1**

**Run 2**

- PEAKS borrowers final disclosures and right to cancel loans
- **55:14 → 58:22**
- Continuation of loan cancellation rights and disclosure receipt
- **58:23 → 60:1**

**Run 3**

- PEAKS borrowers final disclosures and right to cancel loans
- **55:14 → 58:16**
- Enforceability of loans and cancellation rights without disclosures
- **58:17 → 60:5**

### What should have been produced

The testimony is better represented by separating the discussion when it
moves from disclosure/cancellation procedures toward the legal effect of
missing disclosures on loan enforceability.

Run 3 provides the clearest conceptual distinction, with a transition around
**58:17**, although the exact boundary remains a candidate for manual review.

### Why the model failed

The concepts of cancellation rights, disclosures, and enforceability are
closely connected. The testimony also transitions gradually rather than
through a sharp conversational break.

Consequently, the model produced different boundaries across runs:

- one broad topic,
- two closely related topics,
- or a split at a different point.

### Improvement

Boundary detection should consider more than semantic similarity. A stronger
boundary scorer should combine:

- semantic change,
- question/answer intent,
- legal concept changes,
- and whether the new segment represents a distinct attorney-relevant issue.

---

## Additional observed issue — overlapping CFPB topics

Run 1 also produced an overlap:

- CFPB investigation and Civil Investigative Demand regarding PEAKS program
  **66:22 → 68:25**
- CFPB findings regarding Vervent defendants
  **68:7 → 68:25**

The second topic overlaps the first from **68:7 → 68:25**.

Runs 2 and 3 instead represented this region as a single CFPB investigation
topic spanning approximately **66:22 → 69:1**.

This demonstrates that valid provenance alone does not guarantee ideal
segmentation. A reference can be completely valid while the topic itself is
redundant or overlapping.

A future refinement should therefore include a deterministic overlap check
after LLM extraction and flag or merge overlapping topics when they represent
the same underlying discussion.

---

## Summary of failure modes

The three main cases demonstrate different types of instability:

| Case | Failure mode | Main issue |
|---|---|---|
| 1 | Merge vs. split | Related discussion can be represented as one broad topic or two subtopics |
| 2 | Granularity variation | Broad parent topic vs. more specific child topic |
| 3 | Boundary drift | Gradual conceptual transition produces different start/end boundaries |

The complete three-run experiment shows that the pipeline's provenance layer
is stable even when LLM segmentation varies. All three runs produced valid
page/line references.

The main remaining improvement area is therefore **segmentation consistency**,
particularly around closely related topics, gradual transitions, and
topic/subtopic boundaries.