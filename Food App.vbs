Set oShell = CreateObject("Wscript.Shell")
Dim strPath
strPath = "C:\Users\suhaimi.abdullah\Desktop\Food\Food Order.bat"
oShell.Run """" & strPath & """", 0, True