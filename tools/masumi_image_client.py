import os
import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

import httpx


class MasumiImageClientError(Exception):
    """Base error for Masumi image client failures."""


def _get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise MasumiImageClientError(f"Missing required environment variable: {name}")
    return value


def _build_image_agent_base_url() -> str:
    base = _get_env("IMAGE_AGENT_BASE_URL")
    return base.rstrip("/")


def _build_payment_base_url() -> str:
    payment_url = os.getenv("IMAGE_PAYMENT_SERVICE_URL") or os.getenv(
        "PAYMENT_SERVICE_URL"
    )
    if not payment_url:
        raise MasumiImageClientError(
            "IMAGE_PAYMENT_SERVICE_URL or PAYMENT_SERVICE_URL must be set"
        )
    return payment_url.rstrip("/")


def _build_network() -> str:
    # Prefer explicit image network, then generic NETWORK, fall back to Preprod
    return os.getenv("IMAGE_NETWORK") or os.getenv("NETWORK") or "Preprod"


def _build_payment_auth() -> Tuple[str, str]:
    """
    Returns (header_name, api_key) for payment auth.

    Defaults to x-api-key header. You can override the header name with
    IMAGE_PAYMENT_API_KEY_HEADER, and the key with IMAGE_PAYMENT_API_KEY.
    """
    api_key = os.getenv("IMAGE_PAYMENT_API_KEY") or os.getenv("PAYMENT_API_KEY")
    if not api_key:
        raise MasumiImageClientError(
            "IMAGE_PAYMENT_API_KEY or PAYMENT_API_KEY must be set for image purchase"
        )
    header_name = os.getenv("IMAGE_PAYMENT_API_KEY_HEADER", "token")
    return header_name, api_key


def _build_ipfs_gateway() -> str:
    gateway = os.getenv("IMAGE_IPFS_GATEWAY") or "https://ipfs.io/ipfs"
    return gateway.rstrip("/")


async def start_image_job(
    prompt: str,
    *,
    identifier_from_purchaser: Optional[str] = None,
    model_type: Optional[str] = None,
    timeout: float = 10.0,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Call the image Masumi agent /start_job endpoint.

    Request body (per user spec):
    {
      "identifier_from_purchaser": "12345671234567",
      "input_data": {
        "model_type": "DALLLE",
        "prompt": "..."
      }
    }
    """
    base_url = _build_image_agent_base_url()
    url = f"{base_url}/start_job"
    identifier = identifier_from_purchaser or os.getenv("IMAGE_IDENTIFIER_FROM_PURCHASER")

    if not identifier:
        # fall back to a deterministic-but-simple identifier if caller didn't provide one
        # and env is missing; use uuid-style randomness via httpx's built-in secrets
        import uuid

        identifier = "12345671234567"

    payload = {
        "identifier_from_purchaser": identifier,
        "input_data": {
            "model_type": model_type or os.getenv("IMAGE_AGENT_MODEL_TYPE", "DALLE"),
            "prompt": prompt,
        },
    }

    if logger:
        logger.info("Starting Masumi image job at %s", url)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)

    if resp.status_code >= 400:
        raise MasumiImageClientError(
            f"Image /start_job failed ({resp.status_code}): {resp.text}"
        )

    data = resp.json()
    if logger:
        logger.debug("Image /start_job response: %s", data)
    if "job_id" not in data:
        raise MasumiImageClientError("Image /start_job response missing job_id")
    return data


async def trigger_purchase(
    start_job_response: Dict[str, Any],
    *,
    timeout: float = 10.0,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Call the Masumi Payment Service /purchase endpoint using the payload
    returned by the image agent /start_job.
    """
    payment_base = _build_payment_base_url()
    url = f"{payment_base}/purchase"
    header_name, api_key = _build_payment_auth()

    identifier_from_purchaser = (
        start_job_response.get("identifierFromPurchaser")
        or start_job_response.get("identifier_from_purchaser")
    )
    blockchain_identifier = start_job_response.get("blockchainIdentifier")
    seller_vkey = start_job_response.get("sellerVKey")
    agent_identifier = start_job_response.get("agentIdentifier")
    pay_by_time = start_job_response.get("payByTime")
    submit_result_time = start_job_response.get("submitResultTime")
    unlock_time = start_job_response.get("unlockTime")
    external_dispute_unlock_time = start_job_response.get(
        "externalDisputeUnlockTime"
    )
    input_hash = start_job_response.get("inputHash") or start_job_response.get(
        "input_hash"
    )

    missing_fields = [
        name
        for name, value in {
            "identifierFromPurchaser": identifier_from_purchaser,
            "blockchainIdentifier": blockchain_identifier,
            "sellerVkey": seller_vkey,
            "agentIdentifier": agent_identifier,
            "payByTime": pay_by_time,
            "submitResultTime": submit_result_time,
            "unlockTime": unlock_time,
            "externalDisputeUnlockTime": external_dispute_unlock_time,
            "inputHash": input_hash,
        }.items()
        if value is None
    ]
    if missing_fields:
        raise MasumiImageClientError(
            f"Image /start_job response missing fields required for /purchase: {', '.join(missing_fields)}"
        )

    network = _build_network()
    purchase_payload = {
        "identifierFromPurchaser": identifier_from_purchaser,
        "network": network,
        "sellerVkey": seller_vkey,
        "blockchainIdentifier": blockchain_identifier,
        "payByTime": pay_by_time,
        "submitResultTime": submit_result_time,
        "unlockTime": unlock_time,
        "externalDisputeUnlockTime": external_dispute_unlock_time,
        "agentIdentifier": agent_identifier,
        "inputHash": input_hash,
    }

    headers = {header_name: api_key}
    if logger:
        logger.info("Triggering Masumi image purchase at %s", url)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=purchase_payload, headers=headers)

    if resp.status_code >= 400:
        raise MasumiImageClientError(
            f"Payment /purchase failed ({resp.status_code}): {resp.text}"
        )

    data = resp.json()
    if logger:
        logger.debug("Payment /purchase response: %s", data)
    return data


