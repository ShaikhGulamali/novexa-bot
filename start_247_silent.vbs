' GULAMALI ULTIMATE BOT - hidden launcher
' Starts run_247_engine.bat with no console window.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir
' Wait on the engine so the scheduled task stays Running and Task Scheduler
' can revive it if the keep-alive loop itself is ever killed.
sh.Run "cmd.exe /c """ & dir & "\run_247_engine.bat""", 0, True
