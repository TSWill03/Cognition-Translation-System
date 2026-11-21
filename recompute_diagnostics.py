"""Revise only numeric diagnostics, preserve all original 300 translations and timings."""
from __future__ import annotations
import csv,hashlib,json
from collections import defaultdict
from pathlib import Path
from benchmark300 import check_numbers
ROOT=Path(__file__).resolve().parent
DATA=ROOT/"results"
path=DATA/"translations.csv"
preexisting=json.loads((DATA/"manifest.json").read_text(encoding="utf-8"))
if preexisting.get("numeric_metric_version")=="unicode_decimal_v2":
    print("Already migrated: numeric diagnostics v2; no files modified.")
    raise SystemExit(0)
with path.open(newline="",encoding="utf-8-sig") as f: reader=csv.DictReader(f); fieldnames=reader.fieldnames; rows=list(reader)
assert len(rows)==300 and len({x["id"] for x in rows})==300, "Original 300 translations required"
def hash_core(items):
    safe=[{k:r[k] for k in ["id","source_text","output_text","status","duration_ms"]} for r in items]
    return hashlib.sha256(json.dumps(safe,ensure_ascii=False,sort_keys=True).encode("utf-8")).hexdigest()
original_hash=hash_core(rows)
changed=[]; v1_flags=0
for r in rows:
    if r["status"]!="success":continue
    if int(r["numbers_expected"])>0 and r["numbers_preserved"]=="0":v1_flags+=1
    expected,kept=check_numbers(r["source_text"],r["output_text"])
    previous=(r["numbers_expected"],r["numbers_preserved"])
    new=(str(expected),str(kept) if expected else "")
    if previous!=new:
       changed.append({"id":r["id"],"old":previous,"new":new})
    r["numbers_expected"],r["numbers_preserved"]=new
with path.open("w",encoding="utf-8-sig",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=fieldnames);writer.writeheader();writer.writerows(rows)
assert hash_core(rows)==original_hash, "Translation content changed"
by=defaultdict(list)
for r in rows:by[r["tgt_lang"]].append(r)
summary_path=DATA/"summary.json"
summary=json.loads(summary_path.read_text(encoding="utf-8"))
for item in summary:
    cases=by[item["language"]]
    item["numeric_checks"]=sum(int(r["numbers_expected"])>0 and r["status"]=="success" for r in cases)
    item["numeric_checks_passed"]=sum(int(r["numbers_expected"])>0 and r["numbers_preserved"]=="1" for r in cases)
summary_path.write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
manifest_path=DATA/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
manifest.update({"numeric_metric_version":"unicode_decimal_v2","numeric_metric_updated_after_inference":True,
 "numeric_v1_flagged":v1_flags,"translation_content_sha256":original_hash})
manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
report={"n_records":len(rows),"v1_flagged":v1_flags,
 "v2_flagged":sum(int(r["numbers_expected"])>0 and r["numbers_preserved"]=="0" for r in rows),
 "diagnostics_updated":len(changed),"original_output_and_timing_hash":original_hash,
 "changed_ids":changed,"note":"The raw translations and timings have not changed."}
(DATA/"numeric_diagnostic_migration.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k!="changed_ids"},ensure_ascii=False),flush=True)
