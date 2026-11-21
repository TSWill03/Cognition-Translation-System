"""CTS analysis: purely descriptive stats; no synthetic quality grades."""
import csv,json,statistics,hashlib,collections
from pathlib import Path
root=Path(__file__).resolve().parent
results=root/"results"
with (results/"translations.csv").open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
summary=json.loads((results/"summary.json").read_text(encoding="utf-8"))
ok=[r for r in rows if r["status"]=="success"]
assert len(rows)==300 and len(ok)==300,("Inconsistent dataset",len(rows),len(ok))
assert len(set(r["id"] for r in rows))==300
values=[float(r["duration_ms"]) for r in ok]
startups=[float(x["warmup_ms"]) for x in summary if x["warmup_ms"] is not None]
out={
"n_cases":len(rows),"n_success":len(ok),"n_failure":len(rows)-len(ok),
"language_count":len({r["tgt_lang"] for r in rows}),
"prompt_count":len({r["sentence_id"] for r in rows}),
"candidate_lower_resource_count":len({r["tgt_lang"] for r in rows if r["low_resource_candidate"]=="1"}),
"inference_total_s":round(sum(values)/1000,3),
"inference_mean_ms":round(statistics.mean(values),3),
"inference_median_ms":round(statistics.median(values),3),
"inference_p95_ms":round(sorted(values)[int(.95*(len(values)-1))],3),
"warmup_total_s":round(sum(startups)/1000,3),
"warmup_median_s":round(statistics.median(startups)/1000,3),
"numeric_candidate_checks":sum(int(r["numbers_expected"])>0 for r in ok),
"numeric_flagged":sum(int(r["numbers_expected"])>0 and r["numbers_preserved"]=="0" for r in ok),
"output_identical_to_source":sum(r["output_text"].strip()==r["source_text"].strip() for r in ok),
"very_short_ratio":sum(float(r["length_ratio"])<.3 for r in ok),
"very_long_ratio":sum(float(r["length_ratio"])>2.5 for r in ok),
"language_stats":summary
}
(results/"study_statistics.json").write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
for id in ["S02","S04","S07","S19"]:
  print("EXAMPLE",id,flush=True)
  for row in [r for r in rows if r["sentence_id"]==id and r["tgt_lang"] in ["pt","ja","zh","eu","ga","sw","bn"]]:
    print(row["tgt_lang"],row["output_text"].replace("\n"," ")[:260],flush=True)
print("STATS",json.dumps({k:v for k,v in out.items() if k!="language_stats"},ensure_ascii=False),flush=True)
print("PER_LANG",json.dumps([{k:v for k,v in x.items() if k in ["language","sum_translate_ms","warmup_ms","numeric_checks_passed","numeric_checks"]} for x in summary],ensure_ascii=False),flush=True)
