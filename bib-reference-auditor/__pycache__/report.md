# HCDD filtering report

Filtering completed under the user-authorized exclusion of six TOPIQ-NR-Face no-face failures: **352 of 2,088 original samples passed DFJ-7B ≥4**.

## Scope and completion

- Original images: 2,088 unique IDs.
- All three IQA scores valid: 2,082; six TOPIQ face-detector failures were excluded from ranking under the user's instruction.
- The original target of 1,462 and original group quotas were retained; ranks were computed over the 2,082 fully scored items.
- IQA selected: 1,462 (real 272, full fake 0, region fake 1,190).
- DFJ evaluated every IQA-selected candidate: 1,462/1,462 valid scores, unresolved 0, inference errors 0.
- IQA-excluded from DFJ: 626 total, consisting of 620 consensus-ranked rejects and six IQA scoring failures. None was scored by DFJ.
- Six TOPIQ failure IDs: HCFE_000585, HCFE_000646, HCFE_000688, HCFE_000896, HCFE_001513, HCFE_001822.
- DFJ model: MBZUAI/Qwen-2.5-VL-Instruct-7B-Pointwise-DFJ, revision 0270d972f4569059a1c4f10fe606f0146095df04; official prompt text SHA-256 0b33ef73c8cda74891bab9548a32f76ef8edc2ca5d26a1527c0e6727b72e172b.
- Human realism was not manually evaluated; automated scores are not proof of annotation correctness.

## Selection counts and group proportions

| Stage | Real | Full fake | Region fake | Total | Original retention | Real share | Full fake share | Region fake share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Original | 388 | 0 | 1700 | 2088 | 100.00% | 18.58% | 0.00% | 81.42% |
| IQA consensus | 272 | 0 | 1190 | 1462 | 70.02% | 18.60% | 0.00% | 81.40% |
| Final DFJ >=4 | 267 | 0 | 85 | 352 | 16.86% | 75.85% | 0.00% | 24.15% |

Percentage-point change in final group composition vs original: real: +57.27 pp; fake_full: +0.00 pp; fake_region: -57.27 pp.

## IQA consensus

Rankable population: 2082; selected target: 1462; selection method: groupwise average ascending rank normalized to [0,1], minimum of the three percentiles, original group quotas, then consensus descending / mean percentile descending / image ID ascending.

| Group | Original n | Rankable n | Authorized IQA failures | Quota | Selected | Consensus cutoff | Boundary ties (all / selected) |
|---|---:|---:|---:|---:|---:|---:|---:|
| real | 388 | 387 | 1 | 272 | 272 | 0.20207253886010362 | 2 / 1 |
| fake_full | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 |
| fake_region | 1700 | 1695 | 5 | 1190 | 1190 | 0.21192443919716647 | 1 / 1 |

IQA raw-score summaries are computed on the rankable population (n=2,082):

| IQA model | Group | n | Mean | Median | Min | Max |
|---|---|---:|---:|---:|---:|---:|
| reliqs | real | 387 | 0.461153 | 0.459491 | 0.425404 | 0.507508 |
| reliqs | fake_region | 1695 | 0.470860 | 0.471569 | 0.442143 | 0.510788 |
| deqa | real | 387 | 1.934545 | 1.872070 | 1.191406 | 3.349609 |
| deqa | fake_region | 1695 | 2.152381 | 2.099609 | 1.327148 | 3.525391 |
| topiq_face | real | 387 | 0.377507 | 0.366804 | 0.086982 | 0.680140 |
| topiq_face | fake_region | 1695 | 0.388735 | 0.381300 | 0.112990 | 0.663568 |

Spearman correlation between within-group IQA percentile ranks:

| Group | ReLIQS–DeQA | ReLIQS–TOPIQ | DeQA–TOPIQ |
|---|---:|---:|---:|
| real | 0.9345129621394406 | 0.8582363461171365 | 0.8577855376323754 |
| fake_region | 0.9309798984576929 | 0.9193720879215291 | 0.926602828025789 |

## DFJ-7B score distribution

