"""CTS bidirectional text experiment; independent and model-generated round-trip modes.

This is NOT a measure of translation accuracy. No models are downloaded by this module.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmark300 import ROOT, TARGETS, check_numbers, numbers

COLUMNS = [
    "id", "pair", "direction", "case_id", "domain", "source_kind",
    "src_lang", "tgt_lang", "source_text", "output_text", "input_sha256",
    "duration_ms", "status", "numbers_expected", "numbers_preserved", "error",
]


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_source_corpus(path: Path, language: str) -> list[dict]:
    """Load independent target-language prompts; never infer human reference quality."""
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get(language)
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"No independent source corpus for {language} in {path}")
    ids = [entry.get("id") for entry in entries]
    if len(set(ids)) != len(ids) or any(not isinstance(x, str) or not x for x in ids):
        raise ValueError("Independent case IDs must be unique nonempty strings")
    if any(not isinstance(x.get("text"), str) or not x["text"].strip() for x in entries):
        raise ValueError("Independent source text cannot be empty")
    return entries


class ArgosBackend:
    """Require directly installed package for each direction; do not silently pivot."""

    def __init__(self):
        import argostranslate
        import argostranslate.package as package
        import argostranslate.translate as translate

        self.languages = {language.code: language for language in translate.get_installed_languages()}
        self.packages = [
            {"from": item.from_code, "to": item.to_code,
             "version": str(getattr(item, "package_version", "unknown"))}
            for item in package.get_installed_packages()
        ]
        self.version = getattr(argostranslate, "__version__", "unknown")

    def get_translator(self, src: str, tgt: str):
        if not any(p["from"] == src and p["to"] == tgt for p in self.packages):
            raise LookupError(f"DIRECT_MODEL_NOT_INSTALLED: {src}->{tgt}")
        if src not in self.languages or tgt not in self.languages:
            raise LookupError(f"LANGUAGE_NOT_INSTALLED: {src}->{tgt}")
        engine = self.languages[src].get_translation(self.languages[tgt])
        if engine is None:
            raise LookupError(f"TRANSLATION_PAIR_UNAVAILABLE: {src}->{tgt}")
        return engine


def _translator(backend, source: str, target: str, warmup: str):
    start = time.perf_counter()
    try:
        engine = backend.get_translator(source, target)
        result = engine.translate(warmup)
        if not isinstance(result, str) or not result.strip():
            raise ValueError("EMPTY_WARMUP_OUTPUT")
        return engine, round((time.perf_counter() - start) * 1000, 3), ""
    except Exception as exc:
        return None, round((time.perf_counter() - start) * 1000, 3), f"{type(exc).__name__}: {str(exc)[:200]}"


def _translate_case(*, pair: str, direction: str, case: dict, source_kind: str,
                    src: str, tgt: str, engine, engine_error: str) -> dict:
    source = case["text"]
    output, error, duration = "", engine_error, None
    if engine is not None and source.strip():
        start = time.perf_counter()
        try:
            output = engine.translate(source)
            if not isinstance(output, str) or not output.strip():
                output = ""
                error = "EMPTY_OUTPUT"
            else:
                error = ""
        except Exception as exc:
            error = f"{type(exc).__name__}: {str(exc)[:200]}"
        duration = round((time.perf_counter() - start) * 1000, 3)
    elif not source.strip() and not error:
        error = "UPSTREAM_FORWARD_FAILED"
    status = "success" if output.strip() and not error else "error"
    expected, kept = check_numbers(source, output) if status == "success" else (len(numbers(source)), 0)
    return {
        "id": f"CTSB-{pair}-{direction}-{case['id']}", "pair": pair,
        "direction": direction, "case_id": case["id"], "domain": case.get("domain", ""),
        "source_kind": source_kind, "src_lang": src, "tgt_lang": tgt,
        "source_text": source, "output_text": output, "input_sha256": sha256(source),
        "duration_ms": duration, "status": status, "numbers_expected": expected,
        "numbers_preserved": kept if expected else "", "error": error,
    }


def _summary(rows: list[dict], warmup_ms: float, warmup_error: str) -> dict:
    times = [r["duration_ms"] for r in rows if r["status"] == "success" and r["duration_ms"] is not None]
    return {
        "planned": len(rows), "success": sum(r["status"] == "success" for r in rows),
        "errors": sum(r["status"] == "error" for r in rows),
        "warmup_and_load_ms": warmup_ms, "warmup_error": warmup_error,
        "median_inference_ms": round(statistics.median(times), 3) if times else None,
        "sum_inference_ms": round(sum(times), 3),
        "numeric_alerts": sum(bool(r["numbers_expected"]) and r["status"] == "success"
                              and r["numbers_preserved"] == 0 for r in rows),
    }


def run(*, outdir: Path, targets: list[str], mode: str = "independent", limit: int | None = None,
        reverse_corpus: Path = ROOT / "prompts_reverse.json", backend=None) -> int:
    if mode not in {"independent", "roundtrip"}:
        raise ValueError("mode must be independent or roundtrip")
    if not targets or len(set(targets)) != len(targets) or any(x not in TARGETS for x in targets):
        raise ValueError("Targets must be unique supported language codes")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    english = json.loads((ROOT / "prompts.json").read_text(encoding="utf-8"))
    english = english[:limit]
    backwards = {}
    if mode == "independent":
        backwards = {code: load_source_corpus(reverse_corpus, code)[:limit] for code in targets}
    if backend is None:
        backend = ArgosBackend()
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "design": "CTS-BIDIRECTIONAL-v1", "mode": mode, "text_only": True,
        "directions": [f"en->{code}, {code}->en" for code in targets],
        "reverse_input_provenance": "independently authored candidate text" if mode == "independent" else "machine-generated forward output; NOT independent human text",
        "python": platform.python_version(), "platform": platform.platform(), "cpu_count": os.cpu_count(),
        "argos_version": getattr(backend, "version", "test_backend"),
        "installed_argos_packages": getattr(backend, "packages", []),
        "english_corpus_sha256": hashlib.sha256((ROOT / "prompts.json").read_bytes()).hexdigest(),
        "reverse_corpus_sha256": hashlib.sha256(reverse_corpus.read_bytes()).hexdigest() if mode == "independent" else None,
        "utc_start": datetime.now(timezone.utc).isoformat(),
        "limitations": ["No human verification of translation quality", "Round-trip similarity is NOT adequacy",
                        "No speech measured", "Numeric diagnostics are heuristic", "No independent reverse corpus in roundtrip mode"],
    }
    rows: list[dict] = []
    stats: dict = {}
    with (outdir / "translations.csv").open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=COLUMNS)
        writer.writeheader()
        for code in targets:
            pair = f"en-{code}"
            fwd_engine, fwd_warm, fwd_error = _translator(backend, "en", code, english[0]["text"])
            fwd = [_translate_case(pair=pair, direction="A_to_B", case=c,
                                   source_kind="original_en", src="en", tgt=code,
                                   engine=fwd_engine, engine_error=fwd_error) for c in english]
            for row in fwd:
                writer.writerow(row)
            if mode == "roundtrip":
                rev_cases = [
                    {"id": c["id"], "domain": c.get("domain", ""), "text": row["output_text"]}
                    for c, row in zip(english, fwd)
                ]
                reverse_kind = "machine_generated_forward"
            else:
                rev_cases = backwards[code]
                reverse_kind = f"original_{code}_candidate"
            warmup_text = next((x["text"] for x in rev_cases if x["text"].strip()), "")
            rev_engine, rev_warm, rev_error = _translator(backend, code, "en", warmup_text) if warmup_text else (None, None, "NO_REVERSE_SOURCE")
            rev = [_translate_case(pair=pair, direction="B_to_A", case=c,
                                   source_kind=reverse_kind, src=code, tgt="en",
                                   engine=rev_engine, engine_error=rev_error) for c in rev_cases]
            for row in rev:
                writer.writerow(row)
            fp.flush()
            rows.extend(fwd + rev)
            stats[code] = {"A_to_B": _summary(fwd, fwd_warm, fwd_error),
                           "B_to_A": _summary(rev, rev_warm, rev_error)}
            (outdir / "summary.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"pair": pair, **stats[code]}, ensure_ascii=False), flush=True)
    manifest.update({
        "utc_end": datetime.now(timezone.utc).isoformat(), "planned": len(rows),
        "success": sum(r["status"] == "success" for r in rows),
        "errors": sum(r["status"] == "error" for r in rows),
        "csv_sha256": hashlib.sha256((outdir / "translations.csv").read_bytes()).hexdigest(),
    })
    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FINAL", json.dumps({key: manifest[key] for key in ("planned", "success", "errors")}), flush=True)
    return 0 if manifest["errors"] == 0 else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["independent", "roundtrip"], default="independent")
    parser.add_argument("--langs", nargs="+", choices=TARGETS,
                        help="Defaults to pt for independent mode and all 15 targets for roundtrip mode")
    parser.add_argument("--limit", type=int, help="Max cases per direction per language")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "bidirectional")
    parser.add_argument("--reverse-corpus", type=Path, default=ROOT / "prompts_reverse.json")
    args = parser.parse_args()
    try:
        return run(outdir=args.out, targets=args.langs or (["pt"] if args.mode == "independent" else TARGETS),
                   mode=args.mode, limit=args.limit, reverse_corpus=args.reverse_corpus)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
