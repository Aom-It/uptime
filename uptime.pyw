import json
import os
import sys
import time

# ถ้าถูกรันด้วย python.exe (มีหน้าต่าง cmd) ให้เปิดตัวเองใหม่แบบไม่มี cmd แล้วปิดอันเดิม
if (
    sys.platform.startswith("win")
    and os.path.basename(sys.executable).lower() == "python.exe"
    and "--detached" not in sys.argv
):
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if os.path.exists(pyw):
        import subprocess
        subprocess.Popen(
            [pyw, os.path.abspath(__file__), "--detached"],
            creationflags=0x00000008 | 0x00000200,  # DETACHED_PROCESS | NEW_PROCESS_GROUP
            close_fds=True,
        )
        sys.exit()

import tkinter as tk

# ---------- ตั้งค่า (แก้ตรงนี้ได้) ----------
OPACITY = 0.85      # ความทึบ 0.0 - 1.0 (น้อย = โปร่งมาก)
PEEK_MS = 4000      # กด Ctrl+Alt+U แล้วโชว์กี่มิลลิวินาที

W, H = 300, 156
BG, EDGE, TRANS = "#1e1e2e", "#313244", "#010203"
TEXT, MUTED, BODY = "#a6adc8", "#6c7086", "#cdd6f4"
GREEN, BLUE, RED = "#a6e3a1", "#89b4fa", "#f38ba8"
COLORS = ["#a6e3a1", "#f9e2af", "#fab387", "#f38ba8"]   # เขียว > เหลือง > ส้ม > แดง
DATA_FILE = os.path.join(os.path.expanduser("~"), ".uptime_widget.json")

IS_WIN = sys.platform.startswith("win")

# ---------- Windows API ----------
if IS_WIN:
    import ctypes
    from ctypes import wintypes

    u32 = ctypes.windll.user32
    k32 = ctypes.windll.kernel32

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    u32.GetForegroundWindow.restype = wintypes.HWND
    u32.GetParent.argtypes = [wintypes.HWND]
    u32.GetParent.restype = wintypes.HWND
    u32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    u32.FindWindowW.restype = wintypes.HWND
    u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    u32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    u32.GetWindowLongW.restype = ctypes.c_long
    u32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    u32.SetWindowLongW.restype = ctypes.c_long
    u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    u32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    u32.MonitorFromWindow.restype = wintypes.HANDLE
    u32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    u32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    u32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, wintypes.UINT]
    u32.SetForegroundWindow.argtypes = [wintypes.HWND]
    u32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    u32.GetAsyncKeyState.restype = ctypes.c_short
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    k32.GetSystemTimeAsFileTime.argtypes = [ctypes.POINTER(wintypes.FILETIME)]
    k32.GetTickCount64.restype = ctypes.c_ulonglong

    try:  # ให้ตัวหนังสือคมบนจอที่ตั้งสเกล 125% / 150%
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def ft_to_int(ft):
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


# ---------- เวลาที่เปิดคอม ----------
def boot_seconds():
    """เวลาตั้งแต่บูตเคอร์เนล (Windows Fast Startup จะไม่รีเซ็ตค่านี้ตอน Shutdown)"""
    if IS_WIN:
        return k32.GetTickCount64() / 1000
    if sys.platform.startswith("linux"):
        with open("/proc/uptime") as f:
            return float(f.read().split()[0])
    if sys.platform == "darwin":
        import re
        import subprocess
        out = subprocess.check_output(["sysctl", "-n", "kern.boottime"]).decode()
        return time.time() - int(re.search(r"sec = (\d+)", out).group(1))
    raise RuntimeError("ระบบปฏิบัติการนี้ยังไม่รองรับ")


session_start = 0


