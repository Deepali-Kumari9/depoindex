# Segmentation Failure Cases

This document analyzes difficult cases observed during the three-run stability experiment on the same deposition transcript subset (printed pages 19-34).

The same 400 transcript records were processed three times using the same pipeline and model. The runs produced 8, 9, and 7 topics respectively. The main instability was not invalid provenance, but differences in semantic topic boundaries and decisions to split or merge closely related discussions.

## Case 1: Student loan transfer discussion

### What the runs produced

The discussion about student loan portfolio transfers and related data processes was segmented differently:

| Run | Segmentation |
|---|---|
| Run 1 | `20:16 -> 23:18` as one topic |
| Run 2 | `20:16 -> 22:5` and `22:6 -> 23:20` as two topics |
| Run 3 | `20:21 -> 23:18` as one topic |

Run 1 treated the transfer mechanics, risks, and regulatory discussion as one continuous topic.

Run 2 separated the discussion into transfer mechanics/data processes and risks/regulations.

Run 3 again treated most of the discussion as one topic, while also choosing a slightly different starting boundary.

### What should happen

The segmentation should consistently recognize the meaningful transition between:

1. the mechanics and processes involved in transferring student loan portfolios/data, and
2. the risks and regulatory considerations associated with those transfers.

However, closely connected material should not be split merely because the discussion moves from one aspect of the same subject to another.

### Why the LLM varied

The sections are semantically related and occur consecutively. The model can therefore reasonably interpret them either as:

- one broader topic about student loan transfers, or
- separate topics for transfer mechanics and transfer risks/regulations.

The model also has to decide whether a change in emphasis represents a meaningful topic transition or simply a continuation of the current topic.

### Possible improvement

Use a more explicit segmentation criterion in the extraction prompt. For example, require a new topic only when the testimony changes to a substantively different question or subject, rather than when the discussion changes from one aspect of the same subject to another.

A deterministic post-processing stage could also flag very closely related adjacent topics for review before final indexing.

---

## Case 2: PEAKS transfer, criminal law, RICO, and report structure

### What the runs produced

This section showed a stronger difference in topic boundaries:

| Run | Segmentation |
|---|---|
| Run 1 | `23:20 -> 24:13` PEAKS transfer; `24:14 -> 26:14` criminal law/RICO; `26:15 -> 26:25` report structure |
| Run 2 | `23:20 -> 25:7` PEAKS transfer/criminal law; `25:8 -> 26:25` RICO/report formatting |
| Run 3 | `23:19 -> 25:7` PEAKS transfer/criminal law; `25:8 -> 26:25` RICO/report formatting |

Run 1 identified three separate topic transitions.

Runs 2 and 3 grouped some adjacent discussions together.

### What should happen

The final index should distinguish meaningful changes in subject matter. In particular, the transition from the PEAKS loan transfer discussion to the witness's criminal-law experience and the later RICO/report discussion should be evaluated based on the actual substance of the testimony.

The goal is not simply to maximize the number of topics, but to create boundaries where the testimony meaningfully changes subject.

### Why the LLM varied

These discussions are adjacent and relatively short. The model has to determine whether each transition is significant enough to justify a new index entry.

Short sections are especially sensitive to segmentation decisions because there is less surrounding context for determining whether they represent an independent topic or a continuation of the previous discussion.

The runs demonstrate that the model can choose different boundary points even when processing the same transcript content.

### Possible improvement

The prompt can require the model to consider the examiner's question and the witness's response together when deciding whether a new topic begins.

A stronger pipeline could also use a two-stage approach:

1. identify candidate transitions, and
2. classify each candidate transition as a meaningful topic change or continuation.

This would make the boundary decision more explicit rather than asking the model to perform both tasks implicitly.

---

## Case 3: ITT student outcomes and Senate HELP Committee discussion

### What the runs produced

The discussion from pages 27-34 was segmented differently:

| Run | Segmentation |
|---|---|
| Run 1 | `27:1 -> 28:9`, `28:10 -> 31:20`, `31:21 -> 34:25` |
| Run 2 | `27:1 -> 28:15`, `28:16 -> 30:4`, `30:5 -> 31:20`, `31:21 -> 34:25` |
| Run 3 | `27:1 -> 28:14`, `28:16 -> 31:20`, `31:21 -> 34:25` |

The main difference is that Run 2 separated the retention, graduation, and default-rate discussion into its own topic, while Runs 1 and 3 incorporated it into the broader ITT analysis.

### What should happen

The segmentation should consistently distinguish a genuinely new analytical subject from supporting evidence within the broader ITT discussion.

The Senate HELP Committee statistics should either:

- remain part of the broader ITT educational and economic outcomes topic if they function primarily as supporting evidence, or
- become a separate topic if the testimony treats the statistics as a distinct subject of examination.

The decision should be based on the substantive transition rather than simply the presence of a new report or set of statistics.

### Why the LLM varied

The discussion contains several closely related concepts:

- ITT educational quality,
- student debt,
- economic outcomes,
- retention,
- graduation,
- default rates, and
- aggregate versus individual student outcomes.

Because these concepts are strongly related, the model can reasonably produce either broader or narrower topic boundaries.

### Possible improvement

The extraction prompt should define a consistent granularity policy. For example, closely related evidence and statistics should remain within the parent topic unless the examiner changes the substantive question or the testimony clearly develops a separate issue.

A later deterministic or review-based stage can then flag unusually broad or unusually narrow topics for inspection.

---

## Overall Findings

The three-run experiment demonstrates meaningful semantic segmentation instability:

- Run 1 produced 8 topics.
- Run 2 produced 9 topics.
- Run 3 produced 7 topics.
- No topic had an identical label and identical start/end boundary across all three runs.

The instability primarily occurred where adjacent testimony contained closely related concepts. The model sometimes merged these sections into broader topics and sometimes split them into narrower topics.

Importantly, the instability was not caused by broken source references. The provenance validation confirmed that the generated page:line references existed in the canonical transcript and that topic boundaries and evidence references were structurally valid.

## Engineering Improvements

The following improvements can reduce segmentation instability:

1. Define an explicit topic-granularity policy in the extraction prompt.
2. Require meaningful substantive transitions rather than changes in emphasis alone.
3. Use examiner questions and witness responses together when identifying boundaries.
4. Separate candidate-transition detection from the final boundary decision.
5. Use deterministic validation to detect invalid references and inconsistent boundaries.
6. Use human review for ambiguous short sections and unusually broad or narrow topics.
7. Preserve the original page:line references throughout all processing stages so that every segmentation decision remains auditable.

The experiment shows why repeated runs and failure analysis are important for an LLM-based legal-document indexing system. A single successful run is not sufficient evidence of reliable segmentation.