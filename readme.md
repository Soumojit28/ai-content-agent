# Masumi Agent Service

## 🧠 LangGraph Multi-Agent Content Creation

This service demonstrates a **multi-agent LangGraph workflow** that researches a topic with SerpAPI, drafts a LinkedIn/X-ready post with optional AI-generated images, and proposes hashtags. It's a production-ready content composer integrated with the Masumi Network.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT / USER                                  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ POST /start_job
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI SERVER (main.py)                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  MIP-003 Endpoints: /start_job, /status, /availability, etc.    │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
│                                │                                         │
│                                │ Creates Payment Request                 │
│                                ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │           Masumi Payment Service Integration                     │  │
│  │  - Create payment request via Payment API                        │  │
│  │  - Monitor payment status (polling)                              │  │
│  │  - Complete payment after job execution                          │  │
│  └────────────────────────────┬─────────────────────────────────────┘  │
└─────────────────────────────────┼─────────────────────────────────────┘
                                  │
                                  │ Payment Confirmed
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   LANGGRAPH SERVICE (langgraph_service.py)              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    ContentGraph (graph.py)                       │  │
│  │                                                                  │  │
│  │   ┌───────────────┐      ┌────────────────┐                    │  │
│  │   │ fetch_snippets│─────▶│ synthesize     │                    │  │
│  │   │   (SerpAPI)   │      │   research     │                    │  │
│  │   └───────────────┘      └────────┬───────┘                    │  │
│  │                                   │                             │  │
│  │                                   ▼                             │  │
│  │                          ┌────────────────┐                     │  │
│  │                          │ generate_copy  │                     │  │
│  │                          │  (Copywriter)  │                     │  │
│  │                          └────────┬───────┘                     │  │
│  │                                   │                             │  │
│  │                                   ▼                             │  │
│  │                          ┌────────────────┐                     │  │
│  │                          │generate_image  │◄────────┐           │  │
│  │                          │  (Optional)    │         │           │  │
│  │                          └────────┬───────┘         │           │  │
│  │                                   │                 │           │  │
│  │                                   ▼                 │           │  │
│  │                          ┌────────────────┐         │           │  │
│  │                          │generate        │         │           │  │
│  │                          │ hashtags       │         │           │  │
│  │                          └────────────────┘         │           │  │
│  └──────────────────────────────────────────────────────┼───────────┘  │
└─────────────────────────────────────────────────────────┼─────────────┘
                                                          │
                ┌─────────────────────────────────────────┼─────────────┐
                │                                         │             │
                │                                         │             │
                ▼                                         ▼             │
    ┌───────────────────────┐              ┌──────────────────────────┐│
    │   External Services   │              │  Masumi Image Agent      ││
    │                       │              │  (Optional)              ││
    │  • SerpAPI (search)   │              │  - AI image generation   ││
    │  • OpenAI (LLM)       │              │  - IPFS storage          ││
    │  • Blockfrost         │              │  - Payment integration   ││
    └───────────────────────┘              └──────────────────────────┘│
                                                                        │
                                                                        │
                                          Returns: IPFS hash + URL ────┘

Legend:
  ──▶  Data flow
  ◄──  Optional callback/integration
