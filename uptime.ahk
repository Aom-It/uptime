#Requires AutoHotkey v2.0
#SingleInstance Force

W := 300, H := 116
ini := A_AppData "\uptime_widget.ini"

; ---------- หน้าต่าง (ไม่มีกรอบ ลอยบนสุด ไม่โชว์ในแถบงาน) ----------
g := Gui("-Caption +AlwaysOnTop +ToolWindow", "เปิดคอมมานานแค่ไหน")
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
clock := g.AddText("x0 y46 w" W " h60 Center", "00:00:00")

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

; ---------- ลากย้ายด้วยเมาส์ และจำตำแหน่ง ----------
OnMessage(0x201, OnLButtonDown)
OnMessage(0x232, (*) => SavePos())

OnLButtonDown(wParam, lParam, msg, hwnd) {
    if (hwnd = g.Hwnd)
        PostMessage(0xA1, 2, , , g)
}

SavePos() {
    g.GetPos(&sx, &sy)
    IniWrite(sx, ini, "pos", "x")
    IniWrite(sy, ini, "pos", "y")
}

; ---------- คลิกขวา: เมนู ----------
m := Menu()
m.Add("ลอยบนสุดเสมอ", ToggleTop)
m.Check("ลอยบนสุดเสมอ")
m.Add("ปิดโปรแกรม", (*) => ExitApp())
g.OnEvent("ContextMenu", (*) => m.Show())

ToggleTop(name, *) {
    WinSetAlwaysOnTop(-1, g)
    m.ToggleCheck(name)
}

; ---------- ตัวจับเวลา ----------
Tick() {
    s := DllCall("GetTickCount64", "Int64") // 1000
    d := s // 86400
    clock.Text := Format("{:02d}:{:02d}:{:02d}", Mod(s // 3600, 24), Mod(s // 60, 60), Mod(s, 60))
    daysTxt.Text := d ? d . " วัน" : ""
}

Tick()
SetTimer(Tick, 1000)
