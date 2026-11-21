# Cognition Translation System (CTS)

> **Research preview — text only.** Open-source laboratory for reproducible multilingual machine translation, developed independently of the Veredra reading app.

**Status (20 November 2026):** CTS v0.3 research prototype. This repository does **not** provide live meetings, speech recognition, voice synthesis, browser extensions, or an online translation API. These are roadmap items, not existing capabilities.

## Research experiment: 300 real translations

The matrix is **20 original English sentences × 15 target languages = 300 individual machine-translation invocations**. The same sentences are used for each target.

Targets: Portuguese (pt), Spanish (es), French (fr), German (de), Japanese (ja), Chinese (zh), Arabic (ar), Esperanto (eo), Basque (eu), Irish (ga), Galician (gl), Kyrgyz (ky), Swahili (sw), Urdu (ur), Bengali (bn).

Eight targets (eo, eu, ga, gl, ky, sw, ur, bn) are **less commonly benchmarked / potential low-resource contexts**. This label is exploratory; it does not claim these languages have few speakers or that CTS uniquely supports them.

**Engine:** Argos Translate 1.11.0, offline translation packages (version per language in `model_installation.json`). Source text is original author-created test material, not copyright-restricted book chapters. Outputs and errors are recorded, never fabricated.

**What is measured:** invocation success/error; inference milliseconds (exclusive of model installation and per-language warm-up); output length; exact numeric-token preservation heuristic; full raw output. **What is not measured:** verified semantic fidelity, grammatical adequacy, cultural appropriateness or superiority over commercial systems. The numerical heuristic is known to undercount localized number representations in CJK scripts.

## Quick start

Requires Python 3.11 or 3.12; Windows/Linux/macOS may have different native dependency support.

```bash
python -m venv .venv
# Activate the venv for your OS
python -m pip install -r requirements.txt
python install_models.py
python benchmark300.py --out results
python -m unittest discover -s tests -v
```

Optional **local text-only demo UI**:

```bash
python -m pip install -r requirements-ui.txt
python -m streamlit run cts_ui.py
```

Install models before disconnecting from the internet. Default translation execution is local and does not send texts to an online API. No private documents should be added to the public dataset.

### Reproducibility

- `prompts.json`: 20 original, public synthetic inputs with IDs and domains.
- `install_models.py`: 15 official language packages and per-package installation outcome.
- `benchmark300.py`: deterministic matrix, per-language warm-up, timestamps, full outputs, errors, locale-aware numeric diagnostic, dataset SHA-256.
- `results/translations.csv`: row-level result, ID, input/output, time, status, diagnostics.
- `results/manifest.json`: runtime versions and run metadata.
- `results/summary.json`: per-language counters.
- `tests/`: unit, contract and regression tests; run offline without models.
- `.github/workflows/tests.yml`: CI for unit tests on Windows/Linux with Python 3.11/3.12. Model-based integration runs are manual.
- `docs/PAPER.md`: exploratory technical preprint, methodology, results, limitations, references.
- `docs/LINKEDIN.md`: publication draft.

```bash
# Quick smoke trial (NOT the full study)
python benchmark300.py --langs pt --limit 2 --out smoke

# Full matrix, logging to a separate directory
python benchmark300.py --out results
```

The intended matrix contains 300 rows but **only actual `status=success` outputs represent completed successful translations**. A nonzero exit indicates at least one failed case. Successful execution must not be confused with correct translation.

## Privacy, licences, ethics

- MIT applies to the original CTS scripts only; upstream packages, model weights, dataset licenses and external services retain their own licenses.
- Argos Translate model downloads are **not committed** to this repository.
- **Meta NLLB-200 (CC BY-NC 4.0) is cited as related academic work only; it is not part of the tested or commercial CTS runtime.** A commercial deployment would require independently verified model rights.
- No actual speech meetings or people were recorded in this experiment.
- Any generated text can be wrong; review required for medical, legal, contractual or safety-critical uses.
- With low-resource languages, claims of adequate translation require human evaluation by competent speakers and preferably parallel references such as FLORES-200.
- Research planning, test scripts and manuscript drafting were **assisted by OpenAI ChatGPT**. Operational outcomes are distinguished from analysis and editorial interpretation.

## Integration and roadmap

Current: text-only local translation; Argos benchmarking; raw outputs; regression tests; local Streamlit research demo.

Proposed later: glossary-aware context engine, models comparison with commercially suitable licenses, document import/export, **real-time bidirectional meeting translation** (ASR → MT → TTS), independent CTS API, connectors for apps including Veredra.

No current functionality should be described as a completed audio/meeting or website integration.

## Citation and contribution

Author/maintainer: **Wicolly Pedro Alcântara**. See `docs/PAPER.md` for references. Please open an issue with the original input, language pair, output, package version, expected behaviour and reproduction steps (do not include private material).

## Sources

- Argos Translate: https://github.com/argosopentech/argos-translate
- CTranslate2: https://opennmt.net/CTranslate2/performance.html
- NLLB paper: https://doi.org/10.1038/s41586-024-07335-x
- FLORES-200: https://github.com/facebookresearch/flores
- COMET: https://aclanthology.org/2020.emnlp-main.213/
- Free publication outlets: https://joss.theoj.org/about and https://zenodo.org/
