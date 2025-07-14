#!/usr/bin/env python3
"""
N8N Workflow Replica Script
Replicates the exact n8n paywall workflow as functions to debug timing issues.
"""

import hashlib
import json
import os
import requests
import secrets
import time
from datetime import datetime
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration (matches n8n variables)
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "https://your-payment-service-url/api/v1")
PAYMENT_API_KEY = os.getenv("PAYMENT_API_KEY", "your-payment-api-key")
AGENT_IDENTIFIER = os.getenv("AGENT_IDENTIFIER", "your-agent-identifier")
SELLER_VKEY = os.getenv("SELLER_VKEY", "your-seller-vkey")
NETWORK = os.getenv("NETWORK", "Preprod")  # Preprod or Mainnet

def webhook_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Node 1: Webhook Input"""
    print("=== Node 1: Webhook Input ===")
    print(f"Input: {input_data}")
    
    result = {
        "body": input_data
    }
    print(f"Output: {result}")
    return result

def variables() -> Dict[str, Any]:
    """Node 2: Variables"""
    print("\n=== Node 2: Variables ===")
    
    result = {
        "payment_service_url": PAYMENT_SERVICE_URL,
        "payment_api_key": PAYMENT_API_KEY,
        "agent_identifier": AGENT_IDENTIFIER,
        "seller_vkey": SELLER_VKEY,
        "network": NETWORK
    }
    print(f"Output: {result}")
    return result

def input_hash(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Node 3: Input Hash (Crypto SHA256)"""
    print("\n=== Node 3: Input Hash ===")
    
    input_string = webhook_data["body"].get("input_string", "hello world")
    print(f"Input string: {input_string}")
    
    # Create SHA256 hash
    hash_obj = hashlib.sha256(input_string.encode())
    input_string_hash = hash_obj.hexdigest()
    
    result = {
        **webhook_data,
        "inputStringHash": input_string_hash
    }
    print(f"Hash: {input_string_hash}")
    print(f"Output: {result}")
    return result

def generate_identifier() -> Dict[str, Any]:
    """Node 4: Generate Identifier (Crypto random hex)"""
    print("\n=== Node 4: Generate Identifier ===")
    
    # Generate 14 character hex string (7 bytes)
    identifier = secrets.token_hex(7)
    
    result = {
        "identifierFromPurchaser": identifier
    }
    print(f"Generated identifier: {identifier}")
    print(f"Output: {result}")
    return result

def prepare_payment_request(hash_data: Dict[str, Any], identifier_data: Dict[str, Any], vars_data: Dict[str, Any]) -> Dict[str, Any]:
    """Node 5: Prepare Payment Request"""
    print("\n=== Node 5: Prepare Payment Request ===")
    
    # Extract input data
    input_data = hash_data["body"]
    identifier_from_purchaser = identifier_data["identifierFromPurchaser"]
    input_hash = hash_data["inputStringHash"]
    
    # Get environment variables
    payment_service_url = vars_data["payment_service_url"]
    agent_identifier = vars_data["agent_identifier"]
    network = vars_data["network"]
    
    # Generate timestamps (ISO format for /payment endpoint)
    now = datetime.now()
    print(f"Current time: {now}")
    
    # payByTime: 5 minutes from now
    pay_by_time = datetime.fromtimestamp(now.timestamp() + 5 * 60)
    pay_by_time_iso = pay_by_time.isoformat() + "Z"
    
    # submitResultTime: 20 minutes from now (15+ minute gap)
    submit_result_time = datetime.fromtimestamp(now.timestamp() + 20 * 60)
    submit_result_time_iso = submit_result_time.isoformat() + "Z"
    
    print(f"payByTime: {pay_by_time_iso} ({pay_by_time})")
    print(f"submitResultTime: {submit_result_time_iso} ({submit_result_time})")
    print(f"Gap: {(submit_result_time - pay_by_time).total_seconds() / 60} minutes")
    
    # Prepare payment request
    payment_request = {
        "agentIdentifier": agent_identifier,
        "network": network,
        "inputHash": input_hash,
        "payByTime": pay_by_time_iso,
        "metadata": f"Paywall request for input: {json.dumps(input_data)[:100]}",
        "paymentType": "Web3CardanoV1",
        "submitResultTime": submit_result_time_iso,
        "identifierFromPurchaser": identifier_from_purchaser
    }
    
    result = {
        "originalInput": input_data,
        "paymentRequest": payment_request,
        "identifierFromPurchaser": identifier_from_purchaser,
        "paymentServiceUrl": payment_service_url
    }
    
    print(f"Payment request: {json.dumps(payment_request, indent=2)}")
    return result

