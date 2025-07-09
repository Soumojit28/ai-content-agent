# Deploy and Host LangGraph Agentic Service on Railway

LangGraph Agentic Service is a Python API that showcases **LangGraph ReAct agent patterns** with iterative text summarization and character limit enforcement. It demonstrates how to build Masumi Network-compliant agents using LangGraph's tool-based architecture, providing standardized endpoints for job processing, payment integration, and intelligent text processing through blockchain payments.

## About Hosting LangGraph Agentic Service

This service creates a FastAPI wrapper around a LangGraph ReAct agent that uses tools for iterative text summarization. The agent automatically adjusts summary length using character counting tools until it fits within specified limits. It handles job queuing, payment verification, status reporting, and provides Swagger documentation. The service connects to your deployed Masumi Payment Service to process transactions and manage agent registrations on the Cardano blockchain.

## Common Use Cases

- Demonstrate LangGraph ReAct agent patterns for educational purposes
- Build intelligent text summarization services with configurable character limits
- Create pay-per-use AI services with iterative workflows and crypto payments
- Showcase tool-based agent architectures for the Masumi marketplace

## Dependencies for LangGraph Agentic Service Hosting

- Deployed Masumi Payment Service instance
- Python 3.10+ runtime environment
- OpenAI API key (for gpt-4o-mini model)

### Deployment Dependencies

[Masumi Payment Service Template](https://railway.app) - Deploy this first to handle payments

### Implementation Details

The service includes a customizable `langgraph_service.py` file that implements a ReAct agent with tools:

```python
@tool
def summarize_text(text: str, char_limit: int = 240) -> str:
    """Summarize text with character limit using gpt-4o-mini"""
    # LangGraph tool implementation

@tool 
def count_characters(text: str) -> int:
    """Count characters in text"""
    return len(text)

# ReAct agent workflow:
# 1. Summarize text with character limit
# 2. Count characters in summary  
# 3. Re-summarize if over limit
# 4. Repeat until within character limit
```

## Why Deploy LangGraph Agentic Service on Railway?

Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it.

By deploying LangGraph Agentic Service on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.