| Group | Score 1 | Score 2 | Score 3 | Score 4 | Score 5 | Total |
|---|---:|---:|---:|---:|---:|---:|
| real | 0 | 0 | 5 | 267 | 0 | 272 |
| fake_full | 0 | 0 | 0 | 0 | 0 | 0 |
| fake_region | 821 | 102 | 182 | 85 | 0 | 1190 |
| **Overall** | 821 | 102 | 187 | 352 | 0 | 1462 |

Threshold sensitivity over the fixed 1,462 IQA candidates:

| DFJ threshold | Candidates retained |
|---|---:|
| ≥3 | 539 |
| ≥4 | 352 |
| ≥5 | 0 |

## Existing annotation coverage

Counts below are occurrences of the existing annotation.reasoning.where and annotation.reasoning.what entries; no labels or explanations were created.

### Region mentions

| Value | Original | Final |
|---|---:|---:|
| jaw | 310 | 19 |
| left_cheek | 305 | 23 |
| left_ear | 92 | 8 |
| left_eye | 252 | 19 |
| left_eyebrow | 286 | 13 |
| left_pupil | 374 | 20 |
| mouth | 295 | 17 |
| nose | 305 | 26 |
| right_cheek | 303 | 30 |
| right_ear | 79 | 6 |
| right_eye | 281 | 29 |
| right_eyebrow | 325 | 15 |
| right_pupil | 346 | 12 |

### Artifact mentions

| Value | Original | Final |
|---|---:|---:|
| boundary_blending | 1265 | 83 |
| edge_blur | 547 | 31 |
| residual_noise | 1345 | 67 |

## Exclusions

| Reason | Count |
|---|---:|
| dfj_below_threshold | 1110 |
| iqa_rejected | 620 |
| iqa_scoring_error | 6 |

## Runtime and integrity

- ReLIQS IQA: 93.201425075531 s, 2088/2088 valid.
- DeQA IQA: 372.2421910762787 s, 2088/2088 valid.
- TOPIQ-NR-Face IQA: full pass 115.13 s, 2,082/2,088 valid; six detector failures were retried and authorized for exclusion.
- DFJ-7B: 2808.91 s full run; 1462/1462 valid, 0 errors; mean throughput 1873.8 candidates/hour.
- Integrity: 2,088 unique source IDs; 1,462 unique IQA-selected IDs; 1,462 unique valid DFJ candidate scores; 2,088 audit rows; final IDs match JSONL and each has score ≥4; all 12 validation assertions passed.

## Output files

- Run directory: /HC/Deepfake/experiments/hcdd_filtering_20261014
- Resolved configuration: /HC/Deepfake/experiments/hcdd_filtering_20261014/resolved_config.yaml
- Environment: /HC/Deepfake/experiments/hcdd_filtering_20261014/environment.json
- Run log: /HC/Deepfake/experiments/hcdd_filtering_20261014/run.log
- IQA score table: /HC/Deepfake/experiments/hcdd_filtering_20261014/artifacts/iqa_scores.csv
- IQA selection audit: /HC/Deepfake/experiments/hcdd_filtering_20261014/artifacts/selection_audit.csv
- IQA selected manifest: /HC/Deepfake/experiments/hcdd_filtering_20261014/artifacts/iqa_selected.jsonl
- DFJ raw predictions and attempt history: /HC/Deepfake/experiments/hcdd_filtering_20261014/artifacts/dfj7b_raw.jsonl
- DFJ canonical scores: /HC/Deepfake/experiments/hcdd_filtering_20261014/artifacts/dfj7b_scores.csv
- All-sample audit: /HC/Deepfake/experiments/hcdd_filtering_20261014/artifacts/audit_all_samples.csv
- Final selected manifest and IDs: /HC/Deepfake/experiments/hcdd_filtering_20261014/artifacts/final_selected.jsonl, /HC/Deepfake/experiments/hcdd_filtering_20261014/artifacts/final_selected_ids.txt
- Final summary: /HC/Deepfake/experiments/hcdd_filtering_20261014/artifacts/filtering_summary.json
- Completion state: /HC/Deepfake/experiments/hcdd_filtering_20261014/artifacts/pipeline_state.json
