import requests
from typing import List

from .base_connector import BaseVLMConnector
from task_droid.shared.log_utils import log_message
from task_droid.shared.image_utils import encode_image_to_base64
from task_droid.config import settings

class OpenAIConnector(BaseVLMConnector):
    """Concrete VLM connector for OpenAI models."""

    def __init__(self, model_name: str, api_key: str, **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        self.api_base = settings.get_setting("openai.api_base", "https://api.openai.com/v1/chat/completions")
        log_message("SUCCESS", f"OpenAIConnector initialized for model: {self.model_name}", component="OpenAIConnector", color="green")

    def get_response(self, prompt: str, images: List[str]) -> tuple[bool, str]:
        log_message("LLM", f"Sending request to OpenAI model: {self.model_name}", component="OpenAIConnector", color="cyan")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        content = [{"type": "text", "text": prompt}]
        for img_path in images:
            base64_image = encode_image_to_base64(img_path)
            if base64_image:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        try:
            response = requests.post(self.api_base, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            res_json = response.json()

            if "error" in res_json:
                error_msg = res_json["error"]["message"]
                log_message("ERROR", f"OpenAI API Error: {error_msg}", component="OpenAIConnector", color="red")
                return False, error_msg
            
            return True, res_json["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            log_message("ERROR", f"Request to OpenAI API failed: {e}", component="OpenAIConnector", color="red")
            return False, str(e)
        except Exception as e:
            log_message("ERROR", f"An unexpected error occurred: {e}", component="OpenAIConnector", color="red")
            return False, str(e)