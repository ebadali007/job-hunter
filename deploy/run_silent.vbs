Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\User\Downloads\job-hunter"
WshShell.Run "python -u run.py --port 8050 --no-browser", 0, False
Set WshShell = Nothing
