Dim oShell, oFso, sDir, sCmd
Set oFso   = CreateObject("Scripting.FileSystemObject")
Set oShell = CreateObject("WScript.Shell")
sDir = oFso.GetParentFolderName(WScript.ScriptFullName)

If oFso.FileExists(sDir & "\venv\Scripts\pythonw.exe") Then
    sCmd = """" & sDir & "\venv\Scripts\pythonw.exe"" """ & sDir & "\launch.py"""
Else
    sCmd = "pythonw """ & sDir & "\launch.py"""
End If

oShell.Run sCmd, 0, False
Set oShell = Nothing
Set oFso   = Nothing
