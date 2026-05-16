---
source_id: SHORT-DRAMA-SAMPLES-SEEDANCE-PHASE1-CANDIDATE-REGISTRY-20260516
title: Seedance 2.0 short-drama sample candidate registry
doc_type: candidate_rule_card
status: candidate
runtime_retrieval: false
created_at: 2026-05-16
source_pack: output/seedance_sample_learning_20260516_155839/candidate_templates_seedance.yaml
promotion_rule: candidate -> visual review -> Seedance test -> whitelist -> runtime rule
---

# Seedance 2.0 Phase 1 Candidate Registry

This card makes the Phase 1 sample-learning output searchable as candidate knowledge only. It must not be treated as an active runtime rule until it passes visual review and Seedance tests.

## Candidate Coverage Families

- `w1_relation_or_half_body_coverage`: candidate W1 relation-first or half-body coverage. Use only as a reference for readable pressure, stable subject distance, and inheritable tail state.
- `w1_reaction_or_dialogue_hold`: candidate W1 reaction/dialogue hold. Use only as a reference for holding a readable hit, refusal, recognition, or frozen reaction without over-cutting.
- `w1_prop_or_information_insert_proxy`: candidate W1 prop/information insert proxy. It is not automatically a prop close-up; promote only after visual review confirms the object is clear and text is not required.
- `w2_long_relation_or_dialogue_hold`: candidate W2 low-complexity longer hold. Use only when action load is low and tail state remains clear.
- `r1_fast_motion_or_short_cut`: candidate R1 fast motion or short-cut emphasis. It requires bound motion/video/keyframe reference or must be degraded into W1/W2 action beats.
- `x_long_overpacked_or_slow_burn_review`: candidate X review bucket. It must not enter prompt_compiler; split, degrade, or route to manual/post workflow.

## Non-Promotion Boundaries

- Sample subtitles, title cards, screen text, logos, watermarks, readable signs, phone text, and document text are negative QC examples only.
- Final prompts must explicitly forbid subtitles, screen text, English subtitles, text overlays, watermarks, logos, readable signs, phone-screen text, and readable document text.
- Candidate entries may inform rhythm, shot task, tailframe handoff, and negative QC, but they must not override the active whitelist.
