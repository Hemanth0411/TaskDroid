import subprocess
import shlex
import sys
# Eagerly import log_utils to ensure it's available for other tools
try:
    from task_droid.shared.log_utils import log_message
except ImportError:
    # Fallback for when running tools standalone without the main package installed
    print("Warning: task_droid package not found. Using basic print for logging.")
    def log_message(level, message, component=None, color=None):
        print(f"[{level.upper()}] {f'[{component}] ' if component else ''}{message}")

def execute_adb_command(command: str, device_id: str = None) -> tuple[bool, str]:
    """
    Executes a given ADB command and returns the result.

    Args:
        command (str): The ADB command to execute (e.g., "shell ls").
        device_id (str, optional): The specific device to target. Defaults to None.

    Returns:
        tuple[bool, str]: A tuple containing a success flag (True/False)
                          and the command's stdout or stderr.
    """
    try:
        base_cmd = ["adb"]
        if device_id:
            base_cmd.extend(["-s", device_id])

        full_cmd = base_cmd + shlex.split(command)
        cmd_str_for_log = " ".join(full_cmd)
        log_message("DEBUG", f"Executing: {cmd_str_for_log}", component="AdbWrapper")

        result = subprocess.run(full_cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            error_output = result.stderr.strip() if result.stderr else "Unknown ADB error with non-zero exit code."
            log_message("WARNING", f"Command failed: {cmd_str_for_log}\nError: {error_output}", component="AdbWrapper", color="yellow")
            return False, error_output
        
        return True, result.stdout.strip()

    except FileNotFoundError:
        log_message("ERROR", "'adb' command not found. Make sure ADB is installed and in your system's PATH.", component="AdbWrapper", color="red")
        # Exit if adb is not found as it's a critical dependency
        sys.exit(1)
    except Exception as e:
        log_message("ERROR", f"An unexpected error occurred in execute_adb_command: {e}", component="AdbWrapper", color="red")
        return False, str(e)

def find_connected_devices() -> list[str]:
    """
    Lists all connected devices in the 'device' state.
    
    Returns:
        list[str]: A list of device serial numbers.
    """
    success, output = execute_adb_command("devices")
    if not success:
        return []

    devices = []
    lines = output.splitlines()
    for line in lines[1:]: # Skip the "List of devices attached" header
        if "\tdevice" in line:
            devices.append(line.split("\t")[0])
    
    return devices