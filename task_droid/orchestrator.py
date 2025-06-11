import argparse
import os
import sys
import time
import datetime

from task_droid.config import settings
from task_droid.shared.log_utils import log_message
from tools import apk_analyzer, app_installer, adb_wrapper
from task_droid.agent_core.navigator import Navigator
from task_droid.device_interface.device_operator import DeviceOperator
from task_droid.llm_gateway import response_parser

def select_device() -> str | None:
    """
    Prompts the user to select a device if multiple are connected.
    """
    devices = adb_wrapper.find_connected_devices()
    if not devices:
        log_message("ERROR", "No Android devices found. Please connect a device and enable USB debugging.", component="Orchestrator", color="red")
        return None
    
    if len(devices) == 1:
        log_message("SUCCESS", f"Automatically selected device: {devices[0]}", component="Orchestrator", color="green")
        return devices[0]
        
    log_message("INFO", "Multiple devices found. Please select one:", component="Orchestrator", color="blue")
    for i, dev in enumerate(devices):
        print(f"  {i + 1}. {dev}")
        
    while True:
        try:
            choice = int(input("Enter the number of the device: "))
            if 1 <= choice <= len(devices):
                return devices[choice - 1]
            else:
                log_message("WARNING", "Invalid choice. Please try again.", component="Orchestrator", color="yellow")
        except ValueError:
            log_message("WARNING", "Invalid input. Please enter a number.", component="Orchestrator", color="yellow")


def determine_agent_mode(task_description: str) -> str:
    """
    Determines agent mode based on keywords in the task description.
    """
    log_message("INFO", "Determining agent mode...", component="Orchestrator")
    
    explore_keywords = ["explore", "discover", "check out", "understand", "see what this app can do"]
    if any(kw in task_description.lower() for kw in explore_keywords):
        log_message("INFO", "Classified as 'explore' mode based on keywords.", component="Orchestrator")
        return "explore"
    
    log_message("INFO", "Classified as 'task' mode.", component="Orchestrator")
    return "task"
    

def main_workflow(args):
    """The main operational workflow for the TaskDroid agent."""
    log_message("ORCHESTRATOR", "--- TaskDroid Agent Workflow Initializing ---", component="Orchestrator", color="blue")
    
    device_operator = None # Initialize to ensure it's in scope for finally block
    package_name = None

    try:
        # 1. Setup Phase
        log_message("SETUP", "Starting pre-flight checks and setup...", component="Orchestrator", color="cyan")
        
        apk_info = apk_analyzer.get_apk_info(args.apk_path)
        if not apk_info:
            return
        package_name, app_name = apk_info
        log_message("SUCCESS", f"APK analysis complete: App='{app_name}', Package='{package_name}'", component="Orchestrator", color="green")

        device_id = select_device()
        if not device_id:
            return

        if not app_installer.install_apk(args.apk_path, device_id):
            return
        if not app_installer.is_package_present(package_name, device_id):
            return

        # 2. Agent Initialization
        log_message("AGENT", "Initializing agent core...", component="Orchestrator", color="cyan")
        
        root_output_dir = "app_output"
        sanitized_app_name = "".join(e for e in app_name if e.isalnum())
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = f"{sanitized_app_name}_{timestamp}"
        
        task_dir = os.path.join(root_output_dir, sanitized_app_name, "interaction_sessions", session_name)
        docs_dir = os.path.join(root_output_dir, sanitized_app_name, "knowledge_base")
        os.makedirs(task_dir, exist_ok=True)
        os.makedirs(docs_dir, exist_ok=True)
        log_message("SETUP", f"Session data will be saved in: {os.path.abspath(task_dir)}", component="Orchestrator")

        device_operator = DeviceOperator(device_id)
        if not device_operator.launch_app(package_name):
            log_message("ERROR", f"Failed to launch {app_name}. Aborting.", component="Orchestrator", color="red")
            return
        
        app_load_delay = settings.get_setting("agent.app_load_delay_sec", 5)
        log_message("INFO", f"Waiting {app_load_delay}s for app to fully load...", component="Orchestrator")
        time.sleep(app_load_delay)

        navigator = Navigator(task_dir, docs_dir, device_operator, args.task_description)
        agent_mode = determine_agent_mode(args.task_description)
        navigator.run(agent_mode)

    except KeyboardInterrupt:
        log_message("WARNING", "\nCtrl+C detected. Orchestrator initiating graceful shutdown.", component="Orchestrator", color="yellow")
    except Exception as e:
        log_message("ERROR", f"An unhandled exception occurred in the orchestrator: {e}", component="Orchestrator", color="red")
        import traceback
        traceback.print_exc()

    finally:
        # 3. Cleanup Phase
        log_message("CLEANUP", "Orchestrator starting final cleanup phase...", component="Orchestrator", color="cyan")
        if device_operator and package_name:
            log_message("CLEANUP", f"Closing application: {package_name}", component="Orchestrator")
            device_operator.close_app(package_name)
        
        log_message("ORCHESTRATOR", "--- TaskDroid Agent Workflow Finished ---", component="Orchestrator", color="blue")


def main():
    parser = argparse.ArgumentParser(description="TaskDroid: An AI-powered Android App Automation Agent.")
    parser.add_argument("apk_path", help="Path to the target .apk file.")
    parser.add_argument("task_description", help="The task for the agent to perform or a directive for exploration.")
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
    if not os.path.isfile(args.apk_path):
        log_message("ERROR", f"The provided APK path is not a valid file: {args.apk_path}", color="red")
        sys.exit(1)

    main_workflow(args)

if __name__ == "__main__":
    main()