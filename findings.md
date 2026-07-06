# Findings

## 2026-07-06 Pre-Code Discovery

### Required Inputs Read
- `AGENTS.md`: requires complete evidence chain, baseline, validation, sensitivity analysis, paired figures/data, and documentation before q1 can be marked done.
- `tasks/task1.txt`: requires q1 review, derivation, split implementation scripts, numeric outputs, figures, validation, documentation updates, and repo checks.
- `tasks/overview.md`: provides a coherent proposed interpretation for the aircraft cruise-climb model.
- `questions/q1/README.md`, `approach.md`, `manifest.yaml`: still mostly scaffold placeholders.
- `docs/assumptions.md`, `docs/evidence_chain.csv`, `devlog.md`: still initial placeholders.

### Missing Required Files
- `question.md` was required by `tasks/task1.txt` but was not found.
- `questions/q1/brief.md` was required by `tasks/task1.txt` but was not found.
- A likely recovered statement file exists: `cumcm_gmcm2026_qinsen_Model1.pdf_by_PaddleOCR-VL-1.6.md`, but it has not been confirmed as the authoritative replacement.

### Critical Modeling Ambiguities
- The phrase "水平飞行" conflicts with cruise climb unless interpreted as small-flight-path-angle quasi-steady cruise climb.
- The prompt's use of `h(t), V(t)` as "control variables" conflicts with treating them as state/trajectory variables governed by dynamics.
- Fixed final mass `m_f=62000 kg` fixes total fuel burn at `10450 kg`, so total fuel burn cannot distinguish the two q1 strategies.
- The current OCR problem statement gives `W(h)=20+0.00003(h-10000)^2`; this matches the user's later `3e-5` instruction.
- The thrust-specific fuel coefficient `c_T=2.8e-4 kg/(N*s)` appears large; `overview.md` recommends using it as the main题设 parameter and testing `2.8e-5` separately.
- The constant-Mach strategy requires an explicit temperature/speed-of-sound model.

### Proposed Model From `overview.md`
- Flight state: small-angle quasi-steady cruise climb.
- State variables: `(x, h, V, m)`.
- Physical controls: `(T, gamma)`.
- Lift balance: `L ≈ mg`.
- Drag: parabolic polar `C_D=C_D0+k C_L^2`.
- Thrust relation: `T = D + m*dV/dt + mg/V*dh/dt`.
- Closure condition for q1: constant lift coefficient `C_L=C_L*` from initial state.
- Strategy A: constant true airspeed `V=V0`.
- Strategy B: constant Mach `M=M0`, with `V=M0*a(h)`.
- q1 terminal condition: `m(tf)=62000 kg`.
- Compare time, ground distance, final height, and climb-rate distribution; report total fuel as fixed and non-discriminating.

### Current Status
The project is ready for user confirmation of the above interpretation, but not ready for implementation code.

## 2026-07-06 C Option Follow-Up

User selected option C: first supplement `question.md` and `questions/q1/brief.md`, then re-audit before code.

Actions:
- Created `question.md` from the OCR transcription file.
- Created `questions/q1/brief.md` for q1-specific facts and ambiguity list.
- Updated `modeling_state.yaml` and `data/interactions/user_decisions.yaml` with `decision_stage1_001`.
- Re-read the supplemented files and confirmed the original ambiguity remains: implementation still requires confirmation of the `overview.md` interpretation.

New pending confirmation:
- `confirm_stage1_q1_reaudit_001`: confirm whether to proceed with q1 derivation and implementation using the supplemented problem statement plus `overview.md` recommended interpretation.

## 2026-07-06 Wind Formula Override

User specified a revised main wind-speed formula:

```text
W(h)=20+3e-5(h-10000)^2
```

This matches the OCR problem formula `20+0.00003(h-10000)^2` and supersedes the earlier `overview.md` suggestion `20+3e-6(h-10000)^2` for main calculations. The final audit should explicitly note this divergence from `overview.md`.
