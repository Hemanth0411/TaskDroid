"""
Device operator for interacting with Android devices
"""
class DeviceOperator:
    def __init__(self):
        pass
import os
import subprocess
import shlex
import time
from typing import Tuple

from task_droid.config import settings
from task_droid.shared.log_utils import log_message

class DeviceOperator:
    """
    Handles all direct ADB interactions with a connected Android device.
    This class is stateful, holding the device ID and screen dimensions.
    """
    
    def __init__(self, device_id: str):
        if not device_id:
            raise ValueError("Device ID cannot be empty.")
        self.device_id = device_id
        self.screenshot_dir = settings.get_setting("device.screenshot_dir", "/sdcard/task_droid_temp")
        self.xml_dir = settings.get_setting("device.xml_dir", "/sdcard/task_droid_temp")
        
        log_message("INFO", f"Initializing operator for device: {self.device_id}", component="DeviceOperator")
        self._execute_command(f"shell mkdir -p {self.screenshot_dir}")
        self._execute_command(f"shell mkdir -p {self.xml_dir}")
        
        self.width, self.height = self._get_screen_resolution()
        if self.width == 0 or self.height == 0:
            log_message("ERROR", "Failed to get device screen resolution. Operator may not function correctly.", component="DeviceOperator", color="red")

    def _execute_command(self, command: str) -> tuple[bool, str]:
        """Internal helper to run ADB commands for the selected device."""
        base_cmd = ["adb", "-s", self.device_id]
        full_cmd_list = base_cmd + shlex.split(command)
        
        # Hide sensitive text input from logs
        log_cmd = " ".join(full_cmd_list)
        if "input" in command and "text" in command:
            log_cmd = "adb -s " + self.device_id + " shell input text <hidden>"
            
        log_message("ACTION", f"Executing: {log_cmd}", component="DeviceOperator", color="yellow")
        
        try:
            result = subprocess.run(full_cmd_list, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                error_output = result.stderr.strip()
                log_message("WARNING", f"Command failed. Stderr: {error_output}", component="DeviceOperator", color="yellow")
                return False, error_output
            return True, result.stdout.strip()
        except FileNotFoundError:
            log_message("ERROR", "'adb' not found. Ensure it's in your system's PATH.", component="DeviceOperator", color="red")
            return False, "ADB not found"
        except Exception as e:
            log_message("ERROR", f"An unexpected error occurred: {e}", component="DeviceOperator", color="red")
            return False, str(e)

    def _get_screen_resolution(self) -> Tuple[int, int]:
        """Fetches and returns the device's screen width and height."""
        success, output = self._execute_command("shell wm size")
        if success and "Physical size:" in output:
            try:
                res_str = output.split("Physical size:")[1].strip()
                w, h = map(int, res_str.split('x'))
                log_message("SUCCESS", f"Screen resolution: {w}x{h}", component="DeviceOperator", color="green")
                return w, h
            except Exception as e:
                log_message("ERROR", f"Could not parse screen resolution: {e}", component="DeviceOperator", color="red")
        return 0, 0

    # --- App Management ---
    def launch_app(self, package_name: str) -> bool:
        """Launches an application using its package name."""
        success, _ = self._execute_command(f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        if not success:
            log_message("ERROR", f"Failed to launch app {package_name}", component="DeviceOperator", color="red")
        return success

    def close_app(self, package_name: str) -> bool:
        """Force-stops an application."""
        success, _ = self._execute_command(f"shell am force-stop {package_name}")
        return success

    # --- UI State Capture ---
    def capture_screen(self, filename_prefix: str, local_save_dir: str) -> str:
        """Takes a screenshot and pulls it to the local machine."""
        os.makedirs(local_save_dir, exist_ok=True)
        device_path = f"{self.screenshot_dir}/{filename_prefix}.png"
        local_path = os.path.join(local_save_dir, f"{filename_prefix}.png")
        
        cap_ok, _ = self._execute_command(f"shell screencap -p {device_path}")
        if not cap_ok: return "ERROR"
        
        pull_ok, _ = self._execute_command(f"pull {device_path} {local_path}")
        if not pull_ok: return "ERROR"
        
        return local_path

    def get_ui_dump(self, filename_prefix: str, local_save_dir: str) -> str:
        """Dumps the UI hierarchy to XML and pulls it."""
        os.makedirs(local_save_dir, exist_ok=True)
        device_path = f"{self.xml_dir}/{filename_prefix}.xml"
        local_path = os.path.join(local_save_dir, f"{filename_prefix}.xml")
        
        dump_ok, _ = self._execute_command(f"shell uiautomator dump {device_path}")
        if not dump_ok: return "ERROR"

        pull_ok, _ = self._execute_command(f"pull {device_path} {local_path}")
        if not pull_ok: return "ERROR"

        return local_path

    # --- Basic Interactions ---
    def tap(self, x: int, y: int):
        self._execute_command(f"shell input tap {x} {y}")

    def type_text(self, text: str):
        escaped_text = text.replace(" ", "%s").replace("'", "'\\''")
        self._execute_command(f"shell input text '{escaped_text}'")

    def long_press(self, x: int, y: int, duration_ms: int = 1000):
        self._execute_command(f"shell input swipe {x} {y} {x} {y} {duration_ms}")

    def swipe(self, start_x, start_y, end_x, end_y, duration_ms=400):
        self._execute_command(f"shell input swipe {start_x} {start_y} {end_x} {end_y} {duration_ms}")

    def swipe_screen(self, direction: str, distance_ratio: float = 0.5):
        """Performs a swipe across the screen in a given direction."""
        center_x, center_y = self.width // 2, self.height // 2
        offset_x = int(self.width * distance_ratio / 2)
        offset_y = int(self.height * distance_ratio / 2)
        
        if direction.lower() == "up":
            self.swipe(center_x, center_y + offset_y, center_x, center_y - offset_y)
        elif direction.lower() == "down":
            self.swipe(center_x, center_y - offset_y, center_x, center_y + offset_y)
        elif direction.lower() == "left":
            self.swipe(center_x + offset_x, center_y, center_x - offset_x, center_y)
        elif direction.lower() == "right":
            self.swipe(center_x - offset_x, center_y, center_x + offset_x, center_y)

    # --- Key Events ---
    def press_key(self, keycode: int):
        self._execute_command(f"shell input keyevent {keycode}")

    def back(self): self.press_key(4)
    def home(self): self.press_key(3)
    def enter(self): self.press_key(66)
    def delete(self): self.press_key(67)
    def delete_multiple(self, count: int):
        for _ in range(count):
            self.delete()
            time.sleep(0.05) # Small delay to ensure command registers
    def app_switch(self): self.press_key(187)

    # --- System UI ---
    def open_notifications(self):
        self._execute_command("shell cmd statusbar expand-notifications")