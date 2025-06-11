import re
import traceback
from typing import List, Dict, Any

from task_droid.shared.log_utils import log_message

def _extract_section(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None

def parse_reflection_response(response: str) -> Dict[str, str] | None:
    try:
        decision = _extract_section(r"Decision:\s*(.*?)(Thought:|$)", response)
        thought = _extract_section(r"Thought:\s*(.*?)(Documentation:|$)", response)
        documentation = _extract_section(r"Documentation:\s*(.*)", response)
        if not decision or not thought:
            log_message("ERROR", "Could not parse Decision or Thought from reflection response.", component="ResponseParser", color="red")
            return None
        documentation = documentation if documentation else "N/A"
        valid_decisions = ["BACK", "CONTINUE", "SUCCESS", "INEFFECTIVE"]
        if decision.upper() not in valid_decisions:
            log_message("WARNING", f"Invalid decision '{decision}' in reflection. Defaulting to CONTINUE.", component="ResponseParser")
            decision = "CONTINUE"
        return {"decision": decision.upper(), "thought": thought, "documentation": documentation}
    except Exception as e:
        log_message("ERROR", f"Critical error parsing VLM reflection response: {e}\n{traceback.format_exc()}", component="ResponseParser", color="red")
        return None
    
def parse_action_with_plan_response(response: str) -> Dict[str, Any] | None:
    try:
        parsed = parse_action_response(response) # Reuse the existing logic
        if not parsed:
            return None

        plan = _extract_section(r"Current Plan:\s*(.*)", response) or "N/A"
        parsed['plan'] = plan
        
        log_message("PLAN", f"{plan}", component="VLM", color="blue") # Log the plan

        return parsed
    except Exception as e:
        log_message("ERROR", f"Critical error parsing VLM action+plan response: {e}\n{traceback.format_exc()}", component="ResponseParser", color="red")
        return None
    
def parse_action_response(response: str) -> Dict[str, Any] | None:
    try:
        action_str_match = re.search(r"Action:\s*(.*)", response, re.DOTALL | re.IGNORECASE)
        if not action_str_match:
            log_message("ERROR", "Could not find 'Action:' in VLM response.", component="ResponseParser", color="red")
            return None
        
        action_line = action_str_match.group(1).split('\n')[0].strip()
        
        # *** FINAL PARSER FIX: Handle backticks around parameter-less commands ***
        action_str_cleaned = action_line.strip("` ")

        command_match = re.search(r"(\w+\(.*\))", action_str_cleaned)
        if command_match:
            action_str = command_match.group(1)
        else:
            command_match_simple = re.search(r"^(\w+)", action_str_cleaned)
            if not command_match_simple:
                log_message("ERROR", f"Could not parse a valid command from action line: '{action_str_cleaned}'", component="ResponseParser", color="red")
                return None
            action_str = command_match_simple.group(1)
            
        thought = _extract_section(r"Thought:\s*(.*?)(Action:|$)", response) or "No thought provided."
        summary = _extract_section(r"Summary:\s*(.*)", response) or "No summary provided."
        observation = _extract_section(r"Observation:\s*(.*?)(Thought:|$)", response) or "No observation provided."
        
        log_message("OBSERVATION", f"{observation}", component="VLM")
        log_message("THOUGHT", f"{thought}", component="VLM", color="magenta")
        log_message("ACTION", f"Raw: '{action_str}'", component="VLM", color="cyan")
        
        match = re.match(r"(\w+)\s*\((.*)\)", action_str)
        if match:
            name = match.group(1).lower()
            params_str = match.group(2).strip()
            raw_params = [p.strip() for p in params_str.split(',')]
            parsed_params = []
            for p in raw_params:
                if ':' in p: val = p.split(':', 1)[1].strip()
                else: val = p
                val_cleaned = val.strip(" '\"")
                if name != "type_text" and val_cleaned.isdigit(): parsed_params.append(int(val_cleaned))
                else: parsed_params.append(val_cleaned)
            action_params = parsed_params
        else:
            name = action_str.lower().strip()
            action_params = []

        return {"thought": thought, "action_name": name, "action_params": action_params, "summary": summary}
    except Exception as e:
        log_message("ERROR", f"Critical error parsing VLM action response: {e}\n{traceback.format_exc()}", component="ResponseParser", color="red")
        return None

