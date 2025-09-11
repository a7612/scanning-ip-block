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

def main():
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

    # Sắp xếp
    results.sort(key=lambda x: ip_key(x[0]))
    kept_ips = [ip for ip, _ in results]
    removed_ips.sort(key=ip_key)

    # Xuất file domain.csv
    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for ip, domain in results:
            writer.writerow([ip, domain])

    # Ghi đè lại pass.csv
    with open(PASS_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for ip in kept_ips:
            writer.writerow([ip])

    # Lưu domain_removed.csv
    with open(NA_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for ip in removed_ips:
            writer.writerow([ip])

    print(f"\n✅ Đã lưu file: {OUTPUT_FILE}")
    print(f"✅ pass.csv đã được lọc, còn lại {len(kept_ips)} IP có domain")
    print(f"✅ domain_removed.csv đã lưu {len(removed_ips)} IP bị loại")

if __name__ == "__main__":
    main()
