"""Local-only, blinded CTS profile comparison. Private chapter inputs stay outside Git."""
import argparse
import collections
import gc
import hashlib
import json
import random
import statistics
import time
from pathlib import Path
from cts_text import TextEngine
from benchmark300 import numbers

PAIRS = [
 ("dialogue", '“Do not open the gate,” Selia said. “Lith has not returned yet.”',
  '“Não abra o portão”, disse Selia. “Lith ainda não voltou.”', ["Selia","Lith"]),
 ("numeric", "The price increased from $9.99 to $12.50. We bought 3 items, not 30.",
  "O preço subiu de US$ 9,99 para US$ 12,50. Compramos 3 itens, não 30.", []),
 ("negation", "If the healer does not arrive before dawn, do not move the wounded soldier.",
  "Se o curandeiro não chegar antes do amanhecer, não mova o soldado ferido.", []),
 ("terms", "The mana core was damaged. The mana core must be repaired before the spell is cast.",
  "O núcleo de mana foi danificado. O núcleo de mana deve ser reparado antes que o feitiço seja lançado.", []),
 ("entities", "Lith Verhen met Solus near the city of Derios. Solus remembered the name of Lith Verhen.",
  "Lith Verhen encontrou Solus perto da cidade de Derios. Solus se lembrou do nome de Lith Verhen.", ["Lith Verhen","Solus","Derios"]),
 ("pronouns", "Mira handed the sword to Ada because Ada had lost her own. Mira kept the shield.",
  "Mira entregou a espada a Ada porque Ada havia perdido a própria. Mira ficou com o escudo.", ["Mira","Ada"]),
 ("layout", '"Stay here," he whispered.\n\nThe room was empty.\n\nShe ran upstairs.',
  '“Fique aqui”, ele sussurrou.\n\nO quarto estava vazio.\n\nEla correu escada acima.', []),
 ("units", "The vial contains 2.5 mL. Keep it below 8 °C for 24 hours.",
  "O frasco contém 2,5 mL. Mantenha-o abaixo de 8 °C por 24 horas.", []),
 ("idiom", "After months of work, the breakthrough came out of the blue.",
  "Após meses de trabalho, a descoberta aconteceu de forma inesperada.", []),
 ("order", "First she locked the door, then touched the rune. Only afterward did the light disappear.",
  "Primeiro ela trancou a porta, depois tocou a runa. Só depois a luz desapareceu.", []),
]
PROFILES = {
 "serial": dict(profile="serial"),
 "cpu512": dict(profile="cpu", batch_tokens=512),
 "cuda512": dict(profile="cuda", batch_tokens=512),
 "cuda1024": dict(profile="cuda", batch_tokens=1024),
 "cuda512-beam2": dict(profile="cuda", batch_tokens=512, beam_size=2),
}

def numeric_counts(source, output):
    expected = collections.Counter(numbers(source))
    found = collections.Counter(numbers(output))
    return sum(expected.values()), sum((expected & found).values())


def char_f2(output, reference):
    """Exploratory character n-gram F2 (1..6), not standardized sacreBLEU chrF."""
    a, b = "".join(output.split()), "".join(reference.split())
    ps, rs = [], []
    for n in range(1, 7):
        x = collections.Counter(a[i:i+n] for i in range(len(a)-n+1))
        y = collections.Counter(b[i:i+n] for i in range(len(b)-n+1))
        if not x or not y:
            continue
        shared = sum((x & y).values())
        ps.append(shared / sum(x.values()))
        rs.append(shared / sum(y.values()))
    p, r = (statistics.mean(ps), statistics.mean(rs)) if ps else (0,0)
    return round(100 * 5 * p * r / (4*p+r), 2) if p+r else 0.0

