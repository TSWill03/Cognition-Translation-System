"""Loopback human-review lab. No content is sent to the internet."""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

def app(root, port, open_browser=False):
    root=root.resolve()
    lock=threading.Lock()
    template=(Path(__file__).parent/"review_lab.html").read_bytes()
    def read_data():
        data=json.loads((root/"results.json").read_text(encoding="utf-8"))
        for case in data["cases"]:
            rows=[r for r in data["results"] if r["case_id"]==case["id"] and r["status"]=="success"]
            random.Random(case["id"]+"cts-review-v1").shuffle(rows)
            case["candidates"]=[{"id":hashlib.sha256((case["id"]+"|"+r["profile"]).encode()).hexdigest()[:16],
                                  "label":chr(65+i),"text":r["output"],"profile":r["profile"],
                                  "seconds":r["seconds"],"char_f2":r["char_f2"],
                                  "numeric":f'{r["numbers_preserved"]}/{r["numbers_expected"]}',
                                  "entities":f'{r["entities_preserved"]}/{r["entities_expected"]}'}
                                 for i,r in enumerate(rows)]
        return {"cases":data["cases"],"warmups":data["warmups"],"profiles":data["profiles"]}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,fmt,*args):
            pass
        def reply(self,status,body,mime):
            self.send_response(status)
            self.send_header("Content-Type",mime)
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def send_json(self,obj,status=200):
            self.reply(status,json.dumps(obj,ensure_ascii=False).encode(),"application/json; charset=utf-8")
        def trusted(self):
            return self.headers.get("Host") in (f"127.0.0.1:{port}",f"localhost:{port}")
        def do_GET(self):
            if not self.trusted():
                return self.send_json({"error":"host"},403)
            if self.path=="/":
                return self.reply(200,template,"text/html; charset=utf-8")
            if self.path=="/data":
                try:return self.send_json(read_data())
                except FileNotFoundError:return self.send_json({"error":"benchmark not ready"},503)
            if self.path=="/ratings":
                with lock:
                    p=root/"ratings.json"
                    return self.send_json(json.loads(p.read_text(encoding="utf-8")) if p.exists() else {})
            self.send_json({"error":"not found"},404)
        def do_POST(self):
            if not self.trusted() or self.headers.get("Origin") not in (f"http://127.0.0.1:{port}",f"http://localhost:{port}") or self.path!="/ratings":
                return self.send_json({"error":"forbidden"},403)
            if self.headers.get("Content-Type","").split(";")[0]!="application/json":
                return self.send_json({"error":"content type"},415)
            try:
                size=int(self.headers.get("Content-Length","0"))
                if not 0<size<=1024*1024:raise ValueError()
                obj=json.loads(self.rfile.read(size))
                valid={c["id"]:{r["id"] for r in c["candidates"]} for c in read_data()["cases"]}
                if not isinstance(obj,dict) or obj.get("case") not in valid or obj.get("candidate") not in valid[obj["case"]]:
                    raise ValueError()
                reviewer=obj.get("reviewer","").strip()
                if not reviewer or len(reviewer)>80:raise ValueError()
                record={}
                for k in ("adequacy","fluency"):
                    v=obj.get(k)
                    if v not in (None,1,2,3,4,5):raise ValueError()
                    record[k]=v
                for k in ("entities","numeric","omission","terminology"):
                    v=obj.get(k,"")
                    if v not in ("","ok","error","na"):raise ValueError()
                    record[k]=v
                comment=obj.get("comment","")
                if not isinstance(comment,str) or len(comment)>5000:raise ValueError()
                record.update(comment=comment,case=obj["case"],candidate=obj["candidate"],reviewer=reviewer)
                with lock:
                    p=root/"ratings.json"
                    saved=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
                    saved[reviewer+"|"+obj["case"]+"|"+obj["candidate"]]=record
                    tmp=p.with_suffix(".tmp")
                    tmp.write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding="utf-8")
                    tmp.replace(p)
                self.send_json({"saved":True})
            except (ValueError,TypeError,KeyError,AttributeError):
                self.send_json({"error":"invalid rating"},400)
    server = ThreadingHTTPServer(("127.0.0.1",port),Handler)
    if open_browser:
        import webbrowser
        webbrowser.open("http://127.0.0.1:"+str(port)+"/")
    server.serve_forever()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--port",type=int,default=8791)
    p.add_argument("--open-browser",action="store_true")
    a=p.parse_args()
    app(a.root,a.port,a.open_browser)
