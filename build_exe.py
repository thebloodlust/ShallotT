import os
import sys
import subprocess
import shutil

def run_command(command):
    print(f"Executing: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        sys.exit(1)

def build_windows_exe():
    print("=== ShallotT - Auto Windows Executable (.exe) Builder ===")
    
    # 1. Install pyinstaller if not present
    print("Checking dependencies...")
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        run_command("pip install pyinstaller")

    # 2. Build directories structure
    dist_dir = "dist"
    build_dir = "build"
    for folder in [dist_dir, build_dir]:
        if os.path.exists(folder):
            print(f"Cleaning previous {folder} folder...")
            shutil.rmtree(folder)

    # 3. Create build command
    # --onefile: single executable
    # --noconsole: do not open terminal console (GUI only)
    # --name: Executable name
    # --add-data: Bundle the 'src' directory (including UI files, configs)
    # Under Windows, the path separator for --add-data is ';'
    add_data_param = "src;src" if os.name == 'nt' else "src:src"
    
    pyinstaller_cmd = (
        f"pyinstaller --onefile --windowed "
        f"--add-data \"{add_data_param}\" "
        f"--name \"ShallotT\" "
        f"main.py"
    )

    print(f"Starting PyInstaller compilation...")
    run_command(pyinstaller_cmd)
    
    # 4. Successful outcome
    exe_path = os.path.join("dist", "ShallotT.exe" if os.name == 'nt' else "ShallotT")
    if os.path.exists(exe_path):
        print("\n" + "="*50)
        print("⚡ COMPILATION SUCCESSFUL! ⚡")
        print(f"Your standalone executable is ready: {os.path.abspath(exe_path)}")
        print("You can distribute this executable to any Windows computer.")
        print("Note: To use the OCR Ctrl+F8 feature on another computer,")
        print("make sure Tesseract-OCR is installed on that machine.")
        print("="*50)
    else:
        print("Executable could not be found. Check compilation outputs.")

if __name__ == "__main__":
    build_windows_exe()
