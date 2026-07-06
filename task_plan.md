# Task Plan: q1 Modeling With Pre-Code Block

## Goal
Complete the prompt in `tasks/task1.txt` for q1, stop for explicit confirmation before writing implementation code, then audit completion against `tasks/overview.md`.

## Current Phase
Phase 6

## Phases

### Phase 1: Requirements & Discovery
- [x] Read repository rules and q1 prompt.
- [x] Read q1 scaffold documents and project evidence files.
- [x] Identify missing required inputs and modeling ambiguities.
- [x] Document findings in `findings.md`.
- **Status:** complete

### Phase 2: Pre-Code Confirmation
- [x] Write q1 problem audit and proposed interpretation.
- [x] Write blocking confirmation state before code implementation.
- [x] Process user option C and supplement missing statement files.
- [x] Wait for explicit confirmation after re-audit.
- **Status:** complete

### Phase 3: Implementation
- [x] Write failing tests for q1 behavior.
- [x] Implement required q1 scripts after confirmation.
- [x] Generate numeric outputs and strategy comparison tables.
- [x] Generate required figures with figure data and metadata.
- **Status:** complete

### Phase 4: Validation & Documentation
- [x] Run validation checks required by `tasks/task1.txt`.
- [x] Update q1 evidence, experiments, results, manifest, devlog, registries, and evidence chain.
- [x] Run `python scripts/check_repo.py`.
- **Status:** complete

### Phase 5: Overview Audit
- [x] Compare completed q1 artifacts against `tasks/overview.md`.
- [x] Record pass/fail gaps and residual risks.
- [x] Mark goal complete only if all explicit requirements are verified.
- **Status:** complete

### Phase 6: q1 Review Audit Follow-Up
- [x] Compare completed q1 artifacts against `tasks/q1_review.md`.
- [x] Fix reported metric averaging, step sensitivity, and configured sensitivity grid.
- [x] Update q1 documentation and evidence records after refreshed outputs.
- [x] Rerun full verification and repository self-check.
- **Status:** complete

## Key Questions
1. Should implementation use the `overview.md` unified interpretation for q1? Pending user confirmation after re-audit.
2. Should missing `question.md` and `questions/q1/brief.md` be treated as absent source files, or should `cumcm_gmcm2026_qinsen_Model1.pdf_by_PaddleOCR-VL-1.6.md` serve as the recovered题面? Resolved by user option C; supplemented from OCR file.
3. Should wind use the scaled formula `W(h)=20+3e-6(h-10000)^2` with positive values as tailwind? Superseded by user-specified `W(h)=20+3e-5(h-10000)^2`.
4. Should the main result use the original `c_T=2.8e-4` and include `2.8e-5` as sensitivity/comparison only? Pending confirmation.

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Stop before implementation code | The active objective explicitly requires blocking before code writing. |
| Use q1 documentation/status files for pre-code work | This preserves evidence of ambiguity and prevents silent parameter changes. |
| Treat q1 status as not implementable until confirmation | The model structure changes depend on user acceptance of key assumptions. |
| Supplement missing statement files from OCR source | User selected option C; OCR file is the only available local题面 source. |
| Use `W(h)=20+3e-5(h-10000)^2` as q1 main wind formula | User explicitly specified this wind-speed correction. |
| Proceed to implementation after pre-code block | User selected A on `confirm_stage1_q1_reaudit_002`. |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Initial file reads displayed mojibake in shell output | 1 | Re-read key files with PowerShell UTF-8 output and `-Encoding UTF8`. |
| `question.md` and `questions/q1/brief.md` required by task prompt were not found | 1 | Recorded as blocking missing input in q1 review and modeling state. |

## Notes
- No formal q1 implementation code has been written yet.
- Existing scaffold code remains unchanged pending explicit confirmation.
