# CTS Entity Integrity v1 — reproducible experiment

## Scope and provenance

Executed on 2026-11-22 on an NVIDIA RTX 3050 Ti Laptop GPU (4 GB), Windows, Python 3.11, Argos 1.11.0, CTranslate2 4.9.0; exact model hashes and settings in manifest.json. Base runtime: CTS PR #3, commit 2a14b6c. Raw public outputs, authored synthetic corpus, and diagnostic results are retained unchanged in this experiment directory. No audio, private chapters, credentials or cloud translation requests are included in the public dataset.

The test matrix is 15 fictional name groups × 10 shared bilingual templates × 2 directions (150 EN→PT and 150 PT→EN). These are 300 distinct text cases, NOT 300 independent semantic scenarios. Name-group holdout covers groups 5–14, but templates are shared and the ambiguity list was designed with corpus examples in mind. This is an exploratory engineering stress test, not a blinded held-out quality benchmark or a claim of generalization. References are author-created templates, not human translations from novels.

Observed: **2436 records, 2436 nonempty successes**. This includes 12 G2 offline replays, not 12 additional model calls. H reuses already produced candidates; do not count its rows as new independent inference. All durations for full profiles are amortized batched times from a single warmed run, except H, which includes all candidate costs. Not equivalent to end-to-end book time. G local LLM per-request latency differs from amortized batching.

## Full-matrix results (both directions)

| Profile | Exact entity mentions | Extra entity mentions | Exploratory character F2 | Total seconds |
|---|---:|---:|---:|---:|
| A_raw | 797/810 (98.40%) | 1 | 81.31 | 4.865 |
| B_normalize | 801/810 (98.89%) | 1 | 79.43 | 4.845 |
| C_marker | 804/810 (99.26%) | 1 | 79.21 | 6.935 |
| D_semantic | 804/810 (99.26%) | 1 | 79.78 | 4.458 |
| E_context | 804/810 (99.26%) | 1 | 79.78 | 4.293 |
| F_glossary | 804/810 (99.26%) | 1 | 79.34 | 4.614 |
| H_guarded | 805/810 (99.38%) | 1 | 79.51 | 25.244 |
| I_ner | 801/810 (98.89%) | 1 | 78.01 | 8.581 |

Full per-direction numeric/term/layout diagnostics are in summary.json. The F2 implementation is exploratory, not standardized SacreBLEU chrF. Exact mentions do NOT prove correct agent, action, negation, grammar, or meaning. Number spelling can be equivalent; literal mismatches require review. Term tests are limited to two authored glossary examples. Extra counts can reflect ordinary words and are not perfect semantic detection.

## Named-entity detection

Actual spaCy 3.8.x, English en_core_web_sm 3.8.0 and Portuguese pt_core_news_sm 3.8.0: exact source-span mention precision 543/564, recall 543/810. News/web models are not trained specifically for fantasy names. The I profile deliberately does not get the gold glossary; E uses explicit prior-context cues, not a neural recognizer. D/E equivalence is unsurprising because the synthetic contexts explicitly introduce roles.

## Local LLM pilot

Qwen3:4b via Ollama loopback, 12 selected cases (6 per direction; includes exact Lith regression and ambiguity/diagnostic stress cases). Reference not supplied to model. G originally accepted 12/12; a manual inspection surfaced a number mutation 30 -> 3:00 and a broken contraction. A totals-only gate is insufficient. G2 replays the same outputs with per-value count / punctuation checks and accepts 8/12.
Gate rejection reasons: {'lost_dialogue_quotes': 2, 'introduced_numeric_literal': 1, 'lost_numeric_literal': 1, 'broken_word_punctuation': 1}. G2 is an after-the-fact regression repair, not an independent validation. It cannot prove fidelity or exclude new semantic errors. Human ratings are not available.

| Same pilot subset | Exact names | F2 mean |
|---|---:|---:|
| H before correction | 32/34 | 73.77 |
| G LLM candidate | 34/34 | 75.95 |
| G2 stricter replay | 34/34 | 77.00 |

## Concrete regression: Lith

- A_raw: “Não abra o portão,” disse Selia. Ainda não voltou a verdade.
- B_normalize: "Não abra o portão", disse Selia. "A Lith ainda não voltou."
- C_marker: "Não abra o portão", disse Selia. "Lith ainda não voltou."
- D_semantic: "Não abra o portão", disse Selia. "Lith ainda não voltou."
- H_guarded: "Não abra o portão", disse Selia. "A Lith ainda não voltou."
- G_llm_candidate: Não abra o portão, Selia disse. Lith ainda não voltou.
- G2_replay: "Não abra o portão", disse Selia. "A Lith ainda não voltou."

## Adverse findings and deployment gate

- Ambiguous names Hope/May/Will/Silver can be ordinary words; naive glossary replacements can mistranslate true ordinary uses. C/D/E/F skip a conservative list, so misses remain. The POS/span-specific J/K prototype passed unit-level tests, but two real runs stalled before a complete result; no J/K performance or quality claim is made. Inspect and resolve the stall separately.
- H chooses by integrity alone and can prefer a syntactically worse tie. Name preservation is not a semantic score. LLM is not a trustworthy automatic judge or repair mechanism; G2 is a diagnostic gate, not certified translation.
- Exact memory replay uses 30 **simulated** approvals, 3000 lookup operations, and 30 changed-context misses; this is an in-memory functional test, not saved user approvals or quality evidence.
- Keep current published Veredra stable. Before enabling this research runtime by default: review real chapters side by side, include independent bilingual reviewers and novel domains, add semantic negation/agent/sequence checks, test contextual aliases and longer passages, compare an independent model under license review, and audit memory persistence/invalidation. No automatic promotion of incomplete or unapproved outputs.

## Reproduce

From CTS PR branch, with installed Argos direct EN↔PT packages and configured local CUDA libraries:

    python -m unittest discover -s tests -v
    python benchmark_entity_integrity.py --out experiments/entity_integrity_v1
    python benchmark_ner.py --root experiments/entity_integrity_v1 --models <local-spacy-model-dir>
    python benchmark_llm_correction.py --root experiments/entity_integrity_v1 --limit 12
    python benchmark_guard_replay.py --root experiments/entity_integrity_v1

NER model directories can be explicitly installed from the official spaCy releases (3.8.0) as isolated targets; English model metadata: https://spacy.io/models/en; Portuguese: https://spacy.io/models/pt/. Use Qwen3:4b only if the local model is installed. The optional J/K scripts are experimental and were not completed. Use a *copy* of the public results directory for ratings, never commit reviewer comments or private books.

    python review_server.py --root <local-copy> --port 8792 --open-browser

External model comparison: NLLB-200 distilled 600M has CC-BY-NC-4.0 terms and a research-only/document translation caveat; it is not a drop-in commercial model (https://huggingface.co/facebook/nllb-200-distilled-600M). Evaluate independently licensed translation models and LLMs before commercial product adoption.
