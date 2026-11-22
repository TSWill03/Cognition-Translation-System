from pathlib import Path
import json, hashlib, statistics, collections
root=Path('experiments/entity_integrity_v1')
data=json.loads((root/'results.json').read_text(encoding='utf-8'))
manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
summary=json.loads((root/'summary.json').read_text(encoding='utf-8'))
assert len(data['cases'])==300
assert all(r['kind']=='synthetic' for r in data['cases'])
assert manifest['results_sha256']==hashlib.sha256((root/'results.json').read_bytes()).hexdigest()
assert len({(r['case_id'],r['profile']) for r in data['results']})==len(data['results'])
case={r['id']:r for r in data['cases']}
base={r['case_id']:r for r in data['results'] if r['profile']=='H_guarded'}
pilot=[r for r in data['results'] if r['profile']=='G_llm_candidate']
g2=[r for r in data['results'] if r['profile']=='G2_replay']
reasons=collections.Counter(reason for r in g2 for reason in r.get('guard_reasons',[]))
ner=[r['ner'] for r in data['results'] if r['profile']=='I_ner']
def aggregate(mode):
 rs=[r for r in data['results'] if r['profile']==mode and r['status']=='success']
 return (sum(r['entities_preserved'] for r in rs),sum(r['entities_expected'] for r in rs),
         sum(r['entity_extra'] for r in rs),statistics.mean(r['char_f2'] for r in rs),sum(r['seconds'] for r in rs))
lines=[
 '# CTS Entity Integrity v1 — reproducible experiment',
 '',
 '## Scope and provenance',
 '',
 'Executed on 2026-11-22 on an NVIDIA RTX 3050 Ti Laptop GPU (4 GB), Windows, Python 3.11, Argos 1.11.0, CTranslate2 4.9.0; exact model hashes and settings in manifest.json. Base runtime: CTS PR #3, commit 2a14b6c. Raw public outputs, authored synthetic corpus, and diagnostic results are retained unchanged in this experiment directory. No audio, private chapters, credentials or cloud translation requests are included in the public dataset.',
 '',
 'The test matrix is 15 fictional name groups × 10 shared bilingual templates × 2 directions (150 EN→PT and 150 PT→EN). These are 300 distinct text cases, NOT 300 independent semantic scenarios. Name-group holdout covers groups 5–14, but templates are shared and the ambiguity list was designed with corpus examples in mind. This is an exploratory engineering stress test, not a blinded held-out quality benchmark or a claim of generalization. References are author-created templates, not human translations from novels.',
 '',
 f"Observed: **{manifest['observed']} records, {manifest['success']} nonempty successes**. This includes 12 G2 offline replays, not 12 additional model calls. H reuses already produced candidates; do not count its rows as new independent inference. All durations for full profiles are amortized batched times from a single warmed run, except H, which includes all candidate costs. Not equivalent to end-to-end book time. G local LLM per-request latency differs from amortized batching.",
 '',
 '## Full-matrix results (both directions)',
 '',
 '| Profile | Exact entity mentions | Extra entity mentions | Exploratory character F2 | Total seconds |',
 '|---|---:|---:|---:|---:|',
]
for mode in data['profiles']:
 rs=[r for r in data['results'] if r['profile']==mode]
 if len(rs)!=300:continue
 k,n,x,f,t=aggregate(mode);lines.append(f'| {mode} | {k}/{n} ({100*k/n:.2f}%) | {x} | {f:.2f} | {t:.3f} |')
