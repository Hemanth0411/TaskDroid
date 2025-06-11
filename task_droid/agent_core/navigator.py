import os
import time
import datetime
import shutil
import ast
import json
import re

from task_droid.config import settings
from task_droid.shared.log_utils import log_message
from task_droid.shared import image_utils  # Make sure image_utils is imported
from task_droid.device_interface.device_operator import DeviceOperator
from task_droid.device_interface.ui_parser import extract_interactive_elements
from task_droid.llm_gateway import (
    base_connector, openai_connector, gemini_connector, response_parser
)
from task_droid.assets import prompt_library

class Navigator:
    def __init__(self, task_dir: str, docs_dir: str, device_op: DeviceOperator, task_desc: str):
        self.task_dir = task_dir
        self.docs_dir = docs_dir
        self.screenshot_dir = os.path.join(task_dir, "screenshots")
        self.xml_dir = os.path.join(task_dir, "xmls")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        os.makedirs(self.xml_dir, exist_ok=True)
        os.makedirs(self.docs_dir, exist_ok=True)
        
        self.device_op = device_op
        self.task_desc = task_desc
        self.vlm_connector = self._initialize_vlm_connector()
        
        # State Management
        self.round_count = 0
        self.last_action_summary = "None"
        self.task_complete = False
        
        # Sub-goal state
        self.sub_goals = []
        self.current_sub_goal_index = 0

        self.grid_mode = False
        self.grid_rows = 0
        self.grid_cols = 0

    def _initialize_vlm_connector(self):
        provider = settings.get_setting("vlm_provider", "gemini").lower()
        log_message("LLM", f"Initializing VLM provider: {provider.upper()}", component="Navigator")
        if provider == "openai":
            return openai_connector.OpenAIConnector(model_name=settings.get_setting("openai.model_name"), api_key=settings.get_setting("openai.api_key"))
        elif provider == "gemini":
            return gemini_connector.GeminiConnector(model_name=settings.get_setting("gemini.model_name"), api_key=settings.get_setting("gemini.api_key"))
        else:
            raise ValueError(f"Unsupported VLM provider: {provider}")

    def _get_formatted_element_list(self, elements: list) -> str:
        if not elements:
            return "No interactive elements were found on the screen."
        
        formatted_list = []
        for i, elem in enumerate(elements):
            text_desc = f", text: \"{elem.text}\"" if elem.text else ""
            formatted_list.append(f"- element_id: {i+1}{text_desc}, uid: {elem.uid}")
        return "\n".join(formatted_list)

    def _decompose_task_into_sub_goals(self):
        """
        Calls the VLM to get an initial list of sub-goals for the main task.
        """
        log_message("AGENT", "Decomposing task into sub-goals...", component="Navigator", color="cyan")
        prompt = prompt_library.SUBGOAL_DECOMPOSITION_PROMPT.format(task_description=self.task_desc)
        
        # This is a text-only prompt, so no images are needed
        success, response = self.vlm_connector.get_response(prompt, [])
        
        if success:
            try:
                # Extract the Python list from the response
                list_str_match = re.search(r'\[.*\]', response, re.DOTALL)
                if list_str_match:
                    self.sub_goals = ast.literal_eval(list_str_match.group(0))
                    log_message("SUCCESS", "Successfully decomposed task into sub-goals:", component="Navigator", color="green")
                    for i, goal in enumerate(self.sub_goals):
                        print(f"  {i+1}. {goal}")
                else:
                    raise ValueError("No list found in response")
            except Exception as e:
                log_message("ERROR", f"Failed to parse sub-goal list from VLM response: {e}", component="Navigator", color="red")
                self.sub_goals = [self.task_desc] # Fallback to using the whole task description
        else:
            log_message("ERROR", "VLM call failed during sub-goal decomposition.", component="Navigator", color="red")
            self.sub_goals = [self.task_desc] # Fallback

    def _get_element_center(self, elem_idx, elements):
        elem = elements[elem_idx - 1]
        x = (elem.bbox[0][0] + elem.bbox[1][0]) // 2
        y = (elem.bbox[0][1] + elem.bbox[1][1]) // 2
        return x, y

    def _area_to_xy(self, area, subarea):
        """Converts a grid area and subarea to screen (x, y) coordinates."""
        if self.grid_cols == 0 or self.grid_rows == 0:
            log_message("ERROR", "Grid dimensions are not set. Cannot calculate XY.", component="Navigator")
            return None, None
            
        area -= 1 # Adjust to be 0-indexed
        row = area // self.grid_cols
        col = area % self.grid_cols
        
        col_width = self.device_op.width / self.grid_cols
        row_height = self.device_op.height / self.grid_rows
        
        x_0, y_0 = col * col_width, row * row_height
        
        subarea_map = {
            "center":       (col_width * 0.5, row_height * 0.5),
            "top-left":     (col_width * 0.25, row_height * 0.25),
            "top":          (col_width * 0.5, row_height * 0.25),
            "top-right":    (col_width * 0.75, row_height * 0.25),
            "left":         (col_width * 0.25, row_height * 0.5),
            "right":        (col_width * 0.75, row_height * 0.5),
            "bottom-left":  (col_width * 0.25, row_height * 0.75),
            "bottom":       (col_width * 0.5, row_height * 0.75),
            "bottom-right": (col_width * 0.75, row_height * 0.75),
        }
        
        offset_x, offset_y = subarea_map.get(subarea.lower(), subarea_map["center"])
        return int(x_0 + offset_x), int(y_0 + offset_y)
        
    def _execute_action(self, action_name: str, params: list, elements: list) -> tuple[str, int]:
        # It only handles labeled-element actions. Grid actions will be handled directly in run().
        interacted_uid = ""
        element_idx = -1
        if action_name == "type_text" and not params:
            log_message("WARNING", "type_text action called with no text. Skipping.", component="Navigator")
            return "", -1
        action_map = {
            "tap": lambda p: self.device_op.tap(*self._get_element_center(p[0], elements)),
            "type_text": lambda p: self.device_op.type_text(p[0]),
            "long_press": lambda p: self.device_op.long_press(*self._get_element_center(p[0], elements)),
            "swipe_element": lambda p: self.device_op.swipe(*self._get_element_center(p[0], elements), p[1], p[2]),
            "swipe_screen": lambda p: self.device_op.swipe_screen(p[0]),
            "wait": lambda p: time.sleep(p[0]),
            "go_back": lambda p: self.device_op.back(),
            "press_enter": lambda p: self.device_op.enter(),
            "delete_multiple": lambda p: self.device_op.delete_multiple(p[0]),
            "finish": lambda p: setattr(self, 'task_complete', True)
        }
        handler = action_map.get(action_name)
        if handler:
            if action_name in ["tap", "long_press", "swipe_element"]:
                if not elements:
                    log_message("WARNING", f"Action '{action_name}' called but no elements are available. Skipping.", component="Navigator")
                    return "", -1
                element_idx = params[0]
                if 1 <= element_idx <= len(elements):
                    interacted_uid = elements[element_idx - 1].uid
                else:
                    log_message("WARNING", f"Action '{action_name}' called with invalid element index: {element_idx}", component="Navigator")
                    return "", -1
            log_message("ACTION", f"Executing VLM action: {action_name} with params: {params}", component="Navigator", color="magenta")
            handler(params)
        else:
            log_message("ERROR", f"Unknown action requested by VLM: {action_name}", component="Navigator", color="red")
        return interacted_uid, element_idx

    def _reflect_and_document(self, before_path: str, after_path: str, action_name: str, interacted_uid: str):
        prompt = prompt_library.REFLECTION_PROMPT.format(task_description=self.task_desc, last_action_summary=self.last_action_summary)
        success, response = self.vlm_connector.get_response(prompt, [before_path, after_path])
        if not success: return
        parsed = response_parser.parse_reflection_response(response)
        if not parsed: return
        log_message("INFO", f"Reflection Decision: {parsed['decision']} - {parsed['thought']}", component="Navigator", color="blue")
        if parsed['decision'] == 'BACK':
            self.device_op.back()
        doc = parsed.get("documentation", "N/A")
        if doc != "N/A" and interacted_uid and parsed['decision'] != "INEFFECTIVE":
            doc_path = os.path.join(self.docs_dir, f"{interacted_uid}.txt")
            with open(doc_path, "w", encoding='utf-8') as f: f.write(doc)
            log_message("SUCCESS", f"Documentation created/updated for element {interacted_uid}.", component="Navigator")
            
        # Placed inside the Navigator class

    def run(self, agent_mode: str):
        max_rounds = settings.get_setting(f"agent.max_{agent_mode}_rounds", 30)
        
        # --- Task Decomposition (runs only for "task" mode) ---
        if agent_mode == "task":
            self._decompose_task_into_sub_goals()
            if not self.sub_goals:
                log_message("ERROR", "Could not create a sub-goal plan. Aborting task.", color="red", component="Navigator")
                return
        
        log_message("AGENT", f"Starting navigation in {agent_mode.upper()} mode for {max_rounds} rounds.", color="green", component="Navigator")
        
        interactive_elements = []
        
        try:
            # --- Initial UI Element Loading Loop ---
            initial_load_attempts = 5
            initial_load_delay_sec = 3
            initial_screenshot_path = ""
            initial_xml_path = ""
            for attempt in range(initial_load_attempts):
                prefix = f"0_init_attempt_{attempt + 1}"
                initial_screenshot_path = self.device_op.capture_screen(prefix, self.screenshot_dir)
                initial_xml_path = self.device_op.get_ui_dump(prefix, self.xml_dir)
                
                if initial_xml_path != "ERROR":
                    interactive_elements = extract_interactive_elements(initial_xml_path)
                    if interactive_elements:
                        log_message("SUCCESS", f"Found {len(interactive_elements)} interactive elements. Proceeding.", color="green", component="Navigator")
                        break
                
                log_message("WARNING", f"Attempt {attempt + 1}: No interactive elements found. Retrying in {initial_load_delay_sec}s...", color="yellow", component="Navigator")
                time.sleep(initial_load_delay_sec)
            else:
                log_message("ERROR", "Failed to find any interactive elements after multiple attempts. Aborting.", color="red", component="Navigator")
                return

            # --- Main Execution Loop ---
            while self.round_count < max_rounds and not self.task_complete:
                self.round_count += 1
                log_message("AGENT", f"--- Round {self.round_count}/{max_rounds} ---", color="yellow", component="Navigator")

                # Use the state from the initial load on the first round
                if self.round_count == 1:
                    screenshot_path = initial_screenshot_path
                    xml_path = initial_xml_path
                    # `interactive_elements` is already populated
                else:
                    prefix = f"{self.round_count}_{int(time.time())}"
                    screenshot_path = self.device_op.capture_screen(prefix, self.screenshot_dir)
                    xml_path = self.device_op.get_ui_dump(prefix, self.xml_dir)
                    if screenshot_path == "ERROR" or xml_path == "ERROR":
                        log_message("ERROR", "Failed to capture screen state. Skipping round.", color="red", component="Navigator")
                        continue
                    interactive_elements = extract_interactive_elements(xml_path)

                # --- Sub-goal Management ---
                current_sub_goal = "Explore freely." # Default for exploration mode
                if agent_mode == "task":
                    if self.current_sub_goal_index >= len(self.sub_goals):
                        log_message("SUCCESS", "All sub-goals completed. Finishing task.", color="green", component="Navigator")
                        self.task_complete = True
                        break
                    current_sub_goal = self.sub_goals[self.current_sub_goal_index]
                
                annotated_shot_path = os.path.join(self.screenshot_dir, f"{prefix}_annotated.png")

                # --- Prompt Generation and VLM Call ---
                if self.grid_mode:
                    # Grid mode logic (can also be enhanced with sub-goals)
                    log_message("INFO", "Operating in GRID mode.", color="cyan", component="Navigator")
                    self.grid_rows, self.grid_cols = image_utils.draw_grid(screenshot_path, annotated_shot_path)
                    prompt = prompt_library.TASK_EXECUTION_GRID_PROMPT.format(
                        current_sub_goal=current_sub_goal,
                        last_action_summary=self.last_action_summary
                    )
                    success, response = self.vlm_connector.get_response(prompt, [annotated_shot_path])
                    parsed_action = response_parser.parse_grid_response(response) if success else None
                else:
                    # Labeled Element Mode
                    log_message("INFO", "Operating in LABELED ELEMENT mode.", color="cyan", component="Navigator")
                    image_utils.label_ui_elements(screenshot_path, annotated_shot_path, interactive_elements)
                    element_list_str = self._get_formatted_element_list(interactive_elements)
                    
                    # Doc retrieval
                    retrieved_docs = [] # ... your doc retrieval logic here ...
                    ui_documentation_str = "\n".join(retrieved_docs) if retrieved_docs else "No documentation available."

                    prompt_template = prompt_library.APP_EXPLORATION_PROMPT if agent_mode == 'explore' else prompt_library.TASK_EXECUTION_PROMPT
                    prompt = prompt_template.format(
                        task_description=self.task_desc,
                        sub_goal_list="\n".join([f"{i+1}. {'[DONE] ' if i < self.current_sub_goal_index else ''}{goal}" for i, goal in enumerate(self.sub_goals)]),
                        current_sub_goal=current_sub_goal,
                        element_list=element_list_str,
                        ui_documentation=ui_documentation_str,
                        last_action_summary=self.last_action_summary
                    )
                    success, response = self.vlm_connector.get_response(prompt, [annotated_shot_path])
                    parsed_action = response_parser.parse_action_response(response) if success else None

                # --- Action Handling & State Update ---
                if not parsed_action:
                    self.last_action_summary = "Failed to parse VLM response. Will retry."
                    continue

                self.last_action_summary = parsed_action.get('summary', "No summary provided.")
                action_name = parsed_action.get('action_name', 'error')
                action_params = parsed_action.get('action_params', [])

                # Handle meta-actions first
                if action_name == 'finish':
                    self.task_complete = True
                    break
                
                if action_name == 'subgoal_complete':
                    log_message("SUCCESS", f"Sub-goal '{current_sub_goal}' marked as complete.", color="green", component="Navigator")
                    self.current_sub_goal_index += 1
                    time.sleep(1) # Small delay before starting next sub-goal
                    continue

                interacted_uid = ""
                if self.grid_mode:
                    # ... execute grid actions ...
                    self.grid_mode = False # Always exit grid mode after one action
                else:
                    if action_name == 'grid':
                        self.grid_mode = True
                        log_message("INFO", "Switching to GRID mode for the next round.", component="Navigator")
                        continue
                    
                    interacted_uid, _ = self._execute_action(action_name, action_params, interactive_elements)

                # --- Reflection ---
                time.sleep(settings.get_setting("agent.request_interval_sec", 2))
                
                if action_name not in ['finish', 'wait', 'grid', 'subgoal_complete']:
                    after_prefix = f"{self.round_count}_{int(time.time())}_after"
                    after_screenshot_path = self.device_op.capture_screen(after_prefix, self.screenshot_dir)
                    if after_screenshot_path != "ERROR":
                        self._reflect_and_document(annotated_shot_path, after_screenshot_path, action_name, interacted_uid)

        except KeyboardInterrupt:
            log_message("WARNING", "\nCtrl+C detected. Shutting down agent navigation.", color="yellow", component="Navigator")
            raise 
        
        finally:
            log_message("CLEANUP", "Navigator cleaning up session files...", component="Navigator")
            try:
                if os.path.exists(self.screenshot_dir): shutil.rmtree(self.screenshot_dir)
                if os.path.exists(self.xml_dir): shutil.rmtree(self.xml_dir)
            except Exception as e:
                log_message("ERROR", f"Error during local cleanup: {e}", color="red", component="Navigator")