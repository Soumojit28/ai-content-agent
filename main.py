import os
from dotenv import load_dotenv

# Load environment variables FIRST before any other imports
# This ensures env vars are available when graph.py is imported
load_dotenv(override=True)

import uvicorn
import uuid
import time
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from masumi.config import Config
from masumi.payment import Payment
from agentic_service import get_agentic_service
from logging_config import setup_logging
import cuid2
import logging

#region congif
# Configure logging
logger = setup_logging(log_level=logging.DEBUG)

# Retrieve API Keys and URLs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "")
PAYMENT_API_KEY = os.getenv("PAYMENT_API_KEY", "")
NETWORK = os.getenv("NETWORK", "preview")

logger.info("Starting application with configuration:")
logger.info(f"PAYMENT_SERVICE_URL: {PAYMENT_SERVICE_URL}")

# validate critical environment variables at startup
def validate_url(url: str, name: str) -> str:
    """Validate that a URL is properly formatted"""
    if not url:
        return f"{name} is not set"
    
    # check if it starts with http:// or https://
    if not url.startswith(('http://', 'https://')):
        return f"{name} must start with 'https://' or 'http://' (got: '{url}')"
    
    # parse URL to check if it's valid
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return f"{name} is not a valid URL format (got: '{url}')"
    except Exception:
        return f"{name} is not a valid URL format (got: '{url}')"
    
    return ""  # no error

def validate_environment():
    """Validate that all required environment variables are set"""
    errors = []
    
    agent_id = os.getenv("AGENT_IDENTIFIER", "").strip()
    if not agent_id:
        errors.append("AGENT_IDENTIFIER is not set")
    elif agent_id == "REPLACE":
        errors.append("AGENT_IDENTIFIER is set to placeholder 'REPLACE' - please set a real agent identifier")
    
    # validate payment service URL format
    url_error = validate_url(PAYMENT_SERVICE_URL, "PAYMENT_SERVICE_URL")
    if url_error:
        errors.append(url_error)
    
    if not PAYMENT_API_KEY:
        errors.append("PAYMENT_API_KEY is not set")
    
    if not NETWORK:
        errors.append("NETWORK is not set")
    
    if errors:
        logger.error("Critical environment variable validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("Please fix these configuration issues before starting the server")
        return False
    
    logger.info("Environment validation passed")
    return True

# run validation but don't fail startup (for debugging)
validation_passed = validate_environment()
if not validation_passed:
    logger.warning("Starting server despite configuration errors - some endpoints may not work properly")

# Initialize FastAPI
app = FastAPI(
    title="API following the Masumi API Standard",
    description="Masumi-compliant agent service with payment integration",
    version="1.0.0"
)

# ─────────────────────────────────────────────────────────────────────────────
#region Temporary in-memory job store 
# DO NOT USE IN PRODUCTION)
# ─────────────────────────────────────────────────────────────────────────────
jobs = {}
payment_instances = {}

# track server start time for uptime calculation
server_start_time = time.time()

# ─────────────────────────────────────────────────────────────────────────────
#region Initialize Masumi Payment Config
# ─────────────────────────────────────────────────────────────────────────────
# config will be created in start_job to allow proper validation

# ─────────────────────────────────────────────────────────────────────────────
#region Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────
class InputDataItem(BaseModel):
    key: str
    value: str

class StartJobRequest(BaseModel):
    input_data: dict[str, str]
    identifier_from_purchaser: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "identifier_from_purchaser": "12345671234567",
                "input_data": {
                    "topic": "Use of Masumi Network for Decentralized AI Agents",
                    "tone": "pragmatic",
                    "platform": "linkedin",
                    "keywords": "Masumi Network, Cardano",
                    "link": "https://masumi.network"
                }
            }
        }

class ProvideInputRequest(BaseModel):
    job_id: str

# ─────────────────────────────────────────────────────────────────────────────
#region Task Execution THIS IS THE MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
async def execute_agentic_task(input_data: dict) -> object:
    """ Execute task """
    logger.info(f"starting task with input: {input_data}")
    service = get_agentic_service(logger=logger)
    result = await service.execute_task(input_data)
    logger.info("task completed successfully")
    return result

