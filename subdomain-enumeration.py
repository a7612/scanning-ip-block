# Subdomain Enumeration

# Prompt ==========
# Nhớ comment liên tục trước khi crud
# Liên tục tối ưu hóa code, output
# class SubDomainEnumration
# Tự động tạo resource/wordlist + 5 file: scheme.csv, subdomain.csv, domain.csv, topdomain.csv, port.csv
# Cho phép input domain (ví dụ: dev.api.example.com) -> tách thành scheme, sub, name, tld, port. Append dữ liệu lưu vào 3 file. Mặc định scheme, port dựa trên subdomain hoặc ngược lại, sort và check duplicate
# Check với 50 Worker
# Check thử xem nó ping được không
# Check thử xem nó reverse được không
# Xuất kết quả ra CSV/JSON

#!/usr/bin/env python3
"""
SubDomainEnumeration (patched: dedup & sort)
- Giữ nguyên tính năng trước đó (5 file, parse scheme+port, add, check, export)
- Thêm: sort + dedup cho các file wordlist, gọi sau batch-add và lúc khởi tạo
- Mỗi CRUD file có comment trước khi thao tác
"""

import os
import csv
import socket
import subprocess
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlparse

class SubDomainEnumeration:
    def __init__(self, base_path="resource/wordlist", workers=50, verbose=True, port_timeout=0.8):
        self.base_path = base_path
        self.workers = int(workers)
        self.verbose = verbose
        self.port_timeout = float(port_timeout)

        # Tạo thư mục wordlist nếu chưa tồn tại
        os.makedirs(self.base_path, exist_ok=True)

        # Định nghĩa các file wordlist (5 file theo yêu cầu)
        self.scheme_file = os.path.join(self.base_path, "scheme.csv")
        self.sub_file = os.path.join(self.base_path, "subdomain.csv")
        self.domain_file = os.path.join(self.base_path, "domain.csv")
        self.tld_file = os.path.join(self.base_path, "topdomain.csv")
        self.port_file = os.path.join(self.base_path, "port.csv")

        # Default values
        default_schemes = ["http", "https", "ftp", "ssh"]
        default_subs = ["www", "mail", "ftp"]
        default_domains = ["example"]
        default_tlds = ["com", "org", "net"]
        default_ports = [21, 22, 23, 53, 68, 69, 80, 139, 443, 445, 1110, 4444]

        # Comment: tạo file scheme nếu chưa có
        self._ensure_file(self.scheme_file, default_schemes)
        # Comment: tạo file subdomain nếu chưa có
        self._ensure_file(self.sub_file, default_subs)
        # Comment: tạo file domain nếu chưa có
        self._ensure_file(self.domain_file, default_domains)
        # Comment: tạo file topdomain nếu chưa có
        self._ensure_file(self.tld_file, default_tlds)
        # Comment: tạo file port nếu chưa có
        self._ensure_file(self.port_file, [str(p) for p in default_ports])

        # Load wordlists
        self.schemes = self._load_file(self.scheme_file)
        self.subdomains = self._load_file(self.sub_file)
        self.domains = self._load_file(self.domain_file)
        self.tlds = self._load_file(self.tld_file)
        self.ports = [int(p) for p in self._load_file(self.port_file)]

        # Mapping port -> scheme (basic)
        self.port_scheme_map = {
            80: "http",
            443: "https",
            21: "ftp",
            22: "ssh",
            23: "telnet",
            53: "dns",
            68: "dhcp",
            69: "tftp",
            139: "netbios-ssn",
            445: "microsoft-ds",
            1110: "unknown",
            4444: "metasploit"
        }

        # Heuristics: infer scheme/port from subdomain tokens
        self.sub_infer_map = {
            "ftp": ("ftp", 21),
            "ssh": ("ssh", 22),
            "smtp": ("smtp", 25),
            "mail": ("smtp", 25),
            "www": ("http", 80),
            "api": ("http", 80),
            "secure": ("https", 443),
            "https": ("https", 443),
            "http": ("http", 80)
        }

        # Normalize wordlists at startup: dedup & sort
        self._dedup_and_sort_all()

    # ------------------- IO helpers -------------------
    def _ensure_file(self, path, default_values):
        """Tạo file nếu chưa có. Comment trước khi CRUD (ghi file)."""
        if not os.path.exists(path):
            # Comment: sắp tạo file và ghi các giá trị mặc định
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                for v in default_values:
                    writer.writerow([v])

    def _load_file(self, filename):
        """Đọc file CSV đơn giản, trả về danh sách (strip)."""
        if not os.path.exists(filename):
            return []
        with open(filename, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            return [row[0].strip() for row in reader if row and row[0].strip()]

    def _append_unique(self, filename, value):
        """Thêm giá trị vào file (unique). Comment trước khi CRUD (append)."""
        values = self._load_file(filename)
        if value is None or str(value).strip() == "":
            return False
        sval = str(value).strip()
        if sval not in values:
            # Comment: mở file để append giá trị duy nhất
            with open(filename, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([sval])
            if self.verbose:
                print(f"[+] Lưu '{sval}' vào {os.path.basename(filename)}")
            return True
        return False

    def _dedup_and_sort_file(self, filename, numeric=False):
        """Comment: đọc file, dedup, sắp xếp, và ghi lại (sort+unique)."""
        if not os.path.exists(filename):
            return
        with open(filename, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            items = [row[0].strip() for row in reader if row and row[0].strip()]
        if not items:
            return
        if numeric:
            # Comment: chuyển sang int để sort numeric, sau đó ghi lại dưới dạng string
            try:
                unique_nums = sorted({int(x) for x in items})
                lines = [str(x) for x in unique_nums]
            except ValueError:
                # fallback to text sort if some non-numeric values present
                lines = sorted(set(items), key=lambda s: s.lower())
        else:
            lines = sorted(set(items), key=lambda s: s.lower())
        # Comment: ghi đè file với nội dung đã dedup và sắp xếp
        with open(filename, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for v in lines:
                writer.writerow([v])
        if self.verbose:
            print(f"[+] Sorted & dedup {os.path.basename(filename)} ({len(lines)} entries)")

    def _dedup_and_sort_all(self):
        """Comment: dedup+sort cho tất cả 5 file và reload lists."""
        self._dedup_and_sort_file(self.scheme_file, numeric=False)
        self._dedup_and_sort_file(self.sub_file, numeric=False)
        self._dedup_and_sort_file(self.domain_file, numeric=False)
        self._dedup_and_sort_file(self.tld_file, numeric=False)
        self._dedup_and_sort_file(self.port_file, numeric=True)
        # reload lists after normalization
        self.schemes = self._load_file(self.scheme_file)
        self.subdomains = self._load_file(self.sub_file)
        self.domains = self._load_file(self.domain_file)
        self.tlds = self._load_file(self.tld_file)
        self.ports = [int(p) for p in self._load_file(self.port_file)]

    # ------------------- Domain input (enhanced) -------------------
    def add_input_domain(self, domain_str):
        """
        Nhận một domain input (plain host hoặc URL), parse scheme+port sub/name/tld,
        append unique vào files (không tự sort mỗi lần add để tránh overhead khi batch-add).
        Sau batch-add, CLI sẽ gọi _dedup_and_sort_all().
        """
        if not domain_str or not isinstance(domain_str, str):
            return False

        original = domain_str.strip()
        s = original

        parsed = urlparse(s if "://" in s else "//" + s)
        schemes_to_add = []
        if parsed.scheme and parsed.scheme != "":
            schemes_to_add.append(parsed.scheme.lower())

        netloc = parsed.netloc if parsed.netloc else parsed.path
        host = netloc
        port_from_input = None
        if "@" in netloc:
            host = netloc.split("@", 1)[1]
        if ":" in host and not host.startswith("["):
            parts = host.rsplit(":", 1)
            if parts[1].isdigit():
                host, port_from_input = parts[0], int(parts[1])
        elif host.startswith("[") and "]" in host:
            if "]:" in host:
                hpart, ppart = host.split("]:", 1)
                host = hpart.strip("[]")
                if ppart.isdigit():
                    port_from_input = int(ppart)

        host = host.strip()
        if host == "":
            return False

        parts = host.split(".")
        if len(parts) < 2:
            sub = ""
            name = host
            tld = ""
        else:
            if len(parts) == 2:
                sub = ""
                name = parts[0]
                tld = parts[1]
            else:
                sub = '.'.join(parts[:-2])
                name = parts[-2]
                tld = parts[-1]

        ports_to_add = set()
        schemes_to_add_final = set()

        if schemes_to_add:
            for sc in schemes_to_add:
                schemes_to_add_final.add(sc)
        else:
            inferred = False
            for token in (sub.split('.') if sub else []):
                tok = token.lower()
                if tok in self.sub_infer_map:
                    sc, p = self.sub_infer_map[tok]
                    schemes_to_add_final.add(sc)
                    ports_to_add.add(p)
                    inferred = True
            if not inferred:
                schemes_to_add_final.update(["http", "https"])
                ports_to_add.update([80, 443])

        if port_from_input:
            ports_to_add.add(port_from_input)
            if port_from_input in self.port_scheme_map:
                schemes_to_add_final.add(self.port_scheme_map[port_from_input])
        else:
            for sc in list(schemes_to_add_final):
                for p, ps in self.port_scheme_map.items():
                    if ps == sc:
                        ports_to_add.add(p)

        if not schemes_to_add_final:
            schemes_to_add_final.update(["http", "https"])
        if not ports_to_add:
            ports_to_add.update([80, 443])

        # Commit to files (append unique). Không sort ở đây để tối ưu batch-add.
        written = False
        # Comment: append subdomain if exists
        if sub:
            written |= self._append_unique(self.sub_file, sub)
        # Comment: append domain name
        written |= self._append_unique(self.domain_file, name)
        # Comment: append tld if present
        if tld:
            written |= self._append_unique(self.tld_file, tld)

        # Comment: append schemes parsed/inferred
        for sc in schemes_to_add_final:
            self._append_unique(self.scheme_file, sc)

        # Comment: append ports parsed/inferred (store as string)
        for p in ports_to_add:
            self._append_unique(self.port_file, str(p))

        # reload simple lists (note: final normalization done by _dedup_and_sort_all())
        self.schemes = self._load_file(self.scheme_file)
        self.subdomains = self._load_file(self.sub_file)
        self.domains = self._load_file(self.domain_file)
        self.tlds = self._load_file(self.tld_file)
        self.ports = [int(p) for p in self._load_file(self.port_file)]

        return written

    # ------------------- Candidate generation -------------------
    def generate_candidates(self):
        """Sinh các FQDN từ các wordlist."""
        for sub in self.subdomains:
            for dom in self.domains:
                for tld in self.tlds:
                    if sub:
                        yield f"{sub}.{dom}.{tld}"
                    else:
                        yield f"{dom}.{tld}"

    # ------------------- Network checks -------------------
    def _dns_resolve(self, fqdn):
        try:
            return socket.gethostbyname(fqdn)
        except socket.gaierror:
            return None

    def _ping(self, ip, timeout=1):
        if not ip:
            return False
        if os.name == 'nt':
            cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip]
        else:
            cmd = ["ping", "-c", "1", "-W", str(int(timeout)), ip]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return proc.returncode == 0
        except Exception:
            return False

    def _reverse_ptr(self, ip):
        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return None

    def _check_port(self, ip, port, timeout=None):
        if timeout is None:
            timeout = self.port_timeout
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                rc = s.connect_ex((ip, port))
                return rc == 0
        except Exception:
            return False

    def check_domain(self, fqdn):
        """Kiểm tra DNS, Ping, Reverse và danh sách ports (kèm scheme inferred)."""
        res = {
            'domain': fqdn,
            'ip': None,
            'ping': False,
            'reverse': None,
            'ports': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        ip = self._dns_resolve(fqdn)
        if not ip:
            return res

        res['ip'] = ip
        res['ping'] = self._ping(ip)
        res['reverse'] = self._reverse_ptr(ip)

        # Kiểm tra các port đã cấu hình trong port.csv
        for p in self.ports:
            scheme = self.port_scheme_map.get(p) or (self.schemes[0] if self.schemes else None)
            open_status = self._check_port(ip, p)
            res['ports'].append({'port': p, 'scheme': scheme, 'open': open_status})

        return res

    # ------------------- Runner & export -------------------
    def run(self, export_csv=True, export_json=True, out_prefix=None):
        if out_prefix is None:
            out_prefix = datetime.now().strftime('results_%Y%m%d_%H%M%S')

        candidates = list(self.generate_candidates())
        total = len(candidates)
        if self.verbose:
            print(f"[*] Tìm kiếm {total} candidate với {self.workers} workers...")

        results = []
        with ThreadPoolExecutor(max_workers=self.workers) as exe:
            futures = {exe.submit(self.check_domain, fqdn): fqdn for fqdn in candidates}
            done = 0
            for future in as_completed(futures):
                done += 1
                r = future.result()
                results.append(r)
                if self.verbose and done % max(1, int(self.workers/5)) == 0:
                    print(f"    - {done}/{total} done")

        # Export CSV: flatten ports into repeated rows (one row per domain+port)
        if export_csv:
            csv_path = f"{out_prefix}.csv"
            # Comment: mở file csv để ghi kết quả (flatten port entries)
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['domain', 'ip', 'ping', 'reverse', 'port', 'scheme', 'open', 'timestamp'])
                for r in results:
                    if r.get('ports'):
                        for p in r['ports']:
                            writer.writerow([r['domain'], r.get('ip') or '', r.get('ping'), r.get('reverse') or '', p['port'], p.get('scheme') or '', p.get('open'), r.get('timestamp')])
                    else:
                        writer.writerow([r['domain'], r.get('ip') or '', r.get('ping'), r.get('reverse') or '', '', '', '', r.get('timestamp')])
            if self.verbose:
                print(f"[+] Xuất CSV: {csv_path}")

        # Export JSON: lưu structure hoàn chỉnh
        if export_json:
            json_path = f"{out_prefix}.json"
            # Comment: mở file json để ghi kết quả đầy đủ
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            if self.verbose:
                print(f"[+] Xuất JSON: {json_path}")

        return results

# ------------------- CLI -------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SubDomain Enumeration - patched (scheme+port parsing, sort/dedup)')
    parser.add_argument('--base', '-b', default='resource/wordlist', help='Base path chứa wordlist')
    parser.add_argument('--workers', '-w', type=int, default=50, help='Số worker song song')
    parser.add_argument('--add', '-a', nargs='+', help='Thêm 1 hoặc nhiều domain vào wordlist (vd: dev.api.example.com hoặc https://host:8443)')
    parser.add_argument('--no-export', action='store_true', help='Không xuất CSV/JSON')
    parser.add_argument('--quiet', action='store_true', help='Giảm output')
    parser.add_argument('--port-timeout', type=float, default=0.8, help='Timeout (s) cho check port TCP')
    args = parser.parse_args()

    verbose = not args.quiet
    enum = SubDomainEnumeration(base_path=args.base, workers=args.workers, verbose=verbose, port_timeout=args.port_timeout)

    if args.add:
        for d in args.add:
            added = enum.add_input_domain(d)
            if added:
                print(f"[+] Đã thêm {d} và lưu vào wordlist (kèm scheme/port nếu detect được).")
            else:
                print(f"[-] {d} không có thay đổi (có thể đã tồn tại hoặc không hợp lệ).")
        # Comment: sau khi batch-add, normalize tất cả file (dedup + sort) 1 lần
        enum._dedup_and_sort_all()
        exit(0)

    results = enum.run(export_csv=not args.no_export, export_json=not args.no_export)

    # Hiển thị tóm tắt
    ok = [r for r in results if r['ip']]
    no = [r for r in results if not r['ip']]
    if verbose:
        print('\n=== TÓM TẮT ===')
        print(f'Total candidates : {len(results)}')
        print(f'Resolved         : {len(ok)}')
        print(f'Unresolved       : {len(no)}')
        if len(ok) > 0:
            print('\nMột vài mục resolve được:')
            for r in ok[:20]:
                open_ports = [str(p['port']) for p in r.get('ports', []) if p.get('open')]
                print(f"  - {r['domain']} -> {r['ip']} | Ping: {'OK' if r['ping'] else 'Fail'} | Reverse: {r['reverse'] or 'None'} | Open ports: {', '.join(open_ports) if open_ports else 'None'}")

    print('\nHoàn thành. Xuất file results_*.csv và results_*.json trong thư mục hiện hành.')
