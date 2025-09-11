import csv
import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

os.makedirs("storage", exist_ok=True)

PASS_FILE = "storage\\pass.csv"
OUTPUT_FILE = "storage\\domain.csv"
NA_FILE = "storage\\domain_removed.csv"

MAX_WORKERS = 50 

def valid_ip(ip: str) -> bool:
    parts = ip.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)

def reverse_lookup(ip: str) -> tuple[str, str]:
    """Trả về (ip, domain hoặc N/A)"""
    try:
        return ip, socket.gethostbyaddr(ip)[0]
    except Exception:
        return ip, "N/A"

def ip_key(addr: str):
    return [int(x) for x in addr.split(".")]

def load_csv(file_path: str) -> list[list[str]]:
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        return [row for row in csv.reader(f) if row]

def save_csv(file_path: str, rows: list[list[str]]):
    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def main():
    # lấy danh sách IP từ pass.csv
    ips = []
    if os.path.exists(PASS_FILE):
        with open(PASS_FILE, "r", encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if row and valid_ip(row[0].strip()):
                    ips.append(row[0].strip())

    results = []
    removed_ips = []

    print(f"🔎 Đang tra cứu {len(ips)} IP bằng {MAX_WORKERS} luồng...")

    # chạy đa luồng
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(reverse_lookup, ip): ip for ip in ips}
        for future in as_completed(futures):
            ip, domain = future.result()
            if domain != "N/A":
                results.append((ip, domain))
                print(f"{ip:15} -> {domain}")
            else:
                removed_ips.append(ip)
                print(f"{ip:15} -> N/A  (bỏ)")

    # load dữ liệu cũ
    old_domain = load_csv(OUTPUT_FILE)
    old_pass = load_csv(PASS_FILE)
    old_removed = load_csv(NA_FILE)

    # cập nhật dữ liệu mới
    all_domain = {(row[0], row[1]) for row in old_domain if len(row) >= 2}
    all_domain.update(results)

    kept_ips = {row[0] for row in all_domain}
    removed_set = {row[0] for row in old_removed}
    removed_set.update(removed_ips)

    # sort lại
    all_domain = sorted(list(all_domain), key=lambda x: ip_key(x[0]))
    kept_ips = sorted(list(kept_ips), key=ip_key)
    removed_ips = sorted(list(removed_set), key=ip_key)

    # lưu file
    save_csv(OUTPUT_FILE, [[ip, domain] for ip, domain in all_domain])
    save_csv(PASS_FILE, [[ip] for ip in kept_ips])
    save_csv(NA_FILE, [[ip] for ip in removed_ips])

    print(f"\n✅ Đã append vào: {OUTPUT_FILE}")
    print(f"✅ pass.csv đã cập nhật, còn lại {len(kept_ips)} IP có domain")
    print(f"✅ domain_removed.csv đã lưu {len(removed_ips)} IP bị loại")

if __name__ == "__main__":
    main()