async def wait_for_image_result(
    job_id: str,
    *,
    poll_interval_seconds: float = 60.0,
    max_polls: int = 60,
    timeout: float = 10.0,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Poll the image agent /status endpoint until status == \"completed\" or timeout.

    Example response:
    {
      \"job_id\": \"...\",
      \"status\": \"completed\",
      \"payment_status\": \"completed\",
      \"result\": \"<ipfs-hash>\"
    }
    """
    base_url = _build_image_agent_base_url()
    url = f"{base_url}/status"

    last_response: Optional[Dict[str, Any]] = None

    for attempt in range(1, max_polls + 1):
        params = {"job_id": job_id}
        if logger:
            logger.info(
                "Polling Masumi image status (attempt %s/%s) for job %s",
                attempt,
                max_polls,
                job_id,
            )

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params=params)

        if resp.status_code >= 400:
            raise MasumiImageClientError(
                f"Image /status failed ({resp.status_code}): {resp.text}"
            )

        data = resp.json()
        last_response = data
        status = data.get("status")
        payment_status = data.get("payment_status")

        if status == "completed":
            if logger:
                logger.info(
                    "Masumi image job %s completed with payment status %s",
                    job_id,
                    payment_status,
                )
            return data

        if status == "failed":
            raise MasumiImageClientError(
                f"Masumi image job {job_id} failed with status payload: {data}"
            )

        await asyncio.sleep(poll_interval_seconds)

    raise MasumiImageClientError(
        f"Masumi image job {job_id} did not complete within poll limit; last response={last_response}"
    )


async def generate_image_with_masumi(
    prompt: str,
    *,
    identifier_from_purchaser: Optional[str] = None,
    poll_interval_seconds: float = 60.0,
    max_polls: int = 60,
    http_timeout: float = 60.0,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    High-level helper that orchestrates:
      1) image agent /start_job
      2) payment service /purchase
      3) polling image /status until completion

    Returns a dict:
    {
      \"job_id\": \"...\",
      \"ipfs_hash\": \"<hash>\",
      \"image_ipfs_url\": \"<gateway>/<hash>\",
      \"raw_status\": { ...full /status payload... }
    }
    """
    start_resp = await start_image_job(
        prompt,
        identifier_from_purchaser=identifier_from_purchaser,
        timeout=http_timeout,
        logger=logger,
    )
    await trigger_purchase(start_resp, timeout=http_timeout, logger=logger)
    job_id = start_resp["job_id"]
    status_resp = await wait_for_image_result(
        job_id,
        poll_interval_seconds=poll_interval_seconds,
        max_polls=max_polls,
        timeout=http_timeout,
        logger=logger,
    )

    ipfs_hash = status_resp.get("result")
    gateway = _build_ipfs_gateway()
    image_url = f"{gateway}/{ipfs_hash}" if ipfs_hash else None

    return {
        "job_id": job_id,
        "ipfs_hash": ipfs_hash,
        "image_ipfs_url": image_url,
        "raw_status": status_resp,
    }


