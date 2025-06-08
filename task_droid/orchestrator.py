"""
Main orchestrator for the Chameleon agent
"""
from .agent_core.navigator import Navigator
from .device_interface.device_operator import DeviceOperator
from .llm_gateway.base_connector import LLMConnector

class Orchestrator:
    def __init__(self):
        self.navigator = Navigator()
        self.device_operator = DeviceOperator()
        self.llm_connector = LLMConnector()

    def start_session(self):
        pass
