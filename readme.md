# Masumi Agent Service

## 🧠 LangGraph Multi-Agent Content Creation

This service demonstrates a **multi-agent LangGraph workflow** that researches a topic with SerpAPI, drafts a LinkedIn/X-ready post with optional AI-generated images, and proposes hashtags. It's a production-ready content composer integrated with the Masumi Network.

### Key Features

- **SerpAPI Research Tool**: Fetches fresh public insights for the topic + optional keywords/link.
- **Copywriting Agent**: Tailors tone + platform, stitches insights, and emits CTA-ready copy with optional image prompts.
- **AI Image Generation**: Optional integration with Masumi image agents for AI-generated visuals via IPFS.
- **Hashtag Agent**: Generates ordered hashtags with rationale for reach planning.
- **Config-Driven Prompts**: `config/content_agent.yml` centralizes prompts + API settings.
- **Full Masumi Compliance**: All MIP-003 endpoints implemented and tested.

### Agent Workflow

1. **Input Processing**: Topic, tone, platform, keywords, optional link/audience.
2. **Research**: SerpAPI pulls snippets, research agent distills insights + summary.
3. **Copywriting**: Copy agent turns insights into a LinkedIn/X-style post + rationale, optionally generating image prompts.
4. **Image Generation**: If image prompt is provided by copywriter, calls Masumi image agent to generate and store image on IPFS.
5. **Hashtags**: Hashtag agent outputs a ranked list plus justification.
6. **Output**: Job result JSON contains post body, headline, hashtags, insights, optional image URLs, and metadata.

### Prerequisites

- [Blockfrost](https://blockfrost.io/) API key
- **OpenAI API key** (for gpt-4o-mini model)
- **SerpAPI key** (optional, for search functionality)
- For quick deployment: [Railway account](https://railway.com?referralCode=pa1ar) (free trial is 30 days or $5)
- (Optional) Masumi image agent service for AI image generation

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
2. Edit `langgraph_service.py` to implement your LangGraph agent logic
3. Modify tools and agent workflow in `graph.py` as needed
4. Update `input_schema` in `main.py` to match your input requirements
5. Adjust agent prompts in `config/content_agent.yml`
6. Run or deploy your customized version using Railway

> **Side note:** Railway can try to deploy public repository without asking for any permissions. To deploy a private repository, you need to connect Railway to your GitHub account or GitHub organisation and grant reading permissions (you will be guided through the process by Railway).

## Local Setup

```bash
cp .env.example .env
# edit .env with your config including OPENAI_API_KEY and SERPAPI_KEY

uv venv
source .venv/bin/activate
uv pip sync requirements.txt

python get_payment_source_info.py
# add SELLER_VKEY to .env

python main.py api
```

### Optional: Masumi Image Agent Integration

To enable AI image generation via a separate Masumi-compliant image agent + payment service:

**Environment Variables:**

- **IMAGE_AGENT_BASE_URL**: Base URL of the image agent service (used for `/start_job` and `/status`).
- **IMAGE_AGENT_MODEL_TYPE**: Optional model type for the image agent, defaults to `OPENAI`.
- **IMAGE_PAYMENT_SERVICE_URL**: (Optional) Payment service base URL for image jobs; if not set, falls back to `PAYMENT_SERVICE_URL`.
- **IMAGE_PAYMENT_API_KEY**: (Optional) API key for image purchases; if not set, falls back to `PAYMENT_API_KEY`.
- **IMAGE_PAYMENT_API_KEY_HEADER**: HTTP header name carrying the payment API key, defaults to `x-api-key`.
- **IMAGE_NETWORK**: Network name for image purchases (e.g. `Preprod`); if not set, falls back to `NETWORK` or `Preprod`.
- **IMAGE_IPFS_GATEWAY**: IPFS gateway base (e.g. `https://ipfs.io/ipfs`) used to construct a URL from the returned IPFS hash.

**How it works:**

1. The copywriting agent generates an `image_prompt` field in the post.
2. The graph's `generate_image` node calls the Masumi image agent's `/start_job` endpoint.
3. Payment is automatically processed via the configured payment service.
4. The system polls `/status` until the image is ready.
5. Final output includes `image_ipfs_hash`, `image_ipfs_url`, and `image_job` metadata.

If image generation fails, the text workflow continues and the error is captured in `image_error` field.

## API Endpoints

### `/start_job` - Start a new content job
**POST** request with the following JSON body (Masumi Network Standard):

```json
{
  "input_data": [
    {"key": "topic", "value": "AI copilots for RevOps"},
    {"key": "tone", "value": "pragmatic"},
    {"key": "platform", "value": "linkedin"},
    {"key": "keywords", "value": "RevOps,playbooks"},
    {"key": "link", "value": "https://example.com/deck.pdf"}
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

# start a content job (Masumi Network format)
curl -X POST http://localhost:8000/start_job \
  -H "Content-Type: application/json" \
  -d '{"input_data": [
        {"key": "topic", "value": "Masumi Decentralized AI agents"},
        {"key": "tone", "value": "pragmatic"},
        {"key": "platform", "value": "linkedin"},
        {"key": "keywords", "value": "Ai Agents, Cardano"},
        {"key": "link", "value": "https://masumi.network"}
      ]}'

# run test suite
uv run python -m pytest test_api.py -v

# test LangGraph service independently
uv run python langgraph_service.py
```

## LangGraph Implementation Details

### Service Architecture
- **Factory Pattern**: `get_agentic_service()` returns `LangGraphService`
- **Graph Nodes**:
  1. `fetch_snippets` → SerpAPI client gathers public context.
  2. `synthesize_research` → LLM distills snippets into insights.
  3. `generate_copy` → copywriter agent crafts the LinkedIn/X post.
  4. `generate_image` → (Optional) Masumi image agent generates visuals from copywriter's image prompt.
  5. `generate_hashtags` → hashtag agent proposes tags + rationale.
- **State Management**: Shared `state.State` TypedDict keeps topic, tone, insights, post, images, and hashtags organized.

### Configuration
- Edit `config/content_agent.yml` (or set `CONTENT_AGENT_CONFIG`) to control:
  - SerpAPI key + search defaults.
  - OpenAI model/temperature.
  - Prompt text for research, copywriting, and hashtags.
  - Image generation settings.
- `SERPAPI_KEY` env var overrides the YAML value for secrets-only deploys.

### Example Usage

```python
from langgraph_service import LangGraphService

service = LangGraphService()

payload = {
    "topic": "AI copilots for RevOps",
    "tone": "pragmatic",
    "platform": "linkedin",
    "keywords": ["RevOps", "playbooks"],
    "link": "https://example.com/deck.pdf"
}

result = await service.execute_task(payload)
print(result.raw)  # final post body
print(result.json_dict["hashtags"])
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
└── requirements.txt           # Python dependencies
```
