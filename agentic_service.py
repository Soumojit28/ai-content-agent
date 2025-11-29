from typing import Any, Dict, Optional


class ServiceResult:
    """Generic container for orchestrator results."""
    def __init__(
        self,
        *,
        raw: Any,
        json_dict: Dict[str, Any],
        original_text: str = "",
        extras: Optional[Dict[str, Any]] = None,
    ):
        self.raw = raw
        self.json_dict = json_dict
        self.original_text = original_text
        self.extras = extras or {}

class AgenticService:
    """Simple service that reverses input text"""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    async def execute_task(self, input_data: dict) -> ServiceResult:
        """
        Execute reverse echo task
        
        Args:
            input_data: Dictionary containing 'input_string' key
            
        Returns:
            ServiceResult with reversed text
        """
        text = input_data.get("input_string", "")
        
        if self.logger:
            self.logger.info(f"Processing reverse echo for text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # simple reverse operation
        reversed_text = text[::-1]
        
        if self.logger:
            self.logger.info(f"Reverse echo completed: '{reversed_text[:50]}{'...' if len(reversed_text) > 50 else ''}'")
        
        return ServiceResult(
            raw=reversed_text,
            json_dict={
                "original_text": text,
                "reversed_text": reversed_text,
                "task": "reverse_echo"
            },
            original_text=text
        )

def get_agentic_service(logger=None):
    """
    Factory function to get the appropriate service for this branch.
    This enables easy switching between different implementations across branches.
    
    LangChain branch: LangGraph-based agent implementation
    """
    from langgraph_service import LangGraphService
    return LangGraphService(logger) 