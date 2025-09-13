#!/usr/bin/env python3
"""
cleanup_alive_domain.py
- Đọc storage/lookup_domain_pass.csv
- Giữ lại domain alive (HTTP/HTTPS), xóa domain dead
- Tạo backup .bak trước khi ghi đè
"""

import csv, os, shutil, socket, http.client, argparse, tempfile
from urllib.parse import urlparse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_IN = "storage/lookup_domain_pass.csv"

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def tcp_ok(host, port, timeout=3):
    try:
        with socket.create_connection((host, port), timeout): return True
    except: return False

def http_ok(host, port, https=False, timeout=3):
    if not tcp_ok(host, port, timeout): return False
    try:
        conn = (http.client.HTTPSConnection if https else http.client.HTTPConnection)(host, port, timeout=timeout)
        conn.request("HEAD", "/", headers={"User-Agent": "cleanup/1.0"})
        return conn.getresponse().status < 500
    except: return False
    finally:
        try: conn.close()
        except: pass

def target(row):
    dom, ip = row.get("domain","").strip(), row.get("ip","").strip()
    if dom: return urlparse(dom).hostname or dom if "://" in dom else dom
    return ip

def alive(row, timeout=3): 
    t = target(row)
    return http_ok(t,80,False,timeout) or http_ok(t,443,True,timeout)

def read_csv(path):
    if not os.path.isfile(path): return [], []
    with open(path,newline="",encoding="utf-8") as f:
        r=csv.DictReader(f); return list(r), r.fieldnames or []

def write_csv(path, rows, headers):
    fd,tmp=tempfile.mkstemp(dir=os.path.dirname(path) or "."); os.close(fd)
    with open(tmp,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=headers); w.writeheader(); w.writerows(rows)
    shutil.move(tmp,path)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("-i","--infile",default=DEFAULT_IN)
    ap.add_argument("-w","--workers",type=int,default=20)
    ap.add_argument("-t","--timeout",type=float,default=3.0)
    a=ap.parse_args()

    rows,headers=read_csv(a.infile)
    if not rows: return print(f"[{now()}] No rows in {a.infile}. Exit.")

    bak=a.infile+".bak"; shutil.copy2(a.infile,bak); print(f"[{now()}] Backup -> {bak}")
    alive_rows=[]
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs={ex.submit(alive,r,a.timeout):r for r in rows}
        for fut in as_completed(futs):
            r=futs[fut]; t=target(r)
            ok=fut.result()
            print(f"[{now()}] {t:<30} {'ALIVE' if ok else 'DEAD'}")
            if ok: alive_rows.append(r)

    write_csv(a.infile,alive_rows,headers)
    print(f"[{now()}] Done. Alive kept: {len(alive_rows)}/{len(rows)}")

if __name__=="__main__": main()
