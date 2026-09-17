' Uruchamia DocShield bez widocznego okienka konsoli - tylko interfejs
' aplikacji. Bledy startowe trafiaja do %USERPROFILE%\.anonimizer\
' ostatni_blad.log (patrz src/main.py) zamiast znikac bez sladu, tak
' jak zniklyby przy zwyklym uruchomieniu przez pythonw.exe bez konsoli.
'
' Do debugowania (chcesz widziec konsole na biezaco) uzyj uruchom.bat.

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

pythonwPath = scriptDir & "\.venv\Scripts\pythonw.exe"
mainPath = scriptDir & "\src\main.py"

objShell.CurrentDirectory = scriptDir
objShell.Run """" & pythonwPath & """ """ & mainPath & """", 0, False
