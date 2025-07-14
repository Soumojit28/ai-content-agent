# Masumi n8n Paywall Workflow

## Overview

This repository contains an **n8n workflow** that implements a paywall pattern using the Masumi payment system. The workflow handles payment requests, purchase creation, and status polling - allowing you to monetize any n8n workflow with Cardano blockchain payments.

![Masumi n8n Paywall Workflow](assets/masumi-paywall-n8n-flow.png)

## Repository Contents

- **`Masumi_n8n_Paywall_Flow_no_vars.json`** - The n8n workflow file to import
- **`n8n_workflow_replica.py`** - Python script that replicates the workflow for testing/debugging
- **`.env.example`** - Example configuration file for the replica script
- **`requirements.txt`** - Python dependencies for the replica script

## Quick Start

### 1. Deploy Masumi Payment Service

**Before setting up the n8n workflow, you must have access to your own Masumi Payment Service.** This service is required to:
- Register your agent and connect it to a seller account
- Handle all blockchain interactions and payment processing
- Manage payment requests and status polling

This example uses <a href="https://railway.com?referralCode=pa1ar" target="_blank">Railway</a> templates. Railway is a cloud development platform that enables developers to deploy, manage and scale applications and databases with minimal configuration.

**Prerequisites:**
- <a href="https://blockfrost.io/" target="_blank">Blockfrost</a> API key (free tier is enough)
- <a href="https://railway.com?referralCode=pa1ar" target="_blank">Railway account</a> (free trial is 30 days or $5, more than enough for testing)

**Deploy Payment Service:**

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/masumi-payment-service-official?referralCode=padierfind)

1. Click the deploy button above
2. Provide Blockfrost API key in variables (required to deploy)
3. Wait for deployment (takes 5 minutes or so)
4. You'll see 2 services: PostgreSQL database and Masumi Payment Service
5. Generate a public URL: Payment Service > Settings > Networking > Generate URL
6. Test at `/admin` or `/docs`. Your admin key is in the variables. **Change it in the admin panel.**

