# Masumi Agent Service - LangGraph Branch

## 🧠 LangGraph Integration

This branch demonstrates **LangGraph ReAct agent patterns** with iterative text summarization and character limit enforcement. The agent uses tools to summarize text and automatically adjusts the summary length until it fits within the specified character limit.

### Key Features

- **ReAct Agent Pattern**: Uses `create_react_agent` with tools for iterative workflows
- **Iterative Summarization**: Agent summarizes text, counts characters, and re-runs if over limit
- **Character Limit Enforcement**: Default 240 characters, configurable via `char_limit` parameter
- **Tool-Based Architecture**: Separate tools for summarization (gpt-4o-mini) and character counting
- **Full Masumi Compliance**: All MIP-003 endpoints implemented and tested

### Agent Workflow

1. **Input Processing**: Takes text + optional character limit (default: 240)
2. **Summarization**: Uses gpt-4o-mini to create initial summary with character limit in prompt
3. **Character Counting**: Counts characters in the generated summary
4. **Iteration**: If over limit, creates shorter summary and repeats
5. **Output**: Returns summary within character limit with metadata

### Prerequisites

- [Blockfrost](https://blockfrost.io/) API key
- **OpenAI API key** (for gpt-4o-mini model)
- For quick deployment: [Railway account](https://railway.com?referralCode=pa1ar) (free trial is 30 days or $5)

## Railway Deployment

> The purpose of this repository is to get you from 0 to agentic service owner in as little time as possible. Yet it is assumed, that you are somewhat familiar with [Masumi Network](https://masumi.network/). If you are not, please consider heading over to the official [Masumi docs](https://docs.masumi.network/) first.  

This example uses [Railway](https://railway.com?referralCode=pa1ar) templates. Railway is a cloud development platform that enables developers to deploy, manage and scale applications and databases with minimal configuration. Masumi Services obviously can be hosted anywhere, so feel free to use the templates as examples and pick a service of your choice.  

Railway templates we provide are pointing to the open-source repositories of Masumi organisation. That means you can read full code, if you want, to be sure nothing shady is going on. You can also fork the repositories first, and still use the templates by just pointing them to your forks, if you want.

### How to Deploy

1. **Deploy [Masumi Payment Service](https://github.com/masumi-network/masumi-payment-service)**:  

    [![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/masumi-payment-service-official?referralCode=padierfind)
   - Use the template in an existing or new project (in existing project, "Create" > "Template" > search for "Masumi Payment Service")
   - Provide Blockfrost API key in variables (required to click "deploy")
   - Click on deploy, watch the logs, wait for it (takes 5+ minutes, depending on the load on Railway)
   - You should see 2 services on your canvas, connected with an dotted arrow: a PostgreSQL database and a Masumi Payment Service.
   - Click on Masumi Payment Service on the canvas > Settings > Networking > Generate URL
   - Test at public URL `/admin` or `/docs`. Your default admin key (used to login to the admin panel and sign transactions) is in your variables. **Change it on the admin panel.**
   - **Important:** Masumi API endpoints must include `/api/v1/`!  Be sure to append that slugs in the next steps (deploying agentic service).

2. **Deploy [Agent Service API Wrapper](https://github.com/masumi-network/agentic-service-wrapper)**:  

    [![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/masumi-compliant-service-api-official?referralCode=padierfind)
   - Make sure your Masumi payment service is up and running
   - Provide `PAYMENT_SERVICE_URL` in variables (format: `https://your-instance-of-masumi.up.railway.app/api/v1`, the main part of the URL can differ, point is - don't forget the `/api/v1` slugs)
   - **Add `OPENAI_API_KEY`** to Railway variables (required for LangGraph agent)
   - Wait for deployment to complete
   - Generate public URL in settings of the service
   - Check the swagger at `/docs`

3. **Configure Agent**
   - Go to Payment Service admin panel, top up selling wallet
   - Register agent via Agent Service URL (you need to have funds on your selling wallet, read the [docs](https://docs.masumi.network/))
   - Retrieve Agent ID aka Asset ID
   - Check Agent Service variables:
     - `SELLER_VKEY`: vkey (verificatin key) of selling wallet used to register agent, get it from the admin panel of your payment service
     - `PAYMENT_API_KEY`: payment token or admin key for Payment Service (you have used it to login to the admin panel)
     - `PAYMENT_SERVICE_URL`: URL of your Payment Service
     - `OPENAI_API_KEY`: OpenAI API key for gpt-4o-mini model

4. **Test Integration**
   - Start job via Agent Service with text and optional character limit
   - Copy job output (excluding `job_id` and `payment_id`)
   - Go to the `/docs` of your Masumi Payment Service
   - Open POST `/purchase` on Payment Service and paste your job output (this initiates the payment process)
   - Check job status on Agent Service for results

## How to Customize

1. Fork this repository
2. Switch to the langchain branch: `git checkout langchain`
3. Edit `langgraph_service.py` to implement your LangGraph agent logic
4. Modify tools and agent workflow as needed
5. Update `input_schema` in main.py to match your input requirements
6. Run or deploy your customized version using Railway

> **Side note:** Railway can try to deploy public repository without asking for any permissions. To deploy a private repository, you need to connect Railway to your GitHub account or GitHub organisation and grant reading permissions (you will be guided through the process by Railway).

## Local Setup

```bash
cp .env.example .env
# edit .env with your config including OPENAI_API_KEY

uv venv
source .venv/bin/activate
uv pip sync requirements.txt

python get_payment_source_info.py
# add SELLER_VKEY to .env

python main.py api
```

## API Endpoints

### `/start_job` - Start a new summarization job
**POST** request with the following JSON body (Masumi Network Standard):

```json
{
  "input_data": [
    {"key": "input_string", "value": "Your long text to summarize here"},
    {"key": "char_limit", "value": "100"}
  ]
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "payment_id": "payment-identifier"
}
```

### Other Endpoints
- `GET /availability` - Check server status
- `GET /input_schema` - Get input schema definition
- `GET /status?job_id=<id>` - Check job status
- `GET /health` - Health check

## Test

```bash
# basic health checks
curl http://localhost:8000/availability
curl http://localhost:8000/input_schema

# start a summarization job (Masumi Network format)
curl -X POST http://localhost:8000/start_job \
  -H "Content-Type: application/json" \
  -d '{"input_data": [{"key": "input_string", "value": "This is a long text that needs to be summarized. It contains multiple sentences and should be reduced to a shorter form while maintaining the key information."}, {"key": "char_limit", "value": "50"}]}'

# test with default character limit (240)
curl -X POST http://localhost:8000/start_job \
  -H "Content-Type: application/json" \
  -d '{"input_data": [{"key": "input_string", "value": "Your text here"}]}'

# run test suite
uv run python -m pytest test_api.py -v

# test LangGraph service independently
uv run python langgraph_service.py
```

## LangGraph Implementation Details

### Service Architecture
- **Factory Pattern**: `get_agentic_service()` returns `LangGraphService` instance
- **ReAct Agent**: Uses `create_react_agent` with predefined tools
- **State Management**: Maintains conversation state through agent execution
- **Error Handling**: Graceful handling of API failures and edge cases

### Tools Available
1. **`summarize_text`**: Calls gpt-4o-mini with character limit in prompt
2. **`count_characters`**: Counts characters in text strings

### Configuration
- **Model**: gpt-4o-mini (configurable in `langgraph_service.py`)
- **Temperature**: 0.3 (focused responses)
- **Default Character Limit**: 240 characters
- **Customizable**: Character limit can be overridden per request

### Example Usage

```python
from langgraph_service import LangGraphService

service = LangGraphService()

# Basic usage
result = await service.execute_task({
    "input_string": "Your text here"
})

# With custom character limit
result = await service.execute_task({
    "input_string": "Your text here",
    "char_limit": 100
})

print(f"Summary: {result.raw}")
print(f"Character count: {result.json_dict['character_count']}")
print(f"Within limit: {result.json_dict['within_limit']}")
```

## Branch Information

This is the **langchain** branch of the multi-integration repository. Other branches available:
- **main**: Simple text reversal service (zero dependencies)
- **crewai**: CrewAI framework integration
- **langchain**: LangGraph ReAct agent implementation (this branch)

Switch branches to explore different agent frameworks while maintaining Masumi compliance.