def create_payment_request(prep_data: Dict[str, Any], vars_data: Dict[str, Any]) -> Dict[str, Any]:
    """Node 6: Create Payment Request (HTTP POST)"""
    print("\n=== Node 6: Create Payment Request ===")
    
    url = f"{prep_data['paymentServiceUrl']}/payment/"
    headers = {
        "Content-Type": "application/json",
        "token": vars_data["payment_api_key"],
        "accept": "application/json"
    }
    
    payload = prep_data["paymentRequest"]
    
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code != 200:
        raise Exception(f"Payment request failed: {response.status_code} - {response.text}")
    
    return response.json()

def prepare_purchase_request(payment_response: Dict[str, Any], original_data: Dict[str, Any], vars_data: Dict[str, Any]) -> Dict[str, Any]:
    """Node 7: Prepare Purchase Request"""
    print("\n=== Node 7: Prepare Purchase Request ===")
    
    # Extract payment data
    payment_data = payment_response["data"]
    seller_vkey = vars_data["seller_vkey"]
    
    print(f"Payment data timestamps:")
    print(f"  payByTime: {payment_data['payByTime']}")
    print(f"  submitResultTime: {payment_data['submitResultTime']}")
    print(f"  unlockTime: {payment_data['unlockTime']}")
    print(f"  externalDisputeUnlockTime: {payment_data['externalDisputeUnlockTime']}")
    
    # CRITICAL: We CANNOT change timing values because the blockchain identifier 
    # signature is cryptographically tied to the original timestamps from payment response.
    # Changing timing breaks signature validation.
    # 
    # Solution: Use exact timestamps from payment response (already in milliseconds)
    
    print(f"Using original timestamps from payment response (signature-verified)...")
    
    # Use exact timestamps from payment response - these are already in milliseconds
    pay_by_time_millis = str(payment_data["payByTime"])
    submit_result_time_millis = str(payment_data["submitResultTime"]) 
    unlock_time_millis = str(payment_data["unlockTime"])
    external_dispute_unlock_time_millis = str(payment_data["externalDisputeUnlockTime"])
    
    print(f"Generated timestamps (milliseconds):")
    print(f"  payByTime: {pay_by_time_millis}")
    print(f"  submitResultTime: {submit_result_time_millis}")
    
    # Validate timing
    current_millis = int(time.time() * 1000)
    pay_by_time_int = int(pay_by_time_millis)
    submit_result_time_int = int(submit_result_time_millis)
    
    print(f"Current time: {current_millis} ({datetime.fromtimestamp(current_millis/1000)})")
    print(f"payByTime: {pay_by_time_int} ({datetime.fromtimestamp(pay_by_time_int/1000)})")
    print(f"submitResultTime: {submit_result_time_int} ({datetime.fromtimestamp(submit_result_time_int/1000)})")
    
    gap_minutes = (submit_result_time_int - pay_by_time_int) / (60 * 1000)
    time_until_pay_by = (pay_by_time_int - current_millis) / (60 * 1000)
    
    print(f"Gap between times: {gap_minutes} minutes")
    print(f"Time until payByTime: {time_until_pay_by} minutes")
    
    # Prepare purchase request
    purchase_request = {
        "identifierFromPurchaser": original_data["identifierFromPurchaser"],
        "network": original_data["paymentRequest"]["network"],
        "sellerVkey": seller_vkey,
        "paymentType": "Web3CardanoV1",
        "blockchainIdentifier": payment_data["blockchainIdentifier"],
        "payByTime": pay_by_time_millis,
        "submitResultTime": submit_result_time_millis,
        "unlockTime": unlock_time_millis,
        "externalDisputeUnlockTime": external_dispute_unlock_time_millis,
        "agentIdentifier": original_data["paymentRequest"]["agentIdentifier"],
        "inputHash": payment_data["inputHash"]
    }
    
    result = {
        "originalInput": original_data["originalInput"],
        "paymentData": payment_data,
        "purchaseRequest": purchase_request,
        "paymentServiceUrl": original_data["paymentServiceUrl"],
        "blockchainIdentifier": payment_data["blockchainIdentifier"]
    }
    
    print(f"Purchase request: {json.dumps(purchase_request, indent=2)}")
    return result

