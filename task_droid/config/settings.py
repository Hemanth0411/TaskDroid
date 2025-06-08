import os
import yaml
from task_droid.shared.log_utils import log_message

_configs = None

def _load_settings():
    """
    Loads settings from settings.yaml and environment variables.
    Environment variables have higher precedence.
    """
    global _configs
    if _configs is not None:
        return _configs

    # Default to a path relative to this file, assuming settings.yaml is in the project root
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'settings.yaml')

    yaml_settings = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                yaml_settings = yaml.safe_load(f) or {}
        except Exception as e:
            log_message("WARNING", f"Could not load or parse {config_path}: {e}. Continuing...", component="Settings")
            yaml_settings = {}
    else:
        log_message("INFO", f"Configuration file {config_path} not found. Relying on defaults and environment variables.", component="Settings")

    # A simple way to merge nested dicts, with env vars taking precedence
    # We will provide helper functions to access nested properties easily.
    final_settings = yaml_settings

    # Example of overriding nested keys with environment variables
    # VLM Provider
    final_settings['vlm_provider'] = os.getenv('VLM_PROVIDER', final_settings.get('vlm_provider'))
    
    # API Keys
    final_settings.setdefault('gemini', {})['api_key'] = os.getenv('GEMINI_API_KEY', final_settings.get('gemini', {}).get('api_key'))
    final_settings.setdefault('openai', {})['api_key'] = os.getenv('OPENAI_API_KEY', final_settings.get('openai', {}).get('api_key'))
    final_settings.setdefault('qwen', {})['api_key'] = os.getenv('DASHSCOPE_API_KEY', final_settings.get('qwen', {}).get('api_key'))
    
    _configs = final_settings
    log_message("SUCCESS", "Settings loaded and merged.", component="Settings", color="green")
    return _configs

def get_setting(key_path: str, default=None):
    """
    Retrieves a setting using a dot-separated path.

    Args:
        key_path (str): The dot-separated key (e.g., "agent.max_task_rounds").
        default: The value to return if the key is not found.

    Returns:
        The value of the setting or the default.
    """
    settings = _load_settings()
    keys = key_path.split('.')
    value = settings
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

# Initialize settings on first import
_load_settings()