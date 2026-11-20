#Requires AutoHotkey v2.0
#SingleInstance Force

; ---------- ตั้งค่า (แก้ตรงนี้ได้) ----------
OPACITY := 215          ; ความทึบ 0-255 (ยิ่งน้อยยิ่งโปร่ง)
PEEK_MS := 4000         ; กด Ctrl+Alt+U แล้วโชว์กี่มิลลิวินาที
W := 300, H := 156
ini := A_AppData "\uptime_widget.ini"

record := Integer(IniRead(ini, "stats", "record", "0"))   ; สถิติเปิดนานสุด (วินาที)
sessionStart := 0                                          ; เวลาเริ่มเซสชัน (FILETIME)
lastTier := -1
colors := ["A6E3A1", "F9E2AF", "FAB387", "F38BA8"]         ; เขียว > เหลือง > ส้ม > แดง

userHidden := false     ; ผู้ใช้สั่งซ่อน
alwaysTop := false      ; ค่าเริ่มต้น: ไม่ลอยบนสุด (อยู่ชั้นเดียวกับหน้าต่างทั่วไป)
peeking := false           ; กำลังโชว์ชั่วคราว
shown := false

nPeek := "ดูเวลา (Ctrl+Alt+U)"
nHide := "ซ่อนตัวจับเวลา"
nTop := "ลอยบนสุดเสมอ"
nClick := "คลิกทะลุ (เมาส์ไม่โดนตัวจับเวลา)"

; ---------- หน้าต่าง ----------
; +E0x08000000 = ไม่แย่งโฟกัส (คลิกที่ตัวจับเวลาแล้วเกมไม่หลุดโฟกัส)
g := Gui("-Caption +ToolWindow +E0x08000000", "เปิดคอมมานานแค่ไหน")
g.BackColor := "1E1E2E"
g.MarginX := 0
g.MarginY := 0

g.SetFont("s9 cA6E3A1", "Segoe UI")
g.AddText("x18 y21 w14 h20", "●")

g.SetFont("s10 cA6ADC8", "Segoe UI")
g.AddText("x34 y20 w140 h22", "เปิดคอมมาแล้ว")

g.SetFont("s10 bold c89B4FA", "Segoe UI")
daysTxt := g.AddText("x170 y20 w90 h22 Right", "")

g.SetFont("s11 norm c6C7086", "Segoe UI")
closeBtn := g.AddText("x266 y18 w26 h24 Center", "✕")
closeBtn.OnEvent("Click", (*) => ExitApp())

g.SetFont("s30 bold cA6E3A1", "Consolas")
clock := g.AddText("x0 y44 w" W " h58 Center", "00:00:00")

g.SetFont("s9 norm cCDD6F4", "Segoe UI")
msgTxt := g.AddText("x10 y104 w280 h22 Center", "")

g.SetFont("s8 c6C7086", "Segoe UI")
recTxt := g.AddText("x10 y128 w280 h18 Center", "")

; ---------- ตำแหน่งและมุมโค้ง ----------
g.Show("Hide w" W " h" H)
g.GetPos(, , &gw, &gh)

x := A_ScreenWidth - gw - 24
y := 24
try {
    px := Integer(IniRead(ini, "pos", "x"))
    py := Integer(IniRead(ini, "pos", "y"))
    if (px >= 0 && py >= 0 && px <= A_ScreenWidth - gw && py <= A_ScreenHeight - gh) {
        x := px
        y := py
    }
}

r := Round(18 * A_ScreenDPI / 96)
WinSetRegion("0-0 w" gw " h" gh " r" r "-" r, g)
WinMove(x, y, , , g)
g.Show("NA")
WinSetTransparent(OPACITY, g)
shown := true

; ---------- ลากย้ายด้วยเมาส์ และจำตำแหน่ง ----------
OnMessage(0x201, OnLButtonDown)
OnMessage(0x232, (*) => SavePos())
OnExit((*) => SaveRecord())

OnLButtonDown(wParam, lParam, msg, hwnd) {
    if (hwnd = g.Hwnd)
        PostMessage(0xA1, 2, , , g)
}

SavePos() {
    g.GetPos(&sx, &sy)
    IniWrite(sx, ini, "pos", "x")
    IniWrite(sy, ini, "pos", "y")
}

SaveRecord() {
    IniWrite(record, ini, "stats", "record")
}

; ---------- เมนู (คลิกขวาที่ตัวจับเวลา และที่ไอคอนถาดระบบ) ----------
BuildMenu(mm) {
    mm.Add(nPeek, Peek)
    mm.Add(nHide, ToggleHide)
    mm.Add(nTop, ToggleTop)
    mm.Add(nClick, ToggleClickThrough)
    mm.Add()
    mm.Add("ปิดโปรแกรม", (*) => ExitApp())
}

m := Menu()
BuildMenu(m)
A_TrayMenu.Delete()
BuildMenu(A_TrayMenu)
A_TrayMenu.Default := nPeek
A_TrayMenu.ClickCount := 1
A_IconTip := "เปิดคอมมานานแค่ไหน"

g.OnEvent("ContextMenu", (*) => m.Show())
Hotkey("^!u", Peek)

ToggleBoth(name) {
    m.ToggleCheck(name)
    A_TrayMenu.ToggleCheck(name)
}

ToggleHide(name, *) {
    global userHidden
    userHidden := !userHidden
    ToggleBoth(name)
    UpdateVisibility()
}

ToggleTop(name, *) {
    global alwaysTop
    alwaysTop := !alwaysTop
    WinSetAlwaysOnTop(alwaysTop ? 1 : 0, g)
    ToggleBoth(name)
}

