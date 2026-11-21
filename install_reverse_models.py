"""Explicitly install direct reverse Argos packages target -> English (never auto-run)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from benchmark300 import ROOT, TARGETS


def install(codes: list[str], out: Path) -> int:
    import argostranslate.package as package
    if not codes or any(code not in TARGETS for code in codes):
        raise ValueError("Invalid language selection")
    package.update_package_index()
    available = {(p.from_code, p.to_code): p for p in package.get_available_packages()}
    installed = {(p.from_code, p.to_code) for p in package.get_installed_packages()}
    records = []
    for code in codes:
        status = "already_installed" if (code, "en") in installed else "unavailable"
        error = ""
        entry = available.get((code, "en"))
        if (code, "en") not in installed and entry is not None:
            try:
                # Explicit user action: downloading to the local Argos cache.
                downloaded = entry.download()
                package.install_from_path(downloaded)
                status = "installed"
            except Exception as exc:
                status = "error"
                error = f"{type(exc).__name__}: {str(exc)[:200]}"
        record = {"source": code, "target": "en", "status": status, "error": error,
                  "package_version": str(getattr(entry, "package_version", "unknown"))}
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), "packages": records},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(r["status"] in {"already_installed", "installed"} for r in records) else 2


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--langs", nargs="+", choices=TARGETS, default=["pt"])
    cli.add_argument("--out", type=Path, default=ROOT / "results" / "reverse_installation.json")
    args = cli.parse_args()
    raise SystemExit(install(args.langs, args.out))
