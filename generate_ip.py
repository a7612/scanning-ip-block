import random
import platform
import subprocess
import os
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone


class GenerateIP:
    @staticmethod
    def _generate_ip() -> str:
        return ".".join(str(random.randint(0, 255)) for _ in range(4))

    @staticmethod
    def _now_utc() -> str:
        """Trả về thời gian UTC hiện tại (string)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    @staticmethod
    def ping(ip: str) -> bool:
        system = platform.system().lower()
        param = "-n" if "windows" in system else "-c"
        wait = "-w" if "windows" in system else "-W"
        cmd = ["ping", param, "1", wait, "1", ip]
        try:
            return subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
        except Exception:
            return False

    def _filter_alive(self, ips: list[str], worker: int) -> list[str]:
        """Ping nhiều IP song song, trả về list IP còn sống."""
        alive = []
        with ThreadPoolExecutor(max_workers=worker) as executor:
            future_to_ip = {executor.submit(self.ping, ip): ip for ip in ips}
            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    if future.result():
                        print(f"[+] {ip} Alive")
                        alive.append(ip)
                    else:
                        print(f"[-] {ip} Dead")
                except Exception as e:
                    print(f"[!] {ip} Error: {e}")
        return alive

    def _check_existing(self, path: str, worker: int) -> list[str]:
        """Đọc pass.csv, test lại và ghi đè với IP sống."""
        if not os.path.isfile(path):
            return []

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing = [row["ip"].strip() for row in reader if "ip" in row]

        if not existing:
            return []

        print(f"[*] Kiểm tra lại {len(existing)} IP trong {path} ...")
        alive = self._filter_alive(existing, worker)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ip", "timestamp_utc"])
            now = self._now_utc()
            for ip in alive:
                writer.writerow([ip, now])

        print(f"[*] {len(alive)}/{len(existing)} IP còn sống, đã cập nhật {path}")
        return alive

    def run(self, count: int = 0, worker: int = 10, out_path: str = "storage/pass.csv"):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # 1. Check lại IP cũ
        self._check_existing(out_path, worker)

        # 2. Sinh và test IP mới
        new_ips = [self._generate_ip() for _ in range(count)]
        alive_new = self._filter_alive(new_ips, worker)

        if alive_new:
            now = self._now_utc()
            file_exists = os.path.isfile(out_path)
            with open(out_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["ip", "timestamp_utc"])
                for ip in alive_new:
                    writer.writerow([ip, now])
            print(f"\n[+] Thêm {len(alive_new)} IP mới vào {out_path}")
        else:
            print("\n[-] Không có IP mới nào Alive")

        return alive_new


if __name__ == "__main__":
    g = GenerateIP()
    g.run(count=2000, worker=20)
