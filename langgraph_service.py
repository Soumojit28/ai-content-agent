"""
LangGraph Service Implementation
Uses create_react_agent with tools for iterative text summarization with character limits
"""

from agentic_service import ServiceResult
from typing import Dict, Any
import os
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage


class LangGraphService:
    """
    LangGraph-based service implementation for text summarization with character limits
    
    Uses ReAct agent pattern with tools for iterative summarization
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        self.llm = ChatOpenAI(temperature=0.3, model="gpt-4o-mini")
        self.agent = self._create_agent()
    
    def _create_agent(self):
        """Create a ReAct agent with summarization and character counting tools"""
        
        @tool
        def summarize_text(text: str, char_limit: int = 240) -> str:
            """
            Summarize text with a specific character limit.
            
            Args:
                text: The text to summarize
                char_limit: Maximum characters for the summary
                
            Returns:
                A concise summary within the character limit
            """
            prompt = f"""
            Please summarize the following text in {char_limit} characters or less.
            Be concise but capture the key points.
            
            Text to summarize: {text}
            
            Summary:
            """
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
        
        @tool
        def count_characters(text: str) -> int:
            """
            Count characters in the given text.
            
            Args:
                text: The text to count characters for
                
            Returns:
                Number of characters in the text
            """
            return len(text)
        
        # Create tools list
        tools = [summarize_text, count_characters]
        
        # Create ReAct agent
        system_prompt = """
        You are a text summarization assistant. Your task is to:
        1. Summarize text within a specified character limit (default 240 characters)
        2. Count characters in your summary
        3. If the summary exceeds the limit, create a shorter version
        4. Continue until the summary fits within the character limit
        
        Always use the tools provided to you. First summarize, then count characters, 
        and re-summarize if needed until you achieve the target length.
        """
        
        return create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=system_prompt
        )
    
    async def execute_task(self, input_data: dict) -> ServiceResult:
        """
        Execute LangGraph summarization task with character limit enforcement
        
        Args:
            input_data: Dictionary containing:
                - 'input_string': Text to summarize
                - 'char_limit': Optional character limit (default: 240)
                
        Returns:
            ServiceResult with summarized text within character limit
        """
        text = input_data.get("input_string", "")
        char_limit = input_data.get("char_limit", 240)
        
        if self.logger:
            self.logger.info(f"Processing with LangGraph: '{text[:50]}{'...' if len(text) > 50 else ''}' (limit: {char_limit} chars)")
        
        # Create the user message with instructions
        user_message = f"""
        Please summarize this text within {char_limit} characters:
        
        {text}
        
        Make sure to:
        1. First create a summary using the summarize_text tool
        2. Count the characters using the count_characters tool
        3. If it's over {char_limit} characters, summarize again with a shorter version
        4. Continue until you get a summary that fits within {char_limit} characters
        """
        
        # Run the agent
        result = await self.agent.ainvoke({"messages": [HumanMessage(content=user_message)]})
        
        # Extract the final summary from the last AI message
        final_summary = result["messages"][-1].content
        
        # Clean up the summary (remove any tool-related text)
        if "count_characters" in final_summary or "summarize_text" in final_summary:
            # Find the actual summary content
            lines = final_summary.split('\n')
            summary_lines = []
            for line in lines:
                if not line.strip().startswith('count_characters') and not line.strip().startswith('summarize_text'):
                    if line.strip() and not line.strip().startswith('I'):
                        summary_lines.append(line.strip())
            
            if summary_lines:
                final_summary = summary_lines[-1]
            else:
                final_summary = final_summary.strip()
        
        # Verify character count
        actual_count = len(final_summary)
        
        if self.logger:
            self.logger.info(f"LangGraph summarization completed: {actual_count}/{char_limit} characters")
        
        # Create result with metadata
        result = ServiceResult(text, final_summary)
        result.json_dict = {
            "original_text": text,
            "summary": final_summary,
            "character_count": actual_count,
            "character_limit": char_limit,
            "within_limit": actual_count <= char_limit,
            "task": "langgraph_summarization_with_limit",
            "model": "gpt-4o-mini",
            "framework": "langgraph"
        }
        return result


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test function
# ─────────────────────────────────────────────────────────────────────────────

async def test_langgraph_service():
    """Test the LangGraph service independently"""
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return
    
    service = LangGraphService()
    
    test_cases = [
        {
            "input_string": "The quick brown fox jumps over the lazy dog. This is a classic pangram that contains all letters of the alphabet. It has been used for decades in typing tests and font demonstrations because it showcases every letter in a natural-sounding sentence.",
            "char_limit": 100
        },
        {
            "input_string": "LangGraph is a library for building stateful, multi-actor applications with LLMs. It extends the LangChain ecosystem by providing a framework for creating complex workflows with agents that can call tools and maintain state across interactions.",
            "char_limit": 50
        },
        {
            "input_string": "Hello world! This is a test.",
            "char_limit": 240  # Default limit
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = await service.execute_task(test_case)
            print(f"\n=== Test Case {i} ===")
            print(f"Input: '{test_case['input_string']}'")
            print(f"Character limit: {test_case['char_limit']}")
            print(f"Summary: '{result.raw}'")
            print(f"Summary length: {len(result.raw)} characters")
            print(f"Within limit: {result.json_dict['within_limit']}")
            print(f"Full metadata: {result.json_dict}")
        except Exception as e:
            print(f"Error processing test case {i}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_langgraph_service())