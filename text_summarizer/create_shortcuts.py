#!/usr/bin/env python3
"""
Create desktop shortcuts for Text Summarizer on Windows.
Run this after installing the text-summarizer-aweebtaku package.
"""

import os
import sys
import platform

def create_shortcuts():
    """Create desktop shortcuts for Text Summarizer GUI and CLI."""

    if platform.system() != "Windows":
        print("This script is designed for Windows only.")
        print("On other platforms, use the console scripts:")
        print("  text-summarizer-gui    # Launch GUI")
        print("  text-summarizer-aweebtaku --help  # CLI help")
        return

    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        print("Required modules not found. Installing...")
        os.system(f"{sys.executable} -m pip install pywin32 winshell")
        try:
            import winshell
            from win32com.client import Dispatch
        except ImportError:
            print("Failed to install required modules.")
            print("Please install manually: pip install pywin32 winshell")
            return

    desktop = winshell.desktop()

    # Create GUI shortcut
    gui_shortcut_path = os.path.join(desktop, "Text Summarizer GUI.lnk")
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(gui_shortcut_path)
    shortcut.Targetpath = sys.executable
    shortcut.Arguments = '-c "import text_summarizer.ui; text_summarizer.ui.main()"'
    shortcut.WorkingDirectory = os.path.expanduser("~")
    shortcut.IconLocation = sys.executable + ",0"
    shortcut.Description = "Text Summarizer GUI - Extractive text summarization tool"
    shortcut.save()

    # Create CLI shortcut
    cli_shortcut_path = os.path.join(desktop, "Text Summarizer CLI.lnk")
    shortcut = shell.CreateShortCut(cli_shortcut_path)
    shortcut.Targetpath = "cmd.exe"
    shortcut.Arguments = '/k text-summarizer-aweebtaku --help'
    shortcut.WorkingDirectory = os.path.expanduser("~")
    shortcut.IconLocation = "cmd.exe,0"
    shortcut.Description = "Text Summarizer CLI - Command line interface"
    shortcut.save()

    print("Desktop shortcuts created successfully!")
    print(f"GUI Shortcut: {gui_shortcut_path}")
    print(f"CLI Shortcut: {cli_shortcut_path}")
    print("\nYou can now double-click these shortcuts to launch the application.")

if __name__ == "__main__":
    create_shortcuts()