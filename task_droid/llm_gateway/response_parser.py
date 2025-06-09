import re
import traceback
from typing import List, Dict, Any

from task_droid.shared.log_utils import log_message

def _extract_section(pattern: str, text: str) -> str | None:
    """Extracts a section from the VLM response using regex."""
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None

def parse_action_response(response: str) -> Dict[str, Any] | None:
    """
    Parses the VLM's response to extract the thought, action, and summary.
    
    Args:
        response (str): The raw text response from the VLM.

    Returns:
        A dictionary with 'thought', 'action_name', 'action_params', 'summary'
        or None if parsing fails.
    """
    try:
        observation = _extract_section(r"Observation:\s*(.*?)(Thought:|$)", response)
        thought = _extract_section(r"Thought:\s*(.*?)(Action:|$)", response)
        action_str = _extract_section(r"Action:\s*(.*?)(Summary:|$)", response)
        summary = _extract_section(r"Summary:\s*(.*)", response)

        if not all([thought, action_str, summary]):
            log_message("ERROR", "Could not parse one or more required sections (Thought, Action, Summary) from VLM response.", component="ResponseParser", color="red")
            log_message("DEBUG", f"Full Response:\n{response}", component="ResponseParser")
            return None

        # Clean the action string by removing potential markdown backticks
        action_str = action_str.strip("` ")

        log_message("OBSERVATION", f"{observation}", component="VLM")
        log_message("THOUGHT", f"{thought}", component="VLM", color="magenta")
        log_message("ACTION", f"Raw: '{action_str}'", component="VLM", color="cyan")
        
        # --- Action Parsing Logic ---
        # Match action name and parameters within parentheses
        match = re.match(r"(\w+)\s*\((.*)\)", action_str)
        if match:
            name = match.group(1).lower()
            params_str = match.group(2).strip()
            # Split params by comma, strip quotes and spaces
            params = [p.strip(" '\"") for p in params_str.split(',')]
            # Convert numeric params to int
            parsed_params = [int(p) if p.isdigit() else p for p in params]
            action_params = parsed_params
        else:
            # Handle parameter-less actions
            name = action_str.lower().strip()
            action_params = []

        return {
            "thought": thought,
            "action_name": name,
            "action_params": action_params,
            "summary": summary
        }

    except Exception as e:
        log_message("ERROR", f"Critical error parsing VLM action response: {e}\n{traceback.format_exc()}", component="ResponseParser", color="red")
        return None

def parse_reflection_response(response: str) -> Dict[str, str] | None:
    """
    Parses the VLM's reflection response.

    Args:
        response (str): The raw text response from the VLM.

    Returns:
        A dictionary with 'decision', 'thought', and 'documentation',
        or None if parsing fails.
    """
    try:
        decision = _extract_section(r"Decision:\s*(.*?)(Thought:|$)", response)
        thought = _extract_section(r"Thought:\s*(.*?)(Documentation:|$)", response)
        documentation = _extract_section(r"Documentation:\s*(.*)", response)

        if not decision or not thought:
            log_message("ERROR", "Could not parse Decision or Thought from reflection response.", component="ResponseParser", color="red")
            return None
        
        # Documentation is optional, default to "N/A"
        documentation = documentation if documentation else "N/A"

        # Validate decision
        valid_decisions = ["BACK", "CONTINUE", "SUCCESS", "INEFFECTIVE"]
        if decision.upper() not in valid_decisions:
            log_message("WARNING", f"Invalid decision '{decision}' in reflection. Defaulting to CONTINUE.", component="ResponseParser")
            decision = "CONTINUE"

        return {
            "decision": decision.upper(),
            "thought": thought,

            "documentation": documentation
        }

    except Exception as e:
        log_message("ERROR", f"Critical error parsing VLM reflection response: {e}\n{traceback.format_exc()}", component="ResponseParser", color="red")
        return None