def get_session_start():
    """เวลาที่ explorer.exe (แถบงาน) เริ่มทำงาน = เริ่มเซสชันนี้
    Shutdown แบบ Fast Startup จะล็อกเอาต์ผู้ใช้ จึงเริ่มนับใหม่ทุกครั้งที่เปิดคอม"""
    hwnd = u32.FindWindowW("Shell_TrayWnd", None)
    if not hwnd:
        return 0
    pid = wintypes.DWORD(0)
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return 0
    h = k32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return 0
    try:
        created, ex, kt, ut = (wintypes.FILETIME() for _ in range(4))
        ok = k32.GetProcessTimes(h, ctypes.byref(created), ctypes.byref(ex),
                                 ctypes.byref(kt), ctypes.byref(ut))
    finally:
        k32.CloseHandle(h)
    return ft_to_int(created) if ok else 0


def elapsed_seconds():
    global session_start
    boot = boot_seconds()
    if not IS_WIN:
        return int(boot)
    if not session_start:
        session_start = get_session_start()
    if not session_start:
        return int(boot)
    now = wintypes.FILETIME()
    k32.GetSystemTimeAsFileTime(ctypes.byref(now))
    return int(min(boot, max(0, (ft_to_int(now) - session_start) / 1e7)))


def format_dur(sec):
    d, h, m = sec // 86400, sec // 3600 % 24, sec // 60 % 60
    if d:
        return f"{d} วัน {h} ชม."
    if h:
        return f"{h} ชม. {m} นาที"
    return f"{m} นาที"


def message_for(hrs):
    if hrs >= 8:
        return "เกิน 8 ชั่วโมงแล้ว! ไปพักผ่อนบ้างนะ"
    if hrs >= 4:
        return "ทำงานมานานมาก พักสายตา 5 นาทีนะ"
    if hrs >= 2:
        return "นั่งมาสักพักแล้ว ลุกยืดเส้นหน่อยนะ"
    if hrs >= 1:
        return "ครบ 1 ชั่วโมงแล้ว ดื่มน้ำสักแก้วไหม"
    return "เพิ่งเริ่มต้น สู้ๆ นะ"


# ---------- ข้อมูลที่จำไว้ (ตำแหน่ง + สถิติ) ----------
def load_data():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"x": root.winfo_x(), "y": root.winfo_y(), "record": record}, f)
    except Exception:
        pass


data = load_data()
record = int(data.get("record", 0))

# ---------- หน้าต่าง ----------
root = tk.Tk()
root.title("เปิดคอมมานานแค่ไหน")
root.overrideredirect(True)          # ไม่มีกรอบ / แถบหัวหน้าต่าง
root.configure(bg=TRANS)
try:
    root.attributes("-transparentcolor", TRANS)  # มุมโค้งโปร่งใส (Windows)
    root.attributes("-alpha", OPACITY)
except tk.TclError:
    pass

scale = root.winfo_fpixels("1i") / 96


def S(v):
    return int(v * scale)


w, h = S(W), S(H)
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
x, y = sw - w - S(24), S(24)
try:
    px, py = int(data["x"]), int(data["y"])
    if 0 <= px <= sw - w and 0 <= py <= sh - h:
        x, y = px, py
except Exception:
    pass
root.geometry(f"{w}x{h}+{x}+{y}")
root.update_idletasks()

my_hwnd = None
if IS_WIN:
    my_hwnd = u32.GetParent(root.winfo_id())
    # WS_EX_NOACTIVATE (ไม่แย่งโฟกัสเกม) + WS_EX_TOOLWINDOW (ไม่โชว์ในแถบงาน)
    ex = u32.GetWindowLongW(my_hwnd, -20)
    u32.SetWindowLongW(my_hwnd, -20, ex | 0x08000000 | 0x80)

c = tk.Canvas(root, width=w, height=h, bg=TRANS, highlightthickness=0, bd=0)
c.pack()


def rounded(x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1, x1 + r, y1]
    return c.create_polygon(pts, smooth=True, **kw)