lines+=['','Full per-direction numeric/term/layout diagnostics are in summary.json. The F2 implementation is exploratory, not standardized SacreBLEU chrF. Exact mentions do NOT prove correct agent, action, negation, grammar, or meaning. Number spelling can be equivalent; literal mismatches require review. Term tests are limited to two authored glossary examples. Extra counts can reflect ordinary words and are not perfect semantic detection.',
 '',
 '## Named-entity detection',
 '',
 f"Actual spaCy 3.8.x, English en_core_web_sm 3.8.0 and Portuguese pt_core_news_sm 3.8.0: exact source-span mention precision {sum(x['tp'] for x in ner)}/{sum(x['detected'] for x in ner)}, recall {sum(x['tp'] for x in ner)}/{sum(x['expected'] for x in ner)}. News/web models are not trained specifically for fantasy names. The I profile deliberately does not get the gold glossary; E uses explicit prior-context cues, not a neural recognizer. D/E equivalence is unsurprising because the synthetic contexts explicitly introduce roles.",
 '',
 '## Local LLM pilot',
 '',
 f"Qwen3:4b via Ollama loopback, {len(pilot)} selected cases (6 per direction; includes exact Lith regression and ambiguity/diagnostic stress cases). Reference not supplied to model. G originally accepted {sum(r.get('accepted',False) for r in data['results'] if r['profile']=='G_llm_guarded')}/{len(pilot)}; a manual inspection surfaced a number mutation 30 -> 3:00 and a broken contraction. A totals-only gate is insufficient. G2 replays the same outputs with per-value count / punctuation checks and accepts {sum(r['accepted'] for r in g2)}/{len(g2)}.",
 f"Gate rejection reasons: {dict(reasons)}. G2 is an after-the-fact regression repair, not an independent validation. It cannot prove fidelity or exclude new semantic errors. Human ratings are not available.",
 '',
 '| Same pilot subset | Exact names | F2 mean |',
 '|---|---:|---:|']
for mode,rs in [('H before correction',[base[r['case_id']] for r in pilot]),('G LLM candidate',pilot),('G2 stricter replay',g2)]:
 lines.append(f"| {mode} | {sum(r['entities_preserved'] for r in rs)}/{sum(r['entities_expected'] for r in rs)} | {statistics.mean(r['char_f2'] for r in rs):.2f} |")
lines+=['','## Concrete regression: Lith', '']
for mode in ['A_raw','B_normalize','C_marker','D_semantic','H_guarded','G_llm_candidate','G2_replay']:
 r=next(r for r in data['results'] if r['case_id']=='en-00-00' and r['profile']==mode)
 lines.append(f"- {mode}: {r['output']}")
lines+=['',
 '## Adverse findings and deployment gate',
 '',
 '- Ambiguous names Hope/May/Will/Silver can be ordinary words; naive glossary replacements can mistranslate true ordinary uses. C/D/E/F skip a conservative list, so misses remain. The POS/span-specific J/K prototype passed unit-level tests, but two real runs stalled before a complete result; no J/K performance or quality claim is made. Inspect and resolve the stall separately.',
 '- H chooses by integrity alone and can prefer a syntactically worse tie. Name preservation is not a semantic score. LLM is not a trustworthy automatic judge or repair mechanism; G2 is a diagnostic gate, not certified translation.',
 '- Exact memory replay uses 30 **simulated** approvals, 3000 lookup operations, and 30 changed-context misses; this is an in-memory functional test, not saved user approvals or quality evidence.',
 '- Keep current published Veredra stable. Before enabling this research runtime by default: review real chapters side by side, include independent bilingual reviewers and novel domains, add semantic negation/agent/sequence checks, test contextual aliases and longer passages, compare an independent model under license review, and audit memory persistence/invalidation. No automatic promotion of incomplete or unapproved outputs.',
 '',
 '## Reproduce',
 '',
 'From CTS PR branch, with installed Argos direct EN↔PT packages and configured local CUDA libraries:',
 '',
 '    python -m unittest discover -s tests -v',
 '    python benchmark_entity_integrity.py --out experiments/entity_integrity_v1',
 '    python benchmark_ner.py --root experiments/entity_integrity_v1 --models <local-spacy-model-dir>',
 '    python benchmark_llm_correction.py --root experiments/entity_integrity_v1 --limit 12',
 '    python benchmark_guard_replay.py --root experiments/entity_integrity_v1',
 '',
 'NER model directories can be explicitly installed from the official spaCy releases (3.8.0) as isolated targets; English model metadata: https://spacy.io/models/en; Portuguese: https://spacy.io/models/pt/. Use Qwen3:4b only if the local model is installed. The optional J/K scripts are experimental and were not completed. Use a *copy* of the public results directory for ratings, never commit reviewer comments or private books.',
 '',
 '    python review_server.py --root <local-copy> --port 8792 --open-browser',
 '',
 'External model comparison: NLLB-200 distilled 600M has CC-BY-NC-4.0 terms and a research-only/document translation caveat; it is not a drop-in commercial model (https://huggingface.co/facebook/nllb-200-distilled-600M). Evaluate independently licensed translation models and LLMs before commercial product adoption.',
 ]
(root/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines[:32]))
print('pilot',len(pilot),'G2 reasons',dict(reasons))