```

### Key Features

- **SerpAPI Research Tool**: Fetches fresh public insights for the topic + optional keywords/link.
- **Copywriting Agent**: Tailors tone + platform, stitches insights, and emits CTA-ready copy with optional image prompts.
- **AI Image Generation**: Optional integration with Masumi image agents for AI-generated visuals via IPFS.
- **Hashtag Agent**: Generates ordered hashtags with rationale for reach planning.
- **Config-Driven Prompts**: `config/content_agent.yml` centralizes prompts + API settings.
- **Full Masumi Compliance**: All MIP-003 endpoints implemented and tested.

## Prerequisites

- [Blockfrost](https://blockfrost.io/) API key (for Cardano blockchain interaction)
- **OpenAI API key** (for gpt-4o-mini model)
- **SerpAPI key** (optional, for search functionality)
- (Optional) Masumi image agent service for AI image generation
- For quick deployment: [Railway account](https://railway.com?referralCode=pa1ar)

## Quick Start - Railway Deployment

> This guide assumes familiarity with [Masumi Network](https://masumi.network/). If you're new, check the [official docs](https://docs.masumi.network/) first.

### 1. Deploy Masumi Payment Service

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/masumi-payment-service-official?referralCode=padierfind)

- Provide Blockfrost API key when prompted
- Wait 5+ minutes for deployment
- Generate public URL: Settings > Networking > Generate URL
- Test at `/admin` and `/docs` endpoints
- **Important**: Remember to append `/api/v1` to the URL when using it in next steps

### 2. Deploy This Agent Service

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/masumi-compliant-service-api-official?referralCode=padierfind)

Required environment variables:
- `PAYMENT_SERVICE_URL` - Your payment service URL with `/api/v1` suffix
- `OPENAI_API_KEY` - Your OpenAI API key
- `SERPAPI_KEY` - (Optional) Your SerpAPI key for search
- `AGENT_IDENTIFIER` - Will be set after registering the agent
- `SELLER_VKEY` - Get from payment service admin panel
- `PAYMENT_API_KEY` - Your payment service API key

### 3. Register Your Agent

1. Top up your selling wallet via Payment Service admin panel
2. Register agent using the agent service URL (requires funds)
3. Retrieve the Agent ID (Asset ID)
4. Update `AGENT_IDENTIFIER` in agent service variables
5. Test via `/docs` endpoint

## Local Development

### Setup

```bash
# Clone and setup environment
cp .env.example .env
# Edit .env with OPENAI_API_KEY, SERPAPI_KEY, etc.

# Install dependencies
uv venv
source .venv/bin/activate
uv pip sync requirements.txt

# Get seller verification key
python get_payment_source_info.py
# Add SELLER_VKEY to .env

# Start the server
python main.py api
```

### Environment Variables

Required:
- `OPENAI_API_KEY` - OpenAI API key for LLM
- `PAYMENT_SERVICE_URL` - Masumi payment service URL (with `/api/v1`)
- `PAYMENT_API_KEY` - Payment service API key
- `AGENT_IDENTIFIER` - Your registered agent's asset ID
- `SELLER_VKEY` - Seller verification key
- `NETWORK` - Network name (e.g., `Preprod` or `Mainnet`)

Optional:
- `SERPAPI_KEY` - SerpAPI key for web search (can also be set in config YAML)
- `PAYMENT_AMOUNT` - Payment amount in lovelace (default: 1000000)
- `PAYMENT_UNIT` - Payment unit (default: lovelace)

### Optional: Image Generation

To enable AI image generation via a separate Masumi image agent:

Environment Variables:
- `IMAGE_AGENT_BASE_URL` - Base URL of image agent service
- `IMAGE_AGENT_MODEL_TYPE` - Model type (default: `OPENAI`)
- `IMAGE_PAYMENT_SERVICE_URL` - Payment service for images (falls back to `PAYMENT_SERVICE_URL`)
- `IMAGE_PAYMENT_API_KEY` - API key for image payments (falls back to `PAYMENT_API_KEY`)
- `IMAGE_NETWORK` - Network for image purchases (falls back to `NETWORK`)
- `IMAGE_IPFS_GATEWAY` - IPFS gateway URL (e.g., `https://ipfs.io/ipfs`)

The copywriter agent can generate `image_prompt` fields, which trigger automatic image generation, payment, and IPFS storage. Results include `image_ipfs_hash` and `image_ipfs_url` in the job output.

## Customization

### Modify Agent Behavior

1. **Edit Prompts**: Update `config/content_agent.yml` to customize agent prompts and settings
2. **Modify Workflow**: Edit `graph.py` to add/remove/reorder graph nodes
3. **Change Agents**: Update implementations in `agents/` directory
4. **Add Tools**: Create new integrations in `tools/` directory
5. **Update Schema**: Modify `input_schema` in `main.py` for different inputs

### Configuration File

`config/content_agent.yml` controls:
- OpenAI model and temperature
- SerpAPI settings (key, engine, location, language, result count)
- Agent prompts for research, copywriting, and hashtags
- Default settings like emoji usage

Environment variable `SERPAPI_KEY` overrides the YAML value for security.

## API Endpoints

