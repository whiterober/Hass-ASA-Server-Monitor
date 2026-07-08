Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "A:\Steam\steam.exe", 0, False
WScript.Sleep 5000

' 多次尝试激活Steam窗口
For i = 1 To 5
    If WshShell.AppActivate("Steam") Then
        Exit For
    End If
    WScript.Sleep 2000
Next