"""CTS research: install a fixed list of Argos packages for reproducible 300-case matrix.
Reads official Argos package index; install results are recorded, errors not hidden.
"""
import argostranslate.package as pkg
import argostranslate.translate as translation
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime,timezone
from pathlib import Path
import json,time,sys
ROOT=Path(__file__).resolve().parent
ROOT.mkdir(parents=True,exist_ok=True)
TARGETS=["pt","es","fr","de","ja","zh","ar","eo","eu","ga","gl","ky","sw","ur","bn"]
pkg.update_package_index()
index=pkg.get_available_packages()
lookup={p.to_code:p for p in index if p.from_code=="en"}
installed={x.code for x in translation.get_installed_languages()}
out=[]
def download(code):
    if code in installed: return code,None,"installed"
    item=lookup.get(code)
    if item is None:return code,None,"unavailable"
    try:
        t=time.perf_counter()
        path=item.download()
        return code,str(path),f"downloaded_in_{round(time.perf_counter()-t,2)}s"
    except Exception as e:return code,None,f"download_failed:{type(e).__name__}:{str(e)[:180]}"
print("DOWNLOAD START",len(TARGETS),flush=True)
with ThreadPoolExecutor(max_workers=3) as executor:
    futures={executor.submit(download,c):c for c in TARGETS}
    for f in as_completed(futures):
        code,path,state=f.result()
        if path:
            try:pkg.install_from_path(path);state+=";installed"
            except Exception as e:state+=f";installation_failed:{type(e).__name__}:{str(e)[:180]}"
        item=lookup.get(code)
        result={"language":code,"name":getattr(item,"to_name","unknown"),"package_version":str(getattr(item,"package_version","")),"result":state}
        out.append(result)
        (ROOT/"model_installation.json").write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False),flush=True)
print("COMPLETE INSTALLED",sum("installed" in r["result"] for r in out),"OF",len(TARGETS),flush=True)
