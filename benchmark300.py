"""CTS v0.3: reproducible text-only translation matrix (20 original prompts x 15 targets).
The runner writes actual model outputs and explicit errors; no synthetic successes or fake metrics.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,platform,re,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TARGETS=["pt","es","fr","de","ja","zh","ar","eo","eu","ga","gl","ky","sw","ur","bn"]
NAMES={"pt":"Portuguese","es":"Spanish","fr":"French","de":"German","ja":"Japanese","zh":"Chinese","ar":"Arabic","eo":"Esperanto","eu":"Basque","ga":"Irish","gl":"Galician","ky":"Kyrgyz","sw":"Swahili","ur":"Urdu","bn":"Bengali"}
CANDIDATE_LOWER_RESOURCE={"eo","eu","ga","gl","ky","sw","ur","bn"}
HEADERS=["id","sentence_id","domain","src_lang","tgt_lang","tgt_name","low_resource_candidate","source_text","output_text","input_sha256","duration_ms","status","length_ratio","numbers_expected","numbers_preserved","error"]
def load_prompts(path=ROOT/"prompts.json"):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    ids=[p["id"] for p in data]
    if len(ids)!=20 or len(set(ids))!=20: raise ValueError("Corpus must include 20 unique prompts")
    if any(not p.get("text","").strip() for p in data): raise ValueError("Empty source")
    return data
def numbers(s):
    # Isolated decimal/integer tokens, normalized for comma/dot; unit strings are not evaluated.
    return [m.replace(",",".") for m in re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)",s)]
def check_numbers(src,dst):
    orig=numbers(src); found=numbers(dst)
    # Evaluate multiplicity; comma thousands vs decimal ambiguous: diagnostic only.
    return len(orig), int(all(found.count(v)>=orig.count(v) for v in set(orig)))
def schedule(prompts,targets=TARGETS):
    return [{"id":f"CTS-{lang}-{p['id']}","language":lang,"prompt":p} for lang in targets for p in prompts]
def run_engine(translator,text):
    return translator.translate(text)
def run(*,outdir,targets,limit=None):
    import argostranslate, argostranslate.translate as translate
    outdir.mkdir(parents=True,exist_ok=True)
    prompts=load_prompts()
    corpus_sha=hashlib.sha256((ROOT/"prompts.json").read_bytes()).hexdigest()
    installed={x.code:x for x in translate.get_installed_languages()}
    version=getattr(argostranslate,"__version__",None)
    records=[]; summary=[]
    jobs=schedule(prompts,targets)
    if limit is not None: jobs=jobs[:limit]
    manifest={"design":"CTS-TEXT-300-v1","text_only":True,"source_language":"en",
              "targets":targets,"planned":len(jobs),"prompt_count":len(prompts),
              "source_corpus_sha256":corpus_sha,"python":platform.python_version(),
              "platform":platform.platform(),"argos_version":version,
              "utc_start":datetime.now(timezone.utc).isoformat(),
              "limitations":["No human reference translations","Heuristic checks do not measure adequacy",
                             "No speech translation measured","Short original English prompts only"]}
    (outdir/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    with (outdir/"translations.csv").open("w",newline="",encoding="utf-8-sig") as f:
      writer=csv.DictWriter(f,fieldnames=HEADERS);writer.writeheader()
      for lang in targets:
        cases=[j for j in jobs if j["language"]==lang]
        if not cases:continue
        engine=None; problem=""
        if "en" not in installed or lang not in installed:
            problem="LANGUAGE_MODEL_NOT_INSTALLED"
        else:
            try: engine=installed["en"].get_translation(installed[lang])
            except Exception as e:problem=f"ENGINE_LOAD_ERROR: {type(e).__name__}: {str(e)[:120]}"
            if engine is None and not problem:problem="TRANSLATION_PAIR_UNAVAILABLE"
        warmup_ms=None
        if engine is not None:
            try:
                t0=time.perf_counter();engine.translate("This is a warm-up sentence.")
                warmup_ms=round((time.perf_counter()-t0)*1000,2)
            except Exception as e:problem=f"WARMUP_ERROR: {type(e).__name__}: {str(e)[:120]}";engine=None
        for job in cases:
            p=job["prompt"];src=p["text"];status="success" if engine is not None else "error"
            output="";err=problem;elapsed=None
            if engine is not None:
                t0=time.perf_counter()
                try:
                    output=run_engine(engine,src)
                    if not isinstance(output,str) or not output.strip():status="error";err="EMPTY_OUTPUT"
                except Exception as e:status="error";err=f"INFERENCE_ERROR: {type(e).__name__}: {str(e)[:150]}"
                elapsed=round((time.perf_counter()-t0)*1000,3)
            expected,kept=check_numbers(src,output) if status=="success" else (len(numbers(src)),0)
            row={"id":job["id"],"sentence_id":p["id"],"domain":p["domain"],"src_lang":"en",
                 "tgt_lang":lang,"tgt_name":NAMES[lang],
                 "low_resource_candidate":int(lang in CANDIDATE_LOWER_RESOURCE),
                 "source_text":src,"output_text":output,
                 "input_sha256":hashlib.sha256(src.encode("utf-8")).hexdigest(),
                 "duration_ms":elapsed,"status":status,
                 "length_ratio":round(len(output)/max(1,len(src)),3),
                 "numbers_expected":expected,"numbers_preserved":kept if expected else "",
                 "error":err}
            records.append(row);writer.writerow(row);f.flush()
        counted=[r for r in records if r["tgt_lang"]==lang]
        ok=sum(r["status"]=="success" for r in counted)
        summary.append({"language":lang,"name":NAMES[lang],"planned":len(cases),"success":ok,
                        "error":len(cases)-ok,
                        "warmup_ms":warmup_ms,
                        "sum_translate_ms":round(sum(r["duration_ms"] or 0 for r in counted),3),
                        "numeric_checks":sum(r["numbers_expected"]>0 and r["status"]=="success" for r in counted),
                        "numeric_checks_passed":sum(r["numbers_expected"]>0 and r["status"]=="success" and r["numbers_preserved"]==1 for r in counted)})
        (outdir/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
        print("LANG",json.dumps(summary[-1],ensure_ascii=False),flush=True)
    manifest["utc_end"]=datetime.now(timezone.utc).isoformat()
    manifest["observed"]=len(records)
    manifest["success"]=sum(r["status"]=="success" for r in records)
    manifest["error"]=len(records)-manifest["success"]
    manifest["note"]="Translation executed is not equivalent to linguistically correct translation."
    (outdir/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    print("FINAL",json.dumps({"planned":manifest["planned"],"observed":manifest["observed"],
          "success":manifest["success"],"error":manifest["error"]},ensure_ascii=False),flush=True)
    return 0 if manifest["success"]==manifest["planned"] else 2
if __name__=="__main__":
  parser=argparse.ArgumentParser()
  parser.add_argument("--out",type=Path,default=ROOT/"results")
  parser.add_argument("--langs",nargs="+",choices=TARGETS,default=TARGETS)
  parser.add_argument("--limit",type=int)
  args=parser.parse_args()
  raise SystemExit(run(outdir=args.out,targets=args.langs,limit=args.limit))
