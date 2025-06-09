import abc
from typing import List

class BaseVLMConnector(abc.ABC):
    """
    Abstract Base Class for Vision Language Model connectors.
    Defines the standard interface for communicating with a VLM.
    """
    def __init__(self, model_name: str, api_key: str, temperature: float = 0.0, max_tokens: int = 1024):
        self.model_name = model_name
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abc.abstractmethod
    def get_response(self, prompt: str, images: List[str]) -> tuple[bool, str]:
        """
        Sends a prompt and a list of image paths to the VLM and gets a response.

        Args:
            prompt (str): The text prompt for the VLM.
            images (List[str]): A list of local file paths for the images.

        Returns:
            tuple[bool, str]: A tuple containing a success flag (True/False)
                              and the response string or an error message.
        """
        pass