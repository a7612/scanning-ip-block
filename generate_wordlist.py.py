import random
import csv
import os
import subprocess
import platform

os.makedirs("storage", exist_ok=True)

class GenerateWordlist:
    def __init__(self, path="storage\\wordlist.csv", pass_file="storage\\pass.csv", fail_file="storage\\fail.csv"):
        self.path = path
        self.pass_file = pass_file
        self.fail_file = fail_file
        self.generated = self._load_existing()

    def _load_existing(self):
        ips = set()
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8-sig") as f:
                for row in csv.reader(f):
                    if self._valid_ip(row):
                        ips.add(row[0].strip())
        return ips

    @staticmethod
    def _valid_ip(row):
        if not row or not row[0].strip():
            return False
        parts = row[0].split(".")
        return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)

    def _save_all(self):
        def ip_key(addr): return [int(x) for x in addr.split(".")]
        with open(self.path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for ip in sorted(self.generated, key=ip_key):
                writer.writerow([ip])

    def _save_result(self, ip, ok=True):
        """Lưu IP vào file pass.csv hoặc fail.csv (có sort)"""
        file_path = self.pass_file if ok else self.fail_file
        rows = set()

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8-sig") as f:
                for row in csv.reader(f):
                    if row and self._valid_ip(row):
                        rows.add(row[0].strip())

        rows.add(ip)

        def ip_key(addr): return [int(x) for x in addr.split(".")]
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for addr in sorted(rows, key=ip_key):
                writer.writerow([addr])

    def generate_ip(self):
        while True:
            ip = ".".join(str(random.randint(0, 255)) for _ in range(4))
            if ip not in self.generated:
                self.generated.add(ip)
                self._save_all()
                return ip

    def run(self, count=5):
        for _ in range(count):
            ip = self.generate_ip()
            ok = self.ping(ip)
            self._save_result(ip, ok)  # <-- fix: truyền ip (string), không phải [ip]
            status = "OK" if ok else "FAIL"
            print(f"{ip} -> {status}")

    @staticmethod
    def ping(ip):
        """Ping 1 IP để test kết nối"""
        param = "-n" if platform.system().lower() == "windows" else "-c"
        wait = "-w" if platform.system().lower() == "windows" else "-W"
        cmd = ["ping", param, "1", wait, "1", ip]
        try:
            return subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
        except Exception:
            return False


if __name__ == "__main__":
    g = GenerateWordlist()
    g.run(200)  # sinh 200 IP, test kết nối, lưu pass.csv và fail.csv
