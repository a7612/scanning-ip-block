#!/usr/bin/env python3
"""
reverse_lookup.py
- Đọc storage/pass.csv
- Reverse DNS lookup:
  + Thành công -> append lookup_domain_pass.csv
  + Thất bại   -> append lookup_domain_failed.csv + xóa IP khỏi pass.csv
"""

import csv, socket, os, argparse, shutil, tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

DEFAULT_IN = "storage/pass.csv"
PASS_HEADER = ["ip", "timestamp_utc"]
PASS_OUT_PASS = "storage/lookup_domain_pass.csv"
PASS_OUT_FAIL = "storage/lookup_domain_failed.csv"

def _now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def read_pass(path):
    if not os.path.isfile(path): return []
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("ip")]

def append_csv(path, rows, header):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.isfile(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(header)
        w.writerows(rows)

def reverse_lookup(ip, timeout=5):
    try:
        socket.setdefaulttimeout(timeout)
        name, _, _ = socket.gethostbyaddr(ip)
        return name.rstrip(".") if name else None
    except Exception: return None

def process(rows, workers=20, timeout=5):
    passed, failed = [], []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(reverse_lookup, r["ip"], timeout): r for r in rows}
        for fut in as_completed(futs):
            r, ip = futs[fut], futs[fut]["ip"]
            dom = fut.result()
            if dom:
                passed.append([ip, dom, r.get("timestamp_utc", ""), _now_utc()])
                print(f"[+] {ip} -> {dom}")
            else:
                failed.append([ip, r.get("timestamp_utc", ""), _now_utc()])
                print(f"[-] {ip} -> n/a")
    return passed, failed

def write_pass(path, rows):
    tmp_fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".")
    os.close(tmp_fd)
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(PASS_HEADER); w.writerows(rows)
    shutil.move(tmp, path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--infile", default=DEFAULT_IN)
    ap.add_argument("-w", "--workers", type=int, default=30)
    ap.add_argument("-t", "--timeout", type=int, default=5)
    a = ap.parse_args()

    rows = read_pass(a.infile)
    if not rows: return print("No IPs found.")

    shutil.copy2(a.infile, a.infile + ".bak")
    print(f"Backup -> {a.infile}.bak")

    print(f"Lookup {len(rows)} IPs with {a.workers} workers ...")
    passed, failed = process(rows, a.workers, a.timeout)

    if passed:
        append_csv(PASS_OUT_PASS, passed, ["ip","domain","timestamp_utc","checked_at_utc"])
        print(f"Saved {len(passed)} -> {PASS_OUT_PASS}")
    if failed:
        append_csv(PASS_OUT_FAIL, failed, ["ip","timestamp_utc","checked_at_utc"])
        print(f"Saved {len(failed)} -> {PASS_OUT_FAIL}")
        write_pass(a.infile, [[p[0], p[2]] for p in passed])
        print(f"Removed {len(failed)} IPs from {a.infile}")

    print("Done.")

if __name__ == "__main__":
    main()