# ─────────────────────────────────────────────────────────────────────────────
#region 1) Start Job (MIP-003: /start_job)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/start_job")
async def start_job(data: StartJobRequest):
    """ Initiates a job and creates a payment request """
    print(f"Received data: {data}")
    print(f"Received data.input_data: {data.input_data}")
    try:
        job_id = str(uuid.uuid4())
        
        # validate required environment variables
        agent_identifier = os.getenv("AGENT_IDENTIFIER", "").strip()
        if not agent_identifier or agent_identifier == "REPLACE":
            logger.error("AGENT_IDENTIFIER environment variable is missing or set to placeholder 'REPLACE'")
            raise HTTPException(
                status_code=500,
                detail="Server configuration error: AGENT_IDENTIFIER not properly configured. Please contact administrator."
            )
        
        # validate payment service URL format
        url_error = validate_url(PAYMENT_SERVICE_URL, "PAYMENT_SERVICE_URL")
        if url_error:
            logger.error(f"PAYMENT_SERVICE_URL validation failed: {url_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Server configuration error: {url_error}. Please contact administrator."
            )
            
        if not PAYMENT_API_KEY:
            logger.error("PAYMENT_API_KEY environment variable is missing")
            raise HTTPException(
                status_code=500,
                detail="Server configuration error: PAYMENT_API_KEY not configured. Please contact administrator."
            )
        
        # generate identifier_from_purchaser internally using cuid2
        identifier_from_purchaser = data.identifier_from_purchaser
        logger.info(f"Generated identifier_from_purchaser: {identifier_from_purchaser}")
        
        # convert input_data array to dict for internal processing
        content_payload = data.input_data
        
        logger.info(
            "Received content job topic='%s' tone='%s' platform='%s'",
            content_payload["topic"][:80],
            content_payload["tone"],
            content_payload["platform"],
        )
        logger.info(f"Starting job {job_id} with agent {agent_identifier}")

        # Define payment amounts
        payment_amount = int(os.getenv("PAYMENT_AMOUNT", "1000000"))  # 1 ADA
        payment_unit = os.getenv("PAYMENT_UNIT", "lovelace") # Default lovelace

        logger.info(f"Using payment amount: {payment_amount} {payment_unit}")
        
        # create config after validation
        config = Config(
            payment_service_url=PAYMENT_SERVICE_URL,
            payment_api_key=PAYMENT_API_KEY
        )
        
        # Create a payment request using Masumi
        payment = Payment(
            agent_identifier=agent_identifier,
            #amounts=amounts,
            config=config,
            identifier_from_purchaser=identifier_from_purchaser,
            input_data=content_payload,
            network=NETWORK
            
        )
        
        logger.info("Creating payment request...")
        payment_request = await payment.create_payment_request()
        blockchain_identifier = payment_request["data"]["blockchainIdentifier"]
        payment.payment_ids.add(blockchain_identifier)
        logger.info(f"Created payment request with blockchain identifier: {blockchain_identifier}")

        # Store job info (Awaiting payment)
        jobs[job_id] = {
            "status": "awaiting_payment",
            "payment_status": "pending",
            "blockchain_identifier": blockchain_identifier,
            "input_data": data.input_data,
            "result": None,
            "identifier_from_purchaser": data.identifier_from_purchaser
        }

        async def payment_callback(blockchain_identifier: str):
            await handle_payment_status(job_id, blockchain_identifier)

        # Start monitoring the payment status
        payment_instances[job_id] = payment
        logger.info(f"Starting payment status monitoring for job {job_id}")
        await payment.start_status_monitoring(payment_callback)

        # Return the response in the required format
        return {
            "status": "success",
            "job_id": job_id,
            "blockchainIdentifier": blockchain_identifier,
            "submitResultTime": payment_request["data"]["submitResultTime"],
            "unlockTime": payment_request["data"]["unlockTime"],
            "externalDisputeUnlockTime": payment_request["data"]["externalDisputeUnlockTime"],
            "agentIdentifier": agent_identifier,
            "sellerVKey": os.getenv("SELLER_VKEY"),
            "identifierFromPurchaser": data.identifier_from_purchaser,
            # "amounts": amounts,
            "input_hash": payment.input_hash,
            "payByTime": payment_request["data"]["payByTime"],
        }
    except KeyError as e:
        logger.error(f"Missing required field in request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Bad Request: If input_data or identifier_from_purchaser is missing, invalid, or does not adhere to the schema."
        )
    except Exception as e:
        logger.error(f"Error in start_job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Input_data or identifier_from_purchaser is missing, invalid, or does not adhere to the schema."
        )

