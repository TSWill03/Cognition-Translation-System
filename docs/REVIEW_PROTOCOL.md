# CTS human review protocol (planned; not yet performed)

The CTS 300-case benchmark is **text-only and automatic**. A successful translation API call is not evidence of semantic adequacy.

## Reviewer recruitment and process

1. Recruit at least two competent speakers per target language where feasible; declare fluency level and potential conflict of interest.
2. Randomize sample order and blind reviewer to model identity when comparing engines; include the original English text and candidate translated text.
3. Record adequacy (1–5), fluency (1–5), terminology and named-entity treatment (correct / incorrect / not applicable), numerical fidelity, critical omissions, cultural localization and free-text comments. Special scrutiny for low-resource contexts.
4. Include real parallel benchmark references (e.g. FLORES-200) **only after verifying the dataset's actual license and using the exact authorized subset**.
5. Publish aggregate and per-language confidence intervals, inter-annotator agreement and limitations; do not equate a 300-case exploratory sample with language-wide proficiency.

## Reviewer template

`case_id,language,reviewer_code,adequacy_1_5,fluency_1_5,critical_omission_0_1,numeric_correct_0_1,entity_correct_0_1,comment`

## Risk findings requiring reproduction

- `CTS-eu-S19`: English price increase from **$9.99 to $12.50** became **9,99 → 1,50** in Basque output. Apparent deletion of a significant digit.
- `CTS-bn-S19`: truncated-looking Bengali output for the same price-change sentence; requires Bengali reviewer.
- `CTS-*-S02`: personal and place name handling differs, sometimes translating or transliterating proper nouns. Do not infer an incorrect choice without a controlled glossary and bilingual review.
- `CTS-*-S06`: dates/times can be reformatted and trigger false positives in simple regex checks.
- CJK-adjacent and Bengali-digit numeric checks produced false positives with the original v1 detector; replaced by Unicode-aware v2 diagnostics, keeping exact original translations and timings.

## Scope boundaries

No actual meeting audio, speech-to-text, TTS, speaker diarization, PDF-book translation quality, batch translation speed, model alignment or model-to-model quality comparison is tested in this 300-case matrix. These belong to future experiments.