def cases_for(private_input):
    cases = []
    for name, en, pt, entities in PAIRS:
        cases.append(dict(id="en-"+name, source="en", target="pt", text=en,
                          reference=pt, entities=entities, kind="synthetic"))
        cases.append(dict(id="pt-"+name, source="pt", target="en", text=pt,
                          reference=en, entities=entities, kind="synthetic"))
    if private_input:
        chapters = json.loads(private_input.read_text(encoding="utf-8"))["chapters"]
        sizes = sorted((len(c["content"]), i) for i,c in enumerate(chapters[:100]) if len(c["content"])>1000)
        if sizes:
            for _,i in (sizes[0], sizes[len(sizes)//2], sizes[-1]):
                c = chapters[i]
                cases.append(dict(id=f"chapter-{i+1}", source="en", target="pt", text=c["content"],
                                  reference=None, entities=[], kind="private-chapter"))
    return cases

def run(out, private_input=None, profiles=None):
    out.mkdir(parents=True, exist_ok=True)
    cases = cases_for(private_input)
    profiles = profiles or list(PROFILES)
    data = {"cases":cases, "profiles":{k:PROFILES[k] for k in profiles},
            "results":[], "warmups":[], "method":"Single warmed run per case/configuration; human review pending."}
    for src,tgt in [("en","pt"),("pt","en")]:
        group = [c for c in cases if c["source"]==src and c["target"]==tgt]
        for name in profiles:
            engine = None
            t=time.perf_counter()
            try:
                engine=TextEngine(src,tgt,**PROFILES[name])
                # Equal extra warmup in all profiles.
                engine.translate("The sample is ready." if src == "en" else "A amostra esta pronta.")
                data["warmups"].append(dict(pair=src+"-"+tgt, profile=name,
                                            seconds=round(time.perf_counter()-t,3),
                                            identity=engine.identity, status="success"))
            except Exception as e:
                data["warmups"].append(dict(pair=src+"-"+tgt, profile=name,
                                            seconds=round(time.perf_counter()-t,3),
                                            status="error", error=type(e).__name__))
                print(src,tgt,name,"STARTUP ERROR",type(e).__name__,flush=True)
                engine=None
            for case in group:
                t=time.perf_counter()
                row=dict(case_id=case["id"],profile=name,status="error",output="",seconds=None)
                if engine:
                    try:
                        value=engine.translate(case["text"])
                        expected,kept=numeric_counts(case["text"],value)
                        row.update(status="success",output=value,seconds=round(time.perf_counter()-t,4),
                                   numbers_expected=expected,numbers_preserved=kept,
                                   entities_expected=len(case["entities"]),
                                   entities_preserved=sum(value.count(e)>=case["text"].count(e) for e in case["entities"]),
                                   char_f2=char_f2(value,case["reference"]) if case["reference"] else None)
                    except Exception as e:
                        row.update(error=type(e).__name__,seconds=round(time.perf_counter()-t,4))
                else:
                    row["error"]="ENGINE_UNAVAILABLE"
                data["results"].append(row)
                print(src,tgt,name,case["id"],row["status"],row["seconds"],flush=True)
            del engine
            gc.collect()
            save(out,data)
    return data

def save(out,data):
    path=out/"results.json"
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)
    summary=[]
    for pair in ("en-pt","pt-en"):
        ids={c["id"] for c in data["cases"] if c["source"]+"-"+c["target"]==pair}
        for name in data["profiles"]:
            allr=[r for r in data["results"] if r["case_id"] in ids and r["profile"]==name]
            rows=[r for r in allr if r["status"]=="success"]
            if not allr:continue
            ch=[r for r in rows if r["case_id"].startswith("chapter-")]
            refs=[r["char_f2"] for r in rows if r["char_f2"] is not None]
            summary.append(dict(pair=pair,profile=name,ok=len(rows),planned=len(allr),
                                chapter_seconds=round(sum(r["seconds"] for r in ch),3) if ch else None,
                                synthetic_f2=round(statistics.mean(refs),2) if refs else None,
                                numeric_alerts=sum(r["numbers_preserved"]<r["numbers_expected"] for r in rows),
                                entity_alerts=sum(r["entities_preserved"]<r["entities_expected"] for r in rows)))
    (out/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--private-input",type=Path)
    p.add_argument("--profiles",nargs="+",choices=PROFILES)
    args=p.parse_args()
    run(args.out,args.private_input,args.profiles)
