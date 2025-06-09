import os
import sys
import time

try:
    from .adb_wrapper import execute_adb_command, log_message
except ImportError:
    print("Warning: adb_wrapper not found. Using basic print for logging.")
    def log_message(level, message, component=None, color=None):
        print(f"[{level.upper()}] {f'[{component}] ' if component else ''}{message}")
    def execute_adb_command(command, device_id=None):
        # Dummy implementation for standalone execution without the full structure
        import subprocess, shlex
        try:
            full_cmd = ["adb"] + shlex.split(command)
            result = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
            return True, result.stdout.strip()
        except Exception as e:
            return False, str(e)


def install_apk(apk_path: str, device_id: str = None, retries: int = 2, delay_sec: int = 3) -> bool:
    """
    Installs an APK file on the target device, with retries.

    Args:
        apk_path (str): Path to the .apk file.
        device_id (str, optional): Specific device to install on. Defaults to None.
        retries (int, optional): Number of installation attempts. Defaults to 2.
        delay_sec (int, optional): Delay between retries. Defaults to 3.

    Returns:
        bool: True if installation was successful, False otherwise.
    """
    if not os.path.exists(apk_path):
        log_message("ERROR", f"APK file not found at {apk_path}", component="AppInstaller", color="red")
        return False
        
    for attempt in range(retries):
        log_message("INFO", f"Installing APK: {os.path.basename(apk_path)} (Attempt {attempt + 1}/{retries})", component="AppInstaller", color="cyan")
        # Use '-r' to reinstall if it exists, '-t' to allow test packages
        success, output = execute_adb_command(f'install -r -t "{apk_path}"', device_id)
        
        if success and "Success" in output:
            log_message("SUCCESS", "APK installed successfully!", component="AppInstaller", color="green")
            return True
        else:
            log_message("WARNING", f"Install attempt failed. ADB output: {output}", component="AppInstaller", color="yellow")
            if attempt < retries - 1:
                log_message("INFO", f"Retrying in {delay_sec} seconds...", component="AppInstaller")
                time.sleep(delay_sec)
    
    log_message("ERROR", "Failed to install APK after all retries.", component="AppInstaller", color="red")
    return False

def is_package_present(package_name: str, device_id: str = None) -> bool:
    """
    Checks if a package is installed on the device.

    Args:
        package_name (str): The package name to check (e.g., "com.example.app").
        device_id (str, optional): Specific device to check. Defaults to None.

    Returns:
        bool: True if the package is found, False otherwise.
    """
    log_message("INFO", f"Verifying presence of package: {package_name}", component="AppInstaller")
    success, output = execute_adb_command(f"shell pm list packages {package_name}", device_id)
    
    if success and f"package:{package_name}" in output:
        log_message("SUCCESS", f"Package '{package_name}' is installed.", component="AppInstaller", color="green")
        return True
    else:
        log_message("INFO", f"Package '{package_name}' not found on device.", component="AppInstaller")
        return False


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python tools/app_installer.py <path_to_apk>")
        sys.exit(1)
    
    install_apk(sys.argv[1])