**Prepare for Agent Registration:**
1. Go to Payment Service admin panel at `/admin`
2. Top up selling wallet using <a href="https://dispenser.masumi.network/" target="_blank">Masumi tADA dispenser</a> (Preprod)
3. Top up your buying wallet (you'll need funds for testing payments)
4. Note your seller wallet verification key (vkey) from the admin panel
5. Copy your Masumi Payment Service URL (format: `https://your-service.railway.app/api/v1`)

**Important:** For testing purposes, this workflow shows payment from the same payment service instance. For production and selling services to real customers, refer to the full <a href="https://docs.masumi.network/" target="_blank">Masumi documentation</a> for instructions about selling on marketplaces like Sokosumi.

### 2. Set Up n8n

You have several options to run an n8n workflow:

- **Cloud**: Use [n8n cloud](https://n8n.io/cloud/), fully managed by n8n, includes AI assistant etc.
- **Self-hosted**: Follow the [n8n installation guide](https://docs.n8n.io/hosting/)
- **Railway Template**: Deploy n8n quickly using Railway's n8n template, [for example this one](https://railway.com/deploy/n8n-with-workers) (if you have used Railway for deploying the Masumi Payment Service, you can use the same project to add the n8n service)
- **Docker**: Run n8n in a container using [n8n Docker image](https://hub.docker.com/r/n8nio/n8n)

### 3. Import the Workflow

1. Open your n8n instance
2. Go to Workflows → Import
3. Upload `Masumi_n8n_Paywall_Flow_no_vars.json`
4. The workflow will appear in your editor
5. Note the webhook URL (click on the webhook node to see it)

### 4. Register Your Agent

1. In the Masumi Payment Service admin panel, register your agent
2. Use your n8n webhook URL as the agent endpoint
3. Wait for registration to complete
4. Copy your agent identifier (Asset ID) from the admin panel

### 5. Configure Variables

Update these variables in the workflow's "variables draft" node:

```json
{
  "payment_service_url": "https://your-masumi-payment-service/api/v1",
  "payment_api_key": "your-payment-service-api-key",
  "agent_identifier": "your-registered-agent-id",
  "seller_vkey": "your-seller-wallet-verification-key",
  "network": "Preprod"
}
```

**Important**: For production, use n8n's environment variables (requires enterprise plan, even if you self-host) or credentials system instead of hardcoding values. Also remember to include `/api/v1` in your payment service URL.

### 6. Activate & Test

1. Save and activate your workflow in n8n
2. Test with a POST request to your webhook URL:

```bash
curl -X POST https://your-n8n-instance/webhook/paywall-agent \
  -H "Content-Type: application/json" \
  -d '{"input_string": "Test payment flow"}'
```


## Workflow Details

### How It Works

1. **Webhook Trigger** (`/paywall-agent`) - Entry point for requests
2. **Payment Creation** - Generates payment request with unique identifiers
3. **Purchase Request** - Locks funds using blockchain identifier
4. **Status Polling** - Checks every 10 seconds for payment confirmation
5. **Business Logic** - Executes your custom logic after payment

### Key Nodes Explained

- **Variables**: Configuration storage (update with your values)
- **Input Hash**: SHA256 hash of input for payment tracking
- **Generate Identifier**: Random hex for purchaser identification
- **Prepare Payment/Purchase**: Builds proper JSON payloads
- **Wait for Payment**: 10-second delay between status checks
- **Evaluate Payment Status**: Checks for `FundsLocked` state
- **Execute Business Logic**: Your custom processing (modify this!)

### Integrating with Existing Workflows

This paywall workflow is designed to be **prepended** to your existing business logic:

**Option 1: Add paywall to existing workflow**
1. Import this paywall workflow to your n8n instance
2. Copy the paywall nodes (everything before "Execute Business Logic")
3. Paste them at the beginning of your existing workflow
4. Connect the paywall's success output to your existing workflow's first node
5. Replace the "Execute Business Logic" node with your actual business logic

**Option 2: Add business logic to this workflow**
1. Import this complete paywall workflow
2. Replace/modify the "Execute Business Logic" node with your functionality
3. Access input data via `$('webhook input').item.json.body`

Example business logic:
```javascript
const input = $('webhook input').item.json.body.input_string;
// Your custom processing here
return { result: "Processed: " + input };
```

### Security Considerations

**Important Security Warning:**

The webhook trigger in this workflow is **unprotected by default**. Anyone who discovers your webhook URL can trigger the workflow. For production use:

1. **Protect your webhook URL:**
   - Use n8n's built-in webhook authentication
   - Add custom authentication logic in the workflow
   - Implement API key validation
   - Use IP whitelisting if applicable

2. **Consider authentication patterns:**
   ```javascript
   // Example: API key validation in the first node
   const apiKey = $('webhook input').item.json.headers['x-api-key'];
   if (!apiKey || apiKey !== 'your-secret-key') {
     throw new Error('Unauthorized');
   }
   ```

3. **Environment-specific URLs:**
   - Use different webhook URLs for development/testing
   - Keep production webhook URLs confidential
   - Monitor webhook access logs

4. **Rate limiting:**
   - Implement request throttling to prevent abuse
   - Use n8n's rate limiting features if available

## Testing & Debugging

### Using the Python Replica Script

The `n8n_workflow_replica.py` script helps debug issues:

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values

# Run the test
python n8n_workflow_replica.py
```

This script:
- Replicates each workflow node as a Python function
- Shows detailed request/response data
- Helps debug timing and signature issues
- Useful for understanding the payment flow

### Common Issues

1. **"Pay by time must be before submit result time"**
   - The payment service expects future timestamps
   - Minimum 5-minute gap required between timestamps

2. **"Invalid blockchain identifier, signature invalid"**
   - Never modify timestamps from payment response
   - The blockchain identifier is cryptographically signed
   - Use exact values returned by payment service

3. **"Referenced node doesn't exist"**
   - Check node names in n8n expressions
   - Use exact node names, not IDs

## Additional Security Notes

1. **Never commit credentials** - Use environment variables or n8n credentials
2. **Secure your n8n instance** - Enable authentication and proper access controls
3. **Monitor payment flows** - Check for unusual activity or failed payments
4. **Test on Preprod first** - Always use testnet before deploying to mainnet
5. **Keep endpoints private** - Don't expose development/test webhook URLs publicly

## Resources

- [n8n Documentation](https://docs.n8n.io/)
- [Masumi Network Docs](https://docs.masumi.network/)
- [Masumi Payment Service](https://github.com/masumi-network/masumi-payment-service)
- [Blockfrost API](https://blockfrost.io/)

## Support

- **n8n Issues**: Check [n8n community](https://community.n8n.io/)
- **Masumi Issues**: Visit [Masumi Discord](https://discord.gg/masumi)
- **Workflow Issues**: Use this repository's issue tracker