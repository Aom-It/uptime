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

W, H = 300, 116
BG, EDGE, TRANS = "#1e1e2e", "#313244", "#010203"
TEXT, MUTED, GREEN, BLUE, RED = "#a6adc8", "#6c7086", "#a6e3a1", "#89b4fa", "#f38ba8"
POS_FILE = os.path.join(os.path.expanduser("~"), ".uptime_widget_pos")


def get_uptime_seconds():
    if sys.platform.startswith("win"):
        import ctypes
        k = ctypes.windll.kernel32
        k.GetTickCount64.restype = ctypes.c_ulonglong
        return k.GetTickCount64() / 1000
    if sys.platform.startswith("linux"):
        with open("/proc/uptime") as f:
            return float(f.read().split()[0])
    if sys.platform == "darwin":
        import re
        import subprocess
        out = subprocess.check_output(["sysctl", "-n", "kern.boottime"]).decode()
        return time.time() - int(re.search(r"sec = (\d+)", out).group(1))
    raise RuntimeError("ระบบปฏิบัติการนี้ยังไม่รองรับ")


# ให้ตัวหนังสือคมบนจอที่ตั้งสเกล 125% / 150%
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

root = tk.Tk()
root.title("เปิดคอมมานานแค่ไหน")
root.overrideredirect(True)          # ไม่มีกรอบ / แถบหัวหน้าต่าง
root.attributes("-topmost", True)    # ลอยบนสุด
root.configure(bg=TRANS)
try:
    root.attributes("-transparentcolor", TRANS)  # ทำมุมโค้งโปร่งใส (Windows)
except tk.TclError:
    pass

scale = root.winfo_fpixels("1i") / 96


def S(v):
    return int(v * scale)


w, h = S(W), S(H)
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
x, y = sw - w - S(24), S(24)
try:
    with open(POS_FILE) as f:
        px, py = map(int, f.read().split(","))
    if 0 <= px <= sw - w and 0 <= py <= sh - h:
        x, y = px, py
except Exception:
    pass
root.geometry(f"{w}x{h}+{x}+{y}")

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
clock = c.create_text(w // 2, S(70), text="00:00:00", fill=GREEN, font=("Consolas", 34, "bold"))

job = {"id": None}


def close(*_):
    # ปิดแบบปลอดภัย: ยกเลิกตัวจับเวลา แล้วค่อยออกจาก mainloop (ไม่ destroy ตอนยังอยู่ใน event)
    if job["id"]:
        try:
            root.after_cancel(job["id"])
        except Exception:
            pass
    root.quit()


c.tag_bind(close_txt, "<Enter>", lambda e: c.itemconfig(close_txt, fill=RED))
c.tag_bind(close_txt, "<Leave>", lambda e: c.itemconfig(close_txt, fill=MUTED))
c.tag_bind(close_txt, "<Button-1>", close)

# ลากย้ายตำแหน่งได้ด้วยเมาส์
drag = {"x": 0, "y": 0}


def drag_start(e):
    drag["x"], drag["y"] = e.x_root - root.winfo_x(), e.y_root - root.winfo_y()


def drag_move(e):
    root.geometry(f"+{e.x_root - drag['x']}+{e.y_root - drag['y']}")


def drag_end(e):
    try:
        with open(POS_FILE, "w") as f:
            f.write(f"{root.winfo_x()},{root.winfo_y()}")
    except Exception:
        pass


c.bind("<ButtonPress-1>", drag_start)
c.bind("<B1-Motion>", drag_move)
c.bind("<ButtonRelease-1>", drag_end)

# คลิกขวา: เมนูเล็กๆ
top_var = tk.BooleanVar(value=True)
menu = tk.Menu(root, tearoff=0)
menu.add_checkbutton(
    label="ลอยบนสุดเสมอ", variable=top_var,
    command=lambda: root.attributes("-topmost", top_var.get()),
)
menu.add_separator()
menu.add_command(label="ปิดโปรแกรม", command=close)
c.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))


def tick():
    total = int(get_uptime_seconds())
    d, rem = divmod(total, 86400)
    hh, rem = divmod(rem, 3600)
    mm, ss = divmod(rem, 60)
    c.itemconfig(clock, text=f"{hh:02d}:{mm:02d}:{ss:02d}")
    c.itemconfig(days_txt, text=f"{d} วัน" if d else "")
    job["id"] = root.after(1000, tick)


tick()
root.mainloop()
os._exit(0)  # ออกทันที ข้ามขั้นตอนเก็บกวาดของ tkinter ที่ทำให้เกิด Fatal Error
