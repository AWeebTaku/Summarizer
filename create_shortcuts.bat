@echo off
echo Creating desktop shortcuts for Text Summarizer...

REM Create GUI shortcut
powershell -Command "& {$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Text Summarizer GUI.lnk'); $Shortcut.TargetPath = 'python.exe'; $Shortcut.Arguments = '-c \"import text_summarizer.ui; text_summarizer.ui.main()\"'; $Shortcut.WorkingDirectory = '%USERPROFILE%'; $Shortcut.IconLocation = 'python.exe,0'; $Shortcut.Description = 'Text Summarizer GUI - Extractive text summarization tool'; $Shortcut.Save()}"

REM Create CLI shortcut
powershell -Command "& {$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Text Summarizer CLI.lnk'); $Shortcut.TargetPath = 'cmd.exe'; $Shortcut.Arguments = '/k text-summarizer-aweebtaku --help'; $Shortcut.WorkingDirectory = '%USERPROFILE%'; $Shortcut.IconLocation = 'cmd.exe,0'; $Shortcut.Description = 'Text Summarizer CLI - Command line interface'; $Shortcut.Save()}"

echo Desktop shortcuts created successfully!
echo.
echo Shortcuts created:
echo - Text Summarizer GUI.lnk (launches the graphical interface)
echo - Text Summarizer CLI.lnk (opens command prompt with help)
echo.
pause