# ─────────────────────────────────────────────────────────────────────────────
#region 2) Process Payment and Execute AI Task
# ─────────────────────────────────────────────────────────────────────────────
async def handle_payment_status(job_id: str, payment_id: str) -> None:
    """ Executes task after payment confirmation """
    try:
        logger.info(f"Payment {payment_id} completed for job {job_id}, executing task...")
        
        # Update job status to running
        jobs[job_id]["status"] = "running"
        input_data = jobs[job_id]["input_data"]
        
        # Process keywords if it's a string
        if isinstance(input_data.get("keywords"), str):
            input_data["keywords"] = [k.strip() for k in input_data["keywords"].split(",")]
        
        logger.info(f"Input data: {input_data}")

        # Execute the AI task
        result = await execute_agentic_task(input_data)
        print(f"Result: {result}")
        result_dict = result.json_dict  # type: ignore
        logger.info(f"task completed for job {job_id}")
        
        # Mark payment as completed on Masumi
        # Use a shorter string for the result hash
        await payment_instances[job_id].complete_payment(payment_id, result_dict)
        logger.info(f"Payment completed for job {job_id}")

        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["payment_status"] = "completed"
        jobs[job_id]["result"] = result

        # Stop monitoring payment status
        if job_id in payment_instances:
            payment_instances[job_id].stop_status_monitoring()
            del payment_instances[job_id]
    except Exception as e:
        logger.error(f"Error processing payment {payment_id} for job {job_id}: {str(e)}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        
        # Still stop monitoring to prevent repeated failures
        if job_id in payment_instances:
            payment_instances[job_id].stop_status_monitoring()
            del payment_instances[job_id]

# ─────────────────────────────────────────────────────────────────────────────
#region 3) Check Job and Payment Status (MIP-003: /status)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/status")
async def get_status(job_id: str):
    """ Retrieves the current status of a specific job """
    logger.info(f"Checking status for job {job_id}")
    if job_id not in jobs:
        logger.warning(f"Job {job_id} not found")
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Check latest payment status if payment instance exists
    if job_id in payment_instances:
        try:
            status = await payment_instances[job_id].check_payment_status()
            job["payment_status"] = status.get("data", {}).get("status")
            logger.info(f"Updated payment status for job {job_id}: {job['payment_status']}")
        except ValueError as e:
            logger.warning(f"Error checking payment status: {str(e)}")
            job["payment_status"] = "unknown"
        except Exception as e:
            logger.error(f"Error checking payment status: {str(e)}", exc_info=True)
            job["payment_status"] = "error"


    result_data = job.get("result")
    result = result_data.json_dict if result_data and hasattr(result_data, "json_dict") else None

    return {
        "job_id": job_id,
        "status": job["status"],
        "payment_status": job["payment_status"],
        "result": result
    }

# ─────────────────────────────────────────────────────────────────────────────
#region 4) Check Server Availability (MIP-003: /availability)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/availability")
async def check_availability():
    """ Checks if the server is operational """
    current_time = time.time()
    uptime_seconds = int(current_time - server_start_time)
    
    return {
        "status": "available", 
        "uptime": uptime_seconds,
        "message": "Server operational."
    }

# ─────────────────────────────────────────────────────────────────────────────
#region 5) Retrieve Input Schema (MIP-003: /input_schema)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/input_schema")
async def input_schema():
    """
    Returns the expected input schema for the /start_job endpoint.
    Fulfills MIP-003 /input_schema endpoint.
    """
    return {
        "input_data": [
        {
        "id": "topic",
        "type": "string",
        "name": "Topic",
            "data": {
                "description": "The topic of the article",
                "placeholder": "Use of Masumi Network for Decentralized AI Agents"
            }
        },
        {
            "id": "tone",
            "type": "string",
            "name": "Tone",
            "data": {
                "description": "The tone of the article",
                "placeholder": "pragmatic"
            }
        },
        {
            "id": "platform",
            "type": "string",
            "name": "Platform",
            "data": {
                "description": "The platform of the article",
                "placeholder": "linkedin"
            }
        },
        {
            "id": "keywords",
            "type": "string",
            "name": "Keywords",
            "data": {
                "description": "The keywords of the article",
                "placeholder": "Masumi Network, Cardano"
            }
        },
        {
            "id": "link",
            "type": "string",
            "name": "Link",
            "data": {
                "description": "The link of the article",
                "placeholder": "https://masumi.network"
            }
        }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
#region 6) Health Check
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """
    Returns the health of the server.
    """
    return {
        "status": "healthy"
    }

# ─────────────────────────────────────────────────────────────────────────────
#region Main Logic if Called as a Script
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("Running task as standalone script is not supported when using payments.")
    print("Start the API using `python main.py api` instead.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        print("Starting FastAPI server with Masumi integration...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        main()