rounded(S(2), S(2), w - S(2), h - S(2), S(18), fill=BG, outline=EDGE, width=1)
c.create_oval(S(18), S(22), S(26), S(30), fill=GREEN, outline="")
c.create_text(S(34), S(26), text="เปิดคอมมาแล้ว", anchor="w", fill=TEXT, font=("Segoe UI", 10))
days_txt = c.create_text(w - S(44), S(26), text="", anchor="e", fill=BLUE, font=("Segoe UI", 10, "bold"))
close_txt = c.create_text(w - S(20), S(26), text="✕", fill=MUTED, font=("Segoe UI", 11))
clock = c.create_text(w // 2, S(73), text="00:00:00", fill=GREEN, font=("Consolas", 30, "bold"))
msg_txt = c.create_text(w // 2, S(115), text="", fill=BODY, font=("Segoe UI", 9))
rec_txt = c.create_text(w // 2, S(137), text="", fill=MUTED, font=("Segoe UI", 8))

# ---------- สถานะ ----------
user_hidden = False
peeking = False
peek_job = None
shown = True
job = {"id": None}

hide_var = tk.BooleanVar(value=False)
top_var = tk.BooleanVar(value=False)     # ค่าเริ่มต้น: ไม่ลอยบนสุด
click_var = tk.BooleanVar(value=False)


# ---------- แสดง / ซ่อน / ชั้นของหน้าต่าง ----------
def apply_topmost(on):
    if IS_WIN:
        # SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
        u32.SetWindowPos(my_hwnd, -1 if on else -2, 0, 0, 0, 0, 0x0013)
    else:
        root.attributes("-topmost", bool(on))


def set_shown(v):
    global shown
    if v == shown:
        return
    shown = v
    if IS_WIN:
        u32.ShowWindow(my_hwnd, 4 if v else 0)   # SW_SHOWNOACTIVATE / SW_HIDE
    elif v:
        root.deiconify()
    else:
        root.withdraw()


def is_fullscreen_active():
    """มีโปรแกรมเต็มจอ (เกม / วิดีโอ) อยู่หน้าสุดไหม"""
    if not IS_WIN:
        return False
    hwnd = u32.GetForegroundWindow()
    if not hwnd or hwnd == my_hwnd:
        return False
    buf = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, buf, 256)
    if buf.value in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
        return False
    if u32.GetWindowLongW(hwnd, -16) & 0xC00000:   # มีแถบหัวหน้าต่าง = หน้าต่างปกติ
        return False
    r = wintypes.RECT()
    if not u32.GetWindowRect(hwnd, ctypes.byref(r)):
        return False
    mon = u32.MonitorFromWindow(hwnd, 2)           # MONITOR_DEFAULTTONEAREST
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    if not u32.GetMonitorInfoW(mon, ctypes.byref(mi)):
        return False
    m = mi.rcMonitor
    return r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom


def update_visibility():
    set_shown(peeking or (not user_hidden and not is_fullscreen_active()))


def end_peek():
    global peeking, peek_job
    peeking = False
    peek_job = None
    apply_topmost(top_var.get())
    update_visibility()


def peek(_=None):
    """แวบขึ้นมาดูเวลาบนสุดชั่วคราว"""
    global peeking, peek_job
    peeking = True
    apply_topmost(True)
    update_visibility()
    if peek_job:
        root.after_cancel(peek_job)
    peek_job = root.after(PEEK_MS, end_peek)


def on_hide_menu():
    global user_hidden
    user_hidden = hide_var.get()
    update_visibility()


def toggle_hide(_=None):
    hide_var.set(not hide_var.get())
    on_hide_menu()


def apply_click_through():
    if not IS_WIN:
        return
    ex = u32.GetWindowLongW(my_hwnd, -20)
    ex = (ex | 0x20) if click_var.get() else (ex & ~0x20)   # WS_EX_TRANSPARENT
    u32.SetWindowLongW(my_hwnd, -20, ex)


def close(*_):
    # ปิดแบบปลอดภัย: ยกเลิกตัวจับเวลา แล้วค่อยออกจาก mainloop
    for jid in (job["id"], peek_job):
        if jid:
            try:
                root.after_cancel(jid)
            except Exception:
                pass
    root.quit()


# ---------- ปุ่ม ✕ / ลากย้าย / เมนูคลิกขวา ----------
c.tag_bind(close_txt, "<Enter>", lambda e: c.itemconfig(close_txt, fill=RED))
c.tag_bind(close_txt, "<Leave>", lambda e: c.itemconfig(close_txt, fill=MUTED))
c.tag_bind(close_txt, "<Button-1>", close)

drag = {"x": 0, "y": 0}


def drag_start(e):
    drag["x"], drag["y"] = e.x_root - root.winfo_x(), e.y_root - root.winfo_y()


def drag_move(e):
    root.geometry(f"+{e.x_root - drag['x']}+{e.y_root - drag['y']}")


c.bind("<ButtonPress-1>", drag_start)
c.bind("<B1-Motion>", drag_move)
c.bind("<ButtonRelease-1>", lambda e: save_data())

menu = tk.Menu(root, tearoff=0)
menu.add_command(label="ดูเวลา  (Ctrl+Alt+U)", command=peek)
menu.add_checkbutton(label="ซ่อนตัวจับเวลา  (Ctrl+Alt+H)", variable=hide_var, command=on_hide_menu)
menu.add_checkbutton(label="ลอยบนสุดเสมอ", variable=top_var,
                     command=lambda: apply_topmost(top_var.get()))
menu.add_checkbutton(label="คลิกทะลุ (เมาส์ไม่โดนตัวจับเวลา)", variable=click_var,
                     command=apply_click_through)
menu.add_separator()
menu.add_command(label="ปิดโปรแกรม", command=close)


def popup(e):
    if IS_WIN:
        u32.SetForegroundWindow(my_hwnd)   # ให้เมนูปิดได้เมื่อคลิกที่อื่น
    try:
        menu.tk_popup(e.x_root, e.y_root)
    finally:
        menu.grab_release()


c.bind("<Button-3>", popup)

# ---------- ปุ่มลัด Ctrl+Alt+U (แวบดู) / Ctrl+Alt+H (ซ่อน-แสดง) ----------
hk_down = {"u": False, "h": False}


def poll_keys():
    if (u32.GetAsyncKeyState(0x11) & 0x8000) and (u32.GetAsyncKeyState(0x12) & 0x8000):
        for name, vk, fn in (("u", 0x55, peek), ("h", 0x48, toggle_hide)):
            down = bool(u32.GetAsyncKeyState(vk) & 0x8000)
            if down and not hk_down[name]:
                fn()
            hk_down[name] = down
    else:
        hk_down["u"] = hk_down["h"] = False
    root.after(100, poll_keys)


# ---------- ตัวจับเวลา ----------
def tick():
    global record
    s = elapsed_seconds()
    if s > record:
        record = s
    if s % 60 == 0:
        save_data()

    update_visibility()
    if shown:                         # ซ่อนอยู่ ไม่ต้องอัปเดตหน้าจอ
        d, hrs = s // 86400, s // 3600
        tier = 3 if hrs >= 8 else 2 if hrs >= 4 else 1 if hrs >= 2 else 0
        c.itemconfig(clock, text=f"{hrs % 24:02d}:{s // 60 % 60:02d}:{s % 60:02d}", fill=COLORS[tier])
        c.itemconfig(days_txt, text=f"{d} วัน" if d else "")
        c.itemconfig(msg_txt, text=message_for(hrs))
        c.itemconfig(rec_txt, text="★ กำลังทำสถิติใหม่!" if s >= record
                     else f"สถิติเปิดนานสุด: {format_dur(record)}")
    job["id"] = root.after(1000, tick)


tick()
if IS_WIN:
    poll_keys()
root.mainloop()
save_data()
os._exit(0)  # ออกทันที ข้ามขั้นตอนเก็บกวาดของ tkinter ที่ทำให้เกิด Fatal Error
