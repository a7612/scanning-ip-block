import os
import random
import string
import csv
import datetime
import getpass
import uuid
from config import *

# ================== Setup thư mục ==================
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(QUESTIONS_DIR, exist_ok=True)

# ================== Utils ==================
def timestamp_now():
    """Trả về timestamp dạng YYYYMMDD_HHMMSS"""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def current_user():
    """Lấy user hiện tại (nếu lỗi -> unknown_user)"""
    try:
        return getpass.getuser()
    except Exception:
        return "unknown_user"

def log_action(action: str, detail: str = ""):
    """Ghi log hành động vào file theo ngày"""
    ts = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    fn = os.path.join(LOG_DIR, f"{datetime.datetime.now().strftime('%Y%m%d')}.log")
    line = f"{ts} | {current_user()} | {action} | {detail}\n"
    with open(fn, "a", encoding="utf-8") as f:
        f.write(line)

# ================== Core Game ==================
class QuizGame:
    def __init__(self, qdir=QUESTIONS_DIR):
        self.qdir = qdir
        os.makedirs(self.qdir, exist_ok=True)
        # self._categories = self._load_categories()
        self.color_map = self._build_color_map()

    # ----------------- File handling -----------------
    @staticmethod
    def clearsrc():
        """Clear màn hình console"""
        if CLEAR_SCREEN:
            os.system("cls" if os.name == "nt" else "clear")

    def _files(self):
        """Trả về danh sách file CSV trong thư mục"""
        return [f for f in os.listdir(self.qdir) if f.endswith(".csv")]

    def _list_files(self, show=True):
        """Liệt kê file trong thư mục, kèm số lượng câu hỏi"""
        files = self._files()
        if not files:
            print("⚠️ Không có file câu hỏi.")
            return []

        if show:
            print(f"{BRIGHT_GREEN}\n📂 Danh sách file:{RESET}")
            for i, f in enumerate(files, 1):
                path = os.path.join(self.qdir, f)
                try:
                    with open(path, encoding="utf-8-sig") as f_csv:
                        count = sum(1 for _ in csv.reader(f_csv)) - 1
                except Exception:
                    count = 0
                print(f" {i:>2}) {f:<25} | {count} câu hỏi")
        return files

    def _choose_file(self, action="chọn"):
        """Chọn file từ danh sách"""
        files = self._list_files()
        if not files:
            return
        try:
            i = input(f"\n👉 Nhập ID để {action}: ")
            return os.path.join(self.qdir, files[int(i) - 1]) if i.isdigit() and 0 < int(i) <= len(files) else None
        except:
            print("⚠️ Chọn không hợp lệ.")

    def _load(self, path):
        """Đọc file CSV -> list(tuple)"""
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8-sig") as f:
            return [(r["id"], r["answer"], r["question"], r["desc"], r["ref"]) for r in csv.DictReader(f)]

    def _save(self, path, data):
        """Ghi dữ liệu vào file CSV (sort theo đáp án)"""
        data_sorted = sorted(data, key=lambda x: x[1].lower())
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "answer", "question", "desc", "ref"])
            writer.writerows(data_sorted)

    def _show(self, path):
        """In danh sách câu hỏi trong file"""
        data = self._load(path)
        if not data:
            print("❌ File trống.")
            return []

        print("\n📋 DANH SÁCH CÂU HỎI:")
        for i, (_, a, q, d, r) in enumerate(data, 1):
            q_disp, a_disp, d_disp, r_disp = (self._normalize_all(x) for x in (q, a, d, r))
            print(f"{BRIGHT_CYAN}{i:>2})==========\n❓\tCâu hỏi: {RESET}{q_disp}")
            print(f"{GREEN}➤\tĐáp án: {RESET}{a_disp}")
            for label, val, color in [
                (f"{YELLOW}💡\tMô tả: {RESET}", d_disp, YELLOW),
                (f"{CYAN}🔗\tReference: {RESET}", r_disp, CYAN),
            ]:
                if val:
                    print(f"{color}{label} {val}{RESET}")
        return data

    # ----------------- CRUD câu hỏi -----------------
    def _crud(self, mode):
        """Thao tác CRUD trên câu hỏi"""
        path = self._choose_file(mode)
        if not path:
            return
        data = self._show(path)

        def save_and_log(action, msg):
            self._save(path, data)
            log_action(action, f"{os.path.basename(path)} | {msg}")

        if mode == "thêm":
            while True:
                self.clearsrc()
                self._show(path)
                q = input(f"\n❓ Nhập câu hỏi (hoặc nhập exit() để thoát):{RESET} ").strip()
                if q.lower() == "exit()": break
                a = input(f"✅ Nhập đáp án (hoặc nhập exit() để thoát):{RESET}: ").strip()
                if a.lower() == "exit()": break
                if not q or not a:
                    continue
                d = input("💡 Mô tả (có thể bỏ trống): ").strip()
                r = input("🔗 Reference (có thể bỏ trống): ").strip()
                data.append((str(uuid.uuid4()), a, q, d, r))
                save_and_log("ADD_Q", f"Q: {q}")
                print("➕ Đã thêm câu hỏi mới.")

        elif mode == "xoá":
            while True:
                self.clearsrc()
                self._show(path)
                idx = input(f"\n🗑️ {BRIGHT_GREEN}Nhập ID (hoặc nhập {BRIGHT_RED}exit(){BRIGHT_GREEN} để thoát):{RESET} ").strip()
                if idx.lower() == "exit()": break
                if idx.isdigit() and 1 <= int(idx) <= len(data):
                    removed = data.pop(int(idx) - 1)
                    save_and_log("DEL_Q", f"Q: {removed[2]}")
                    print(f"🗑️ Đã xoá: {removed[2]}")
                else:
                    print("❌ ID không hợp lệ.")

        elif mode.startswith("sửa"):
            field_map = {"sửaQ": 2, "sửaA": 1, "sửaD": 3, "sửaR": 4}
            while True:
                self.clearsrc()
                self._show(path)
                idx = input(f"\n🔢 {BRIGHT_GREEN}Nhập ID (hoặc nhập {BRIGHT_RED}exit(){BRIGHT_GREEN} để thoát):{RESET} ").strip()
                if idx.lower() == "exit()": break
                if idx.isdigit() and 1 <= int(idx) <= len(data):
                    entry = list(data[int(idx) - 1])
                    if mode == "sửa":
                        entry[2] = input("❓ Câu hỏi mới: ").strip() or entry[2]
                        entry[1] = input("✅ Đáp án mới: ").strip() or entry[1]
                        entry[3] = input("💡 Mô tả mới: ").strip() or entry[3]
                        entry[4] = input("🔗 Reference mới: ").strip() or entry[4]
                    else:
                        field_idx = field_map[mode]
                        new_val = input(f"✏️ Nhập giá trị mới (cũ: {entry[field_idx]}): ").strip()
                        if new_val:
                            entry[field_idx] = new_val
                    data[int(idx) - 1] = tuple(entry)
                    save_and_log("EDIT_Q", f"{entry}")
                    print("✅ Đã sửa thành công.")

    # ----------------- Game logic -----------------
        # ----------------- Game logic -----------------
    def _options(self, correct, pool, n):
        """Sinh ra danh sách đáp án lựa chọn"""
        pool = list(set(pool) - {correct, "Đúng", "Sai"})
        return random.sample(pool, min(n - 1, len(pool))) + [correct]

    @staticmethod
    def _progress_bar(percent, width=30):
        """Hiển thị progress bar"""
        filled = int(width * percent // 100)
        return "[" + "=" * filled + " " * (width - filled) + f"] {percent:.1f}%"
    
    @staticmethod
    def _build_color_map():
        """Tạo map {TOKEN} -> ANSI từ config"""
        import config
        return {
            f"{{{k}}}": v
            for k, v in vars(config).items()
            if k.isupper() and isinstance(v, str) and v.startswith(f"\033")
        }
    
    def _normalize_all(self, text, max_passes=1):
        """Chuẩn hóa \n, \t và thay {COLOR} -> ANSI (lặp nhiều lần nếu cần)"""
        if not text:
            return text
        last = None
        passes = 0
        while text != last and passes < max_passes:
            last = text
            # B1: chuẩn hóa ký tự đặc biệt
            text = text.replace("\\n", "\n").replace("\\t", "\t").replace(".\n", "\n")
            # B2: thay token màu
            for token, ansi in self.color_map.items():
                text = text.replace(token, ansi)
            passes += 1
        return text
    
    def _get_options(self, q, a, data, all_ans, n_opts):
        ql = q.lower()

        if "nhận định đúng sai" in ql:
            return ["Đúng", "Sai"]

        special_map = KEYWORD
        for kw in special_map:
            if kw in ql:
                group = {a, *[ans for _, ans, ques, *_ in data if kw in ques.lower()]}
                opts = self._options(a, group, n_opts)
                return list(dict.fromkeys(self._normalize_all(opt) for opt in opts))
            
        opts = self._options(a, all_ans, n_opts)
        return list(dict.fromkeys(self._normalize_all(opt) for opt in opts))
        
        # return [self._normalize_all(opt) for opt in self._options(a, all_ans, n_opts)]

    def _feedback(self, ok, chosen, q, a, d, r, qid):
        """Hiển thị phản hồi sau khi trả lời"""
        if ok:
            print(f"{GREEN}✅ Chính xác!{RESET}")
            log_action(f"CHOSEN:{qid}", f"{chosen} - {q} Đúng + 1 điểm")
        else:
            print(f"{RED}❌ Sai!{RESET} ➤ Đáp án đúng: {a}")
            log_action(f"CHOSEN:{qid}", f"{chosen} - {q} Sai")
        if d:
            print(f"{YELLOW}💡 Mô tả: {d}{RESET}")
        if r:
            print(f"{CYAN}🔗 Tham chiếu:{r}{RESET}")

    def _export_results(self, results, score, total):
        """Xuất kết quả quiz ra CSV"""
        wrong = total - score
        percent = (score / total * 100) if total else 0.0
        print("\n" + "=" * 60)
        print(f"{BLUE}🎯 BẢNG ĐIỂM CHI TIẾT{RESET}")
        print(f"{'#':>3}  {'RESULT':^8}  {'CORRECT':^20}")
        print("-" * 60)
        for r in results:
            res_sym = f"{GREEN}✅{RESET}" if r["ok"] else f"{RED}❌{RESET}"
            print(f"{r['index']:>3})  {res_sym:^8}   {r['correct']:<20}")
        print("-" * 60)
        print(f"{GREEN}✅ Đúng : {score}{RESET}    {RED}❌ Sai : {wrong}{RESET}    {CYAN}📊 Tỉ lệ: {percent:.1f}%{RESET}")
        print(self._progress_bar(percent))

        # Xuất ra CSV
        csv_path = os.path.join(EXPORT_DIR, f"quiz_results_{timestamp_now()}.csv")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", datetime.datetime.now().isoformat()])
            w.writerow(["user", current_user()])
            w.writerow(["total_questions", total])
            w.writerow(["score", score])
            w.writerow(["wrong", wrong])
            w.writerow(["percent", f"{percent:.1f}"])
            w.writerow([])
            w.writerow(["idx", "question", "correct", "ok", "desc", "reference"])
            for r in results:
                w.writerow([r["index"], r["question"], r["correct"], r["ok"], r["desc"], r.get("ref", "")])
        print(f"{BRIGHT_GREEN}✅ Đã export kết quả: {csv_path}{RESET}")

    def _ask_choice(self, mapping):
        """Hỏi người chơi chọn đáp án, trả về lựa chọn hợp lệ"""
        while True:
            pick = input("👉 Nhập đáp án: ").lower().strip()
            if pick in mapping:
                return mapping[pick]
            print("⚠️ Lựa chọn không hợp lệ, nhập lại đi!")
            log_action("CHOSEN", "Nhập thất bại")

    def _check_answer(self, chosen, q, a, data):
        """Kiểm tra đáp án người chơi chọn có đúng không""" 
        correct_answers = [ ans for _, ans, ques, *_ in data if ques.strip().lower() == q.strip().lower() ] 
        return chosen.lower() in (self._normalize_all(ca).lower() for ca in correct_answers)

    def _quiz(self, data, n_opts=None, max_qs=None):
        """Chạy quiz trên dataset"""
        if not data:
            print("❌ Không có câu hỏi.")
            return

        # 🔀 Lấy pool câu hỏi (random + giới hạn nếu cần)
        pool = (data * ((max_qs // len(data)) + 1))[:max_qs] if max_qs else data
        if max_qs:
            random.shuffle(pool)

        all_ans = [a for _, a, _, _, _ in data]
        results, score = [], 0

        for i, (qid, a, q, d, r) in enumerate(pool, 1):
            print(f"\n" + "-" * 60)

            # Chuẩn hóa hiển thị

            """Chuẩn hóa \n, \t và màu (lặp nhiều lần nếu cần)"""
            # Chuẩn hóa \n, \t và màu (có thể lặp nhiều lần nếu cần)
            # q_disp, a_disp, d_disp, r_disp, data_disp, all_ans_disp = (self._normalize_all(x, 40) for x in (q, a, d, r, data, all_ans))
            q_disp, a_disp, d_disp, r_disp = (self._normalize_all(x) for x in (q, a, d, r))
            print(f"{i}. ❓ {q_disp}\n")

            # Tạo lựa chọn
            opts = self._get_options(q_disp, a_disp, data, all_ans, n_opts)
            random.shuffle(opts)
            mapping = dict(zip(string.ascii_lowercase, opts))
            for k, v in list(mapping.items())[:len(opts)]:
                print(f"{BRIGHT_GREEN}\t{k}){RESET} {v}{RESET}\n")

            # Người chơi chọn
            chosen = self._ask_choice(mapping)

            # ✅ Kiểm tra đúng/sai
            ok = self._check_answer(chosen, q, a_disp, data)
            if ok:
                score += 1

            results.append({
                "index": i, "question": q_disp, "correct": a_disp,
                "desc": d_disp, "ref": r_disp, "ok": ok
            })

            # Phản hồi
            self._feedback(ok, chosen, q_disp, a_disp, d_disp, r_disp, qid)

        # Xuất kết quả cuối
        self._export_results(results, score, len(results))

    def play_file(self):
        """Chơi quiz theo 1 file"""
        path = self._choose_file("chơi")
        if path:
            self._quiz(self._load(path), n_opts=MAX_GENERATE_NORMAL_ANSWERS, max_qs=MAX_GENERATE_NORMAL_QUESTIONS)

    def play_all(self):
        """Chơi quiz trên tất cả file"""
        data = [q for f in self._files() for q in self._load(os.path.join(self.qdir, f))]
        self._quiz(data, n_opts=MAX_GENERATE_ALL_ANSWERS, max_qs=MAX_GENERATE_ALL_QUESTIONS)

    # ----------------- Menu -----------------
    def manage_questions(self):
        """Menu quản lý câu hỏi"""
        actions = {
            "1": ("thêm",   f"{BRIGHT_GREEN}➕ Thêm nội dung{RESET}"),
            "2": ("xoá",    f"{BRIGHT_RED}🗑️ Xoá nội dung{RESET}"),
            "3": ("sửa",    f"{BRIGHT_YELLOW}✏️ Sửa toàn bộ nội dung{RESET}"),
            "4": ("sửaQ",   f"{BRIGHT_YELLOW}✏️ Sửa câu hỏi cụ thể{RESET}"),
            "5": ("sửaA",   f"{BRIGHT_YELLOW}✏️ Sửa đáp án cụ thể{RESET}"),
            "6": ("sửaD",   f"{BRIGHT_YELLOW}✏️ Sửa mô tả cụ thể{RESET}"),
            "7": ("sửaR",   f"{BRIGHT_YELLOW}✏️ Sửa tham khảo cụ thẻ{RESET}"),
        }
        while True:
            self.clearsrc()
            print(f"\n{BRIGHT_CYAN}====={BRIGHT_GREEN} 📋 QUẢN LÝ NỘI DUNG  {RESET}{BRIGHT_CYAN}====={RESET}")
            print(f"\n{BRIGHT_GREEN}===\nCác chức năng hiện tại:\n{RESET}")
            [print(f"{BRIGHT_GREEN} {k}) {label}{RESET}") for k, (_, label) in actions.items()]
            print(f"\n{BRIGHT_GREEN}Hoặc nhập {BRIGHT_RED}exit(){BRIGHT_GREEN} 🔙 quay lại{RESET}")
            ch = input(f"\n{BRIGHT_GREEN}👉 Nhập lựa chọn: {RESET}").strip().lower()
            if ch == "exit()": 
                self.clearsrc()
                break
            if ch in actions: self._crud(actions[ch][0])
            else: print("⚠️ Lựa chọn không hợp lệ.")

    def manage_files(self):
        """Menu quản lý file"""
        actions = {
            "1": ("CREATE_FILE", f"➕ {BRIGHT_GREEN}Tạo file{RESET}", self._create_file),
            "2": ("DELETE_FILE", f"🗑️ {BRIGHT_RED}Xoá file{RESET}", self._delete_file),
            "3": ("RENAME_FILE", f"✏️ {BRIGHT_YELLOW}Đổi tên file{RESET}", self._rename_file),
        }
        while True:
            try:
                self.clearsrc()
                print(f"\n{BRIGHT_CYAN}====={BRIGHT_GREEN} 📂 QUẢN LÝ FILE  {RESET}{BRIGHT_CYAN}====={RESET}")
                self._list_files()
                print(f"\n{BRIGHT_CYAN}===\nCác chức năng hiện tại:\n{RESET}")
                [print(f"{BRIGHT_CYAN} {k}) {label}{RESET}") for k, (_, label, _) in actions.items()]
                print(f"\n{BRIGHT_CYAN}Hoặc nhập {BRIGHT_RED}exit(){BRIGHT_CYAN} 🔙 quay lại{RESET}")
                ch = input(f"\n{BRIGHT_CYAN}👉 Nhập lựa chọn: {RESET}").strip().lower()
                if ch == "exit()": 
                    self.clearsrc()
                    break
                if ch in actions:
                    act, _, func = actions[ch]; func(act)
                else: print("⚠️ Lựa chọn không hợp lệ.")
            except FileNotFoundError:
                break

    # ----------------- Xử lý file -----------------
    def _create_file(self, act):
        """➕ Tạo file CSV mới"""
        name = input("📄 Nhập tên file mới (không cần .csv): ").strip()
        if not name: return
        path = os.path.join(self.qdir, f"{name}.csv")
        if os.path.exists(path):
            print("⚠️ File đã tồn tại.")
        else:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerow(["id", "answer", "question", "desc", "ref"])
            log_action(act, path)
            print(f"✅ Đã tạo {name}.csv")

    def _delete_file(self, act):
        """🗑️ Xoá file CSV đã chọn"""
        if (path := self._choose_file("xoá")) and input(f"❓ Xoá {os.path.basename(path)} (y/n)\n> ").lower() == "y":
            os.remove(path); log_action(act, path)
            print("🗑️ Đã xoá file.")

    def _rename_file(self, act):
        """✏️ Đổi tên file CSV"""
        while True:
            if path := self._choose_file("đổi tên"):
                new = input("✏️ Nhập tên mới (hoặc nhập exit() để thoát)\n> ").strip()
                log_action(f"CHANGE_Name")
                if new.lower() == "exit()": break
                if new:
                    newpath = os.path.join(self.qdir, f"{new}.csv")
                    os.rename(path, newpath)
                    log_action(act, f"{path} -> {newpath}")
                    print("✅ Đã đổi tên file.")

    def menu(self):
        """Menu chính chương trình"""
        actions = {
            "1": (self.play_file, f"{BRIGHT_GREEN}🎯 Chơi theo bộ{RESET}"),
            "2": (self.play_all, f"{BRIGHT_GREEN}🌍 Chơi tất cả{RESET}"),
            "3": (self.manage_questions, f"{BRIGHT_YELLOW}📋 Quản lý câu hỏi{RESET}"),
            "4": (self.manage_files, f"{BRIGHT_YELLOW}📂 Quản lý file{RESET}"),
            "0": (lambda: print(f"{BRIGHT_RED}👋 Tạm biệt!"), f"{BRIGHT_RED}🚪 Thoát{RESET}"),
        }
        while True:
            print(f"{BLUE}\n===== 📚 FLASHCARD QUIZ GAME ====={RESET}")
            for k, (_, label) in actions.items():
                print(f" {k}) {label}")
            ch = input("\n👉 Nhập lựa chọn: ").strip()
            if ch in actions:
                self.clearsrc()
                log_action("MENU", f"{ch}:{actions[ch][1]}")
                if ch == "0": return
                actions[ch][0]()
            else:
                self.clearsrc()
                print("⚠️ Sai lựa chọn.")

# Entry point
if __name__ == "__main__":
    QuizGame().menu()