### `/start_job` - Start a new content job
**POST** request with the following JSON body:

```json
{
  "identifier_from_purchaser": "unique-purchaser-id",
  "input_data": {
    "topic": "Masumi Decentralized AI agents",
    "tone": "pragmatic",
    "platform": "linkedin",
    "keywords": "AI Agents, Cardano",
    "link": "https://masumi.network"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "job_id": "uuid-string",
  "blockchainIdentifier": "blockchain-id",
  "submitResultTime": "2024-01-01T00:00:00Z",
  "unlockTime": "2024-01-01T01:00:00Z",
  "externalDisputeUnlockTime": "2024-01-01T02:00:00Z",
  "agentIdentifier": "agent-asset-id",
  "sellerVKey": "seller-verification-key",
  "identifierFromPurchaser": "unique-purchaser-id",
  "input_hash": "hash-of-input-data",
  "payByTime": "2024-01-01T00:30:00Z"
}
```

### Other Endpoints
- `GET /availability` - Check server status and uptime
- `GET /input_schema` - Get input schema definition (MIP-003 compliant)
- `GET /status?job_id=<id>` - Check job status and retrieve results
- `GET /health` - Health check endpoint

## Testing

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/availability

# Get input schema
curl http://localhost:8000/input_schema

# Start a content job
curl -X POST http://localhost:8000/start_job \
  -H "Content-Type: application/json" \
  -d '{
    "identifier_from_purchaser": "test-user-123",
    "input_data": {
      "topic": "Masumi Decentralized AI agents",
      "tone": "pragmatic",
      "platform": "linkedin",
      "keywords": "AI Agents, Cardano",
      "link": "https://masumi.network"
    }
  }'

# Check job status
curl "http://localhost:8000/status?job_id=<your-job-id>"

# Run test suite
uv run python -m pytest test_api.py -v

# Test LangGraph service independently
uv run python test_content_agent.py
```

## Project Structure

```
ai-content-agent/
├── agents/                     # Agent implementations
│   ├── copywriter.py          # LinkedIn/X copywriting agent
│   ├── hashtags.py            # Hashtag generation agent
│   ├── research.py            # Research synthesis agent
│   └── utils.py               # Shared agent utilities
├── config/                     # Configuration files
│   ├── content_agent.py       # Config loader
│   └── content_agent.yml      # Agent prompts and settings
├── tools/                      # External service integrations
│   ├── serp_client.py         # SerpAPI integration
│   └── masumi_image_client.py # Masumi image agent client
├── agentic_service.py         # Service factory pattern
├── graph.py                   # LangGraph workflow definition
├── langgraph_service.py       # Main service implementation
├── main.py                    # FastAPI server + Masumi integration
├── state.py                   # Shared state TypedDict
├── logging_config.py          # Logging configuration
└── requirements.txt           # Python dependencies
```

## Implementation Details

### LangGraph Workflow

The service uses LangGraph's StateGraph to orchestrate a multi-agent pipeline:

1. **fetch_snippets** - SerpAPI client fetches web search results
2. **synthesize_research** - Research agent analyzes and summarizes findings
3. **generate_copy** - Copywriting agent creates platform-specific content
4. **generate_image** - (Optional) Masumi image agent generates visuals
5. **generate_hashtags** - Hashtag agent proposes strategic tags

State flows through the graph using a shared TypedDict (`state.State`), maintaining topic, tone, platform, insights, post content, and metadata.

### Service Factory

`get_agentic_service()` in `agentic_service.py` returns `LangGraphService`, which:
- Loads configuration from `config/content_agent.yml`
- Initializes all agents and tools
- Builds the ContentGraph workflow
- Executes tasks and returns `ServiceResult` objects

### Example Usage

```python
from langgraph_service import LangGraphService

service = LangGraphService()
result = await service.execute_task({
    "topic": "Masumi Decentralized AI agents",
    "tone": "pragmatic",
    "platform": "linkedin",
    "keywords": ["AI Agents", "Cardano"],
    "link": "https://masumi.network"
})

print(result.raw)  # Post body
print(result.json_dict["hashtags"])  # Generated hashtags
print(result.json_dict["insights"])  # Research insights
```