def create_purchase(purchase_data: Dict[str, Any], vars_data: Dict[str, Any]) -> Dict[str, Any]:
    """Node 8: Create Purchase (HTTP POST)"""
    print("\n=== Node 8: Create Purchase ===")
    
    url = f"{purchase_data['paymentServiceUrl']}/purchase/"
    headers = {
        "Content-Type": "application/json",
        "token": vars_data["payment_api_key"],
        "accept": "application/json"
    }
    
    payload = purchase_data["purchaseRequest"]
    
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code != 200:
        raise Exception(f"Purchase request failed: {response.status_code} - {response.text}")
    
    return response.json()

def wait_for_payment() -> Dict[str, Any]:
    """Node 9: Wait for Payment (simulated)"""
    print("\n=== Node 9: Wait for Payment ===")
    print("Waiting 10 seconds for payment processing...")
    time.sleep(2)  # Reduced for testing
    return {"waited": True}

def check_payment_status(purchase_data: Dict[str, Any], vars_data: Dict[str, Any]) -> Dict[str, Any]:
    """Node 10: Check Payment Status"""
    print("\n=== Node 10: Check Payment Status ===")
    
    url = f"{purchase_data['paymentServiceUrl']}/payment/"
    headers = {
        "accept": "application/json",
        "token": vars_data["payment_api_key"]
    }
    params = {
        "limit": "10",
        "network": vars_data["network"],
        "includeHistory": "false"
    }
    
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Params: {params}")
    
    response = requests.get(url, headers=headers, params=params)
    
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code != 200:
        raise Exception(f"Payment status check failed: {response.status_code} - {response.text}")
    
    return response.json()

def evaluate_payment_status(payment_status_response: Dict[str, Any], purchase_data: Dict[str, Any]) -> Dict[str, Any]:
    """Node 11: Evaluate Payment Status"""
    print("\n=== Node 11: Evaluate Payment Status ===")
    
    blockchain_identifier = purchase_data["blockchainIdentifier"]
    print(f"Looking for blockchain identifier: {blockchain_identifier}")
    
    # Find our payment in the response
    our_payment = None
    if payment_status_response["data"] and payment_status_response["data"]["Payments"]:
        our_payment = next(
            (payment for payment in payment_status_response["data"]["Payments"] 
             if payment["blockchainIdentifier"] == blockchain_identifier), 
            None
        )
    
    is_confirmed = False
    payment_status = 'not_found'
    
    if our_payment:
        on_chain_state = our_payment.get("onChainState")
        payment_status = on_chain_state or 'pending'
        is_confirmed = on_chain_state == 'FundsLocked'
        print(f"Found payment with onChainState: {on_chain_state}")
    else:
        print("Payment not found in response")
    
    result = {
        "isPaymentConfirmed": is_confirmed,
        "paymentStatus": payment_status,
        "ourPayment": our_payment,
        "originalInput": purchase_data["originalInput"],
        "blockchainIdentifier": blockchain_identifier
    }
    
    print(f"Payment evaluation result: {json.dumps(result, indent=2)}")
    return result

def main():
    """Run the complete workflow"""
    print("🚀 Starting N8N Workflow Replica")
    print("=" * 50)
    
    try:
        # Test input
        test_input = {"input_string": "Test paywall workflow"}
        
        # Execute workflow nodes in sequence
        webhook_data = webhook_input(test_input)
        vars_data = variables()
        hash_data = input_hash(webhook_data)
        identifier_data = generate_identifier()
        
        prep_data = prepare_payment_request(hash_data, identifier_data, vars_data)
        payment_response = create_payment_request(prep_data, vars_data)
        
        purchase_prep_data = prepare_purchase_request(payment_response, prep_data, vars_data)
        purchase_response = create_purchase(purchase_prep_data, vars_data)
        
        # Continue with payment status checking
        wait_result = wait_for_payment()
        payment_status_response = check_payment_status(purchase_prep_data, vars_data)
        evaluation_result = evaluate_payment_status(payment_status_response, purchase_prep_data)
        
        print(f"\n🎉 SUCCESS! Full workflow completed")
        print(f"Payment confirmed: {evaluation_result['isPaymentConfirmed']}")
        print(f"Payment status: {evaluation_result['paymentStatus']}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()