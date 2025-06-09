import subprocess
import os
import sys
from typing import Tuple, Optional

try:
    from .adb_wrapper import log_message
except ImportError:
    print("Warning: adb_wrapper not found. Using basic print for logging.")
    def log_message(level, message, component=None, color=None):
        print(f"[{level.upper()}] {f'[{component}] ' if component else ''}{message}")

def _find_aapt_path() -> Optional[str]:
    """
    Tries to find the 'aapt' executable in common Android SDK locations.

    Returns:
        Optional[str]: The path to 'aapt' if found, otherwise None.
    """
    sdk_root = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    sdk_locations = [
        os.path.expanduser("~/Android/Sdk/build-tools"),
        os.path.expanduser("~/AppData/Local/Android/Sdk/build-tools"),
        "C:/Users/Administrator/AppData/Local/Android/Sdk/build-tools"
    ]
    if sdk_root:
        sdk_locations.insert(0, os.path.join(sdk_root, "build-tools"))

    for build_tools_path in sdk_locations:
        if not os.path.isdir(build_tools_path):
            continue
        
        versions = sorted([d for d in os.listdir(build_tools_path) if os.path.isdir(os.path.join(build_tools_path, d))], reverse=True)
        for version in versions:
            aapt_path = os.path.join(build_tools_path, version, "aapt.exe" if os.name == 'nt' else "aapt")
            if os.path.exists(aapt_path):
                log_message("DEBUG", f"Found aapt at: {aapt_path}", component="ApkAnalyzer")
                return aapt_path
    
    log_message("WARNING", "aapt tool not found in common SDK locations.", component="ApkAnalyzer", color="yellow")
    return None

def get_apk_info(apk_path: str) -> Optional[Tuple[str, str]]:
    """
    Extracts package name and application label from an APK file using aapt.

    Args:
        apk_path (str): The full path to the APK file.

    Returns:
        Optional[Tuple[str, str]]: A tuple of (package_name, app_name), or None on failure.
    """
    if not os.path.exists(apk_path):
        log_message("ERROR", f"APK file not found: {apk_path}", component="ApkAnalyzer", color="red")
        return None

    aapt_path = _find_aapt_path()
    if not aapt_path:
        log_message("ERROR", "Could not find aapt. Please ensure the Android SDK build-tools are installed and ANDROID_HOME is set.", component="ApkAnalyzer", color="red")
        return None

    try:
        command = [aapt_path, "dump", "badging", apk_path]
        result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='ignore', check=True)
        
        package_name, app_name = None, None
        for line in result.stdout.splitlines():
            if line.startswith("package: name="):
                package_name = line.split("'")[1]
            elif line.startswith("application-label:"):
                app_name = line.split("'")[1]
        
        if package_name and app_name:
            return package_name, app_name
        else:
            log_message("ERROR", "Could not parse package name or app name from aapt output.", component="ApkAnalyzer", color="red")
            return None

    except subprocess.CalledProcessError as e:
        log_message("ERROR", f"aapt command failed. Error: {e.stderr}", component="ApkAnalyzer", color="red")
        return None
    except Exception as e:
        log_message("ERROR", f"An unexpected error occurred while analyzing APK: {e}", component="ApkAnalyzer", color="red")
        return None

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python tools/apk_analyzer.py <path_to_apk>")
        sys.exit(1)
    
    info = get_apk_info(sys.argv[1])
    if info:
        log_message("SUCCESS", f"APK Info: Package='{info[0]}', App='{info[1]}'", component="ApkAnalyzer", color="green")