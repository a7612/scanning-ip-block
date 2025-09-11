import csv
import os
import socket

os.makedirs("storage", exist_ok=True)

PASS_FILE = "storage\\pass.csv"
OUTPUT_FILE = "storage\\domain.csv"
NA_FILE = "storage\\domain_removed.csv"

def valid_ip(ip: str) -> bool:
    parts = ip.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)

def reverse_lookup(ip: str) -> str:
    """Reverse DNS lookup cho 1 IP"""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return "N/A"

def ip_key(addr: str):
    return [int(x) for x in addr.split(".")]

def main():
    results = []      # IP có domain
    kept_ips = []     # danh sách để ghi lại vào pass.csv
    removed_ips = []  # IP bị loại (N/A)

    if os.path.exists(PASS_FILE):
        with open(PASS_FILE, "r", encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if row and valid_ip(row[0].strip()):
                    ip = row[0].strip()
                    domain = reverse_lookup(ip)
                    if domain != "N/A":
                        results.append((ip, domain))
                        kept_ips.append(ip)
                        print(f"{ip:15} -> {domain}")
                    else:
                        removed_ips.append(ip)
                        print(f"{ip:15} -> N/A  (bỏ)")

    # Sắp xếp
    results.sort(key=lambda x: ip_key(x[0]))
    kept_ips.sort(key=ip_key)
    removed_ips.sort(key=ip_key)

    # Xuất file pass_with_domain.csv
    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for ip, domain in results:
            writer.writerow([ip, domain])

    # Ghi đè lại pass.csv
    with open(PASS_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for ip in kept_ips:
            writer.writerow([ip])

    # Lưu danh sách bị loại
    with open(NA_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for ip in removed_ips:
            writer.writerow([ip])

    print(f"\n✅ Đã lưu file: {OUTPUT_FILE}")
    print(f"✅ pass.csv đã được lọc, còn lại {len(kept_ips)} IP có domain")
    print(f"✅ domain_removed.csv đã lưu {len(removed_ips)} IP bị loại")

if __name__ == "__main__":
    main()
