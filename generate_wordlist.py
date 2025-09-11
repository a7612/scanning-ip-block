import random
import csv
import os
import subprocess
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed

os.makedirs("storage", exist_ok=True)

PASS_FILE = "storage\\pass.csv"
FAIL_FILE = "storage\\fail.csv"
DOMAIN_FILE = "storage\\domain.csv"
REMOVED_FILE = "storage\\domain_removed.csv"
WORDLIST_FILE = "storage\\wordlist.csv"


def valid_ip(ip: str) -> bool:
    parts = ip.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def ip_key(addr: str):
    return [int(x) for x in addr.split(".")]


class GenerateWordlist:
    def __init__(self):
        self.generated = self._load_existing()

    def _load_existing(self):
        ips = set()
        if os.path.exists(WORDLIST_FILE):
            with open(WORDLIST_FILE, "r", encoding="utf-8-sig") as f:
                for row in csv.reader(f):
                    if row and valid_ip(row[0]):
                        ips.add(row[0].strip())
        return ips

    def _save_wordlist(self):
        with open(WORDLIST_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for ip in sorted(self.generated, key=ip_key):
                writer.writerow([ip])

    def generate_ip(self):
        while True:
            ip = ".".join(str(random.randint(0, 255)) for _ in range(4))
            if ip not in self.generated:
                self.generated.add(ip)
                return ip

    @staticmethod
    def ping(ip: str) -> bool:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        wait = "-w" if platform.system().lower() == "windows" else "-W"
        cmd = ["ping", param, "1", wait, "1", ip]
        try:
            return subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
        except Exception:
            return False

    def run(self, count=100, workers=50):
        # 1️⃣ load dữ liệu
        removed_ips, domain_ips = [], []
        if os.path.exists(REMOVED_FILE):
            with open(REMOVED_FILE, "r", encoding="utf-8-sig") as f:
                removed_ips = [row[0].strip() for row in csv.reader(f) if row and valid_ip(row[0])]

        if os.path.exists(DOMAIN_FILE):
            with open(DOMAIN_FILE, "r", encoding="utf-8-sig") as f:
                domain_ips = [row[0].strip() for row in csv.reader(f) if row and valid_ip(row[0])]

        new_ips = [self.generate_ip() for _ in range(count)]

        # 2️⃣ test đa luồng
        tasks = [(ip, False) for ip in removed_ips] + \
                [(ip, True) for ip in domain_ips] + \
                [(ip, False) for ip in new_ips]

        results = {"pass": set(), "fail": set(), "alive_domain": {}, "dead_domain": set()}

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.ping, ip): (ip, check_domain) for ip, check_domain in tasks}
            for future in as_completed(futures):
                ip, check_domain = futures[future]
                ok = future.result()
                if check_domain:
                    if ok:
                        results["alive_domain"][ip] = True
                        results["pass"].add(ip)
                        print(f"{ip} -> STILL ALIVE ✅")
                    else:
                        results["dead_domain"].add(ip)
                        results["fail"].add(ip)
                        print(f"{ip} -> DEAD ❌ (removed from domain.csv)")
                else:
                    if ok:
                        results["pass"].add(ip)
                        print(f"{ip} -> OK")
                    else:
                        results["fail"].add(ip)
                        print(f"{ip} -> FAIL")

        # 3️⃣ batch save xuống file
        # pass.csv
        all_pass = results["pass"]
        if os.path.exists(PASS_FILE):
            with open(PASS_FILE, "r", encoding="utf-8-sig") as f:
                all_pass.update([row[0].strip() for row in csv.reader(f) if row and valid_ip(row[0])])
        with open(PASS_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for ip in sorted(all_pass, key=ip_key):
                writer.writerow([ip])

        # fail.csv
        all_fail = results["fail"]
        if os.path.exists(FAIL_FILE):
            with open(FAIL_FILE, "r", encoding="utf-8-sig") as f:
                all_fail.update([row[0].strip() for row in csv.reader(f) if row and valid_ip(row[0])])
        with open(FAIL_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for ip in sorted(all_fail, key=ip_key):
                writer.writerow([ip])

        # domain.csv (chỉ giữ IP alive)
        if os.path.exists(DOMAIN_FILE):
            with open(DOMAIN_FILE, "r", encoding="utf-8-sig") as f:
                rows = [row for row in csv.reader(f) if row and row[0].strip() not in results["dead_domain"]]
        else:
            rows = []
        with open(DOMAIN_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        # lưu lại wordlist
        self._save_wordlist()

        print(f"\n✅ Done: {len(results['pass'])} OK, {len(results['fail'])} FAIL, {len(results['dead_domain'])} removed from domain.csv")


if __name__ == "__main__":
    g = GenerateWordlist()
    g.run(200, workers=50)
