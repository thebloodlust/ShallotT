import os
import sys
import subprocess
import shutil
import argparse

def run_command(command):
    print(f"Executing: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        sys.exit(1)

def build_exe(onefile=False, use_upx=False, console=False):
    print("=== ShallotT - Auto Executable Builder ===")

    # 1. Install PyInstaller if not present
    print("Checking dependencies...")
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        run_command(f'"{sys.executable}" -m pip install pyinstaller')

    # 2. Clean previous builds
    for folder in ["dist", "build"]:
        if os.path.exists(folder):
            print(f"Cleaning previous {folder} folder...")
            shutil.rmtree(folder)

    # 3. Build the PyInstaller command
    mode_flag = "--onefile" if onefile else "--onedir"
    window_flag = "--noconsole" if not console else "--console"
    add_data_param = "src;src" if os.name == 'nt' else "src:src"

    cmd = (
        f'"{sys.executable}" -m PyInstaller '
        f'{mode_flag} {window_flag} '
        f'--add-data "{add_data_param}" '
        f'--name "ShallotT" '
    )

    # Disable UPX by default — major cause of antivirus false positives
    if not use_upx:
        cmd += '--noupx '
    else:
        print("⚠️  UPX compression enabled — may trigger antivirus false positives.")

    # Add Windows version metadata (reduces false positives)
    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version_info.txt")
    if os.name == 'nt' and os.path.exists(version_file):
        cmd += f'--version-file "{version_file}" '
        print("Adding Windows version metadata (CompanyName, FileDescription, etc.).")

    cmd += 'main.py'

    print(f"Mode: {'Single-file (.exe)' if onefile else 'One-folder (AV-friendly)'}")
    print(f"UPX:  {'Enabled' if use_upx else 'Disabled (recommended)'}")
    print(f"Console: {'Visible' if console else 'Hidden'}")
    run_command(cmd)

    # 4. Success
    if onefile:
        exe_path = os.path.join("dist", "ShallotT.exe" if os.name == 'nt' else "ShallotT")
    else:
        exe_path = os.path.join("dist", "ShallotT")

    if os.path.exists(exe_path):
        print("\n" + "=" * 60)
        print("⚡ COMPILATION SUCCESSFUL! ⚡")
        print(f"Output: {os.path.abspath(exe_path)}")
        if not onefile:
            exe_file = os.path.join(exe_path, "ShallotT.exe" if os.name == 'nt' else "ShallotT")
            if os.path.exists(exe_file):
                print(f"Executable: {os.path.abspath(exe_file)}")
        print("=" * 60)

        if onefile:
            print("\n⚠️  Single-file mode may trigger antivirus false positives.")
            print("   If your AV flags it, use the default --onedir mode instead:")
            print("     python build_exe.py")
            print("   You can also submit the file for whitelisting:")
            print("   https://www.microsoft.com/en-us/wdsi/filesubmission")

        if not use_upx:
            print("\n✅ UPX compression DISABLED — much lower risk of false positives.")

        if os.name == 'nt':
            print("\n💡 To further reduce false positives on Windows:")
            print("   1. Code-sign the executable with an Extended Validation certificate")
            print("   2. Submit the signed .exe to Microsoft Defender portal:")
            print("      https://www.microsoft.com/en-us/wdsi/filesubmission")
            print("   3. Submit to other AV vendors (Kaspersky, Bitdefender, etc.)")
            print("   4. Distribute as a .zip of the one-folder output")
    else:
        print("Executable could not be found. Check compilation outputs.")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Build ShallotT standalone executable (Windows / Linux)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_exe.py                  # One-folder mode (AV-friendly default)
  python build_exe.py --onefile        # Single .exe file
  python build_exe.py --console        # Show console for debugging
  python build_exe.py --onefile --upx  # Single file + UPX (max AV risk)
        """)
    parser.add_argument('--onefile', action='store_true',
                        help='Build a single-file .exe (may trigger AV false positives). '
                             'Default: one-folder mode.')
    parser.add_argument('--upx', action='store_true',
                        help='Enable UPX compression (may trigger AV false positives). '
                             'Default: disabled.')
    parser.add_argument('--console', action='store_true',
                        help='Show console window (useful for debugging).')
    args = parser.parse_args()

    build_exe(onefile=args.onefile, use_upx=args.upx, console=args.console)