ToggleClickThrough(name, *) {
    WinSetExStyle("^0x20", g)     ; WS_EX_TRANSPARENT
    ToggleBoth(name)
}

; ---------- แวบขึ้นมาดูเวลาชั่วคราว ----------
Peek(*) {
    global peeking
    peeking := true
    WinSetAlwaysOnTop(1, g)
    UpdateVisibility()
    SetTimer(EndPeek, -PEEK_MS)
}

EndPeek() {
    global peeking
    peeking := false
    WinSetAlwaysOnTop(alwaysTop ? 1 : 0, g)
    UpdateVisibility()
}

; ---------- ซ่อนอัตโนมัติเมื่อมีโปรแกรมเต็มจอ (เกม / วิดีโอเต็มจอ) ----------
IsFullscreenActive() {
    hwnd := WinExist("A")
    if (!hwnd || hwnd = g.Hwnd)
        return false
    try {
        cls := WinGetClass(hwnd)
        style := WinGetStyle(hwnd)
        WinGetPos(&wx, &wy, &ww, &wh, hwnd)
    } catch {
        return false
    }
    if (cls = "Progman" || cls = "WorkerW" || cls = "Shell_TrayWnd" || cls = "Shell_SecondaryTrayWnd")
        return false
    if (style & 0xC00000)          ; มีแถบหัวหน้าต่าง = หน้าต่างปกติ ไม่ใช่เต็มจอ
        return false
    Loop MonitorGetCount() {
        MonitorGet(A_Index, &ml, &mt, &mr, &mb)
        if (wx <= ml && wy <= mt && wx + ww >= mr && wy + wh >= mb)
            return true
    }
    return false
}

UpdateVisibility() {
    global shown
    want := peeking || (!userHidden && !IsFullscreenActive())
    if (want && !shown) {
        g.Show("NA")
        shown := true
    } else if (!want && shown) {
        g.Hide()
        shown := false
    }
}

; ---------- เวลาเริ่มเซสชัน ----------
; Windows ที่เปิด Fast Startup จะไม่รีเซ็ตเวลาเครื่องตอน Shutdown
; จึงใช้เวลาที่ explorer.exe (แถบงาน) เริ่มทำงานแทน ซึ่งจะเริ่มใหม่ทุกครั้งที่เปิดคอม
GetSessionStart() {
    pid := 0
    try pid := WinGetPID("ahk_class Shell_TrayWnd")
    if !pid
        return 0
    h := DllCall("OpenProcess", "UInt", 0x1000, "Int", 0, "UInt", pid, "Ptr")
    if !h
        return 0
    buf := Buffer(32, 0)
    ok := DllCall("GetProcessTimes", "Ptr", h, "Ptr", buf, "Ptr", buf.Ptr + 8, "Ptr", buf.Ptr + 16, "Ptr", buf.Ptr + 24)
    DllCall("CloseHandle", "Ptr", h)
    return ok ? NumGet(buf, 0, "Int64") : 0
}

ElapsedSeconds() {
    global sessionStart
    boot := DllCall("GetTickCount64", "Int64") // 1000
    if !sessionStart
        sessionStart := GetSessionStart()
    if !sessionStart
        return boot
    nowBuf := Buffer(8, 0)
    DllCall("GetSystemTimeAsFileTime", "Ptr", nowBuf)
    nowFT := NumGet(nowBuf, 0, "Int64")
    return Min(boot, Max(0, (nowFT - sessionStart) // 10000000))
}

FormatDur(sec) {
    d := sec // 86400
    h := Mod(sec // 3600, 24)
    m := Mod(sec // 60, 60)
    if d
        return d . " วัน " . h . " ชม."
    if h
        return h . " ชม. " . m . " นาที"
    return m . " นาที"
}

; ---------- ตัวจับเวลา ----------
Tick() {
    global record, lastTier
    s := ElapsedSeconds()
    d := s // 86400
    hrs := s // 3600

    if (Mod(s, 60) = 0 || s > record)
        record := Max(record, s)
    if (Mod(s, 60) = 0)
        SaveRecord()

    UpdateVisibility()
    if !shown                       ; ซ่อนอยู่ ไม่ต้องอัปเดตหน้าจอ
        return

    clock.Text := Format("{:02d}:{:02d}:{:02d}", Mod(hrs, 24), Mod(s // 60, 60), Mod(s, 60))
    daysTxt.Text := d ? d . " วัน" : ""

    tier := hrs >= 8 ? 3 : hrs >= 4 ? 2 : hrs >= 2 ? 1 : 0
    if (tier != lastTier) {
        lastTier := tier
        clock.SetFont("s30 bold c" . colors[tier + 1], "Consolas")
    }

    if (hrs >= 8)
        msg := "เกิน 8 ชั่วโมงแล้ว! ไปพักผ่อนบ้างนะ"
    else if (hrs >= 4)
        msg := "ทำงานมานานมาก พักสายตา 5 นาทีนะ"
    else if (hrs >= 2)
        msg := "นั่งมาสักพักแล้ว ลุกยืดเส้นหน่อยนะ"
    else if (hrs >= 1)
        msg := "ครบ 1 ชั่วโมงแล้ว ดื่มน้ำสักแก้วไหม"
    else
        msg := "เพิ่งเริ่มต้น สู้ๆ นะ"
    if (msgTxt.Text != msg)
        msgTxt.Text := msg

    rec := (s >= record) ? "★ กำลังทำสถิติใหม่!" : "สถิติเปิดนานสุด: " . FormatDur(record)
    if (recTxt.Text != rec)
        recTxt.Text := rec
}

Tick()
SetTimer(Tick, 1000)
