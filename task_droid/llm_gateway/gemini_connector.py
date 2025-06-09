from typing import List
import google.generativeai as genai
from PIL import Image

from .base_connector import BaseVLMConnector
from task_droid.shared.log_utils import log_message
from task_droid.shared.image_utils import encode_image_to_base64

class GeminiConnector(BaseVLMConnector):
    """Concrete VLM connector for Google's Gemini models."""

    def __init__(self, model_name: str, api_key: str, **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            log_message("SUCCESS", f"GeminiConnector initialized for model: {self.model_name}", component="GeminiConnector", color="green")
        except Exception as e:
            log_message("ERROR", f"Failed to configure Gemini: {e}", component="GeminiConnector", color="red")
            raise

    def get_response(self, prompt: str, images: List[str]) -> tuple[bool, str]:
        log_message("LLM", f"Sending request to Gemini model: {self.model_name}", component="GeminiConnector", color="cyan")
        
        try:
            model_input = [prompt]
            for img_path in images:
                try:
                    img = Image.open(img_path)
                    model_input.append(img)
                except FileNotFoundError:
                    log_message("ERROR", f"Image file not found: {img_path}", component="GeminiConnector", color="red")
                    return False, f"Image file not found: {img_path}"

            response = self.model.generate_content(model_input)
            
            if response.text:
                return True, response.text
            elif response.prompt_feedback and response.prompt_feedback.block_reason:
                err_msg = f"Gemini API call blocked. Reason: {response.prompt_feedback.block_reason}"
                log_message("ERROR", err_msg, component="GeminiConnector", color="red")
                return False, err_msg
            else:
                log_message("ERROR", "Gemini API call failed: No text in response.", component="GeminiConnector", color="red")
                return False, "Gemini API Error: No text content in response."

        except Exception as e:
            log_message("ERROR", f"An unexpected error occurred with Gemini API: {e}", component="GeminiConnector", color="red")
            return False, str(e)