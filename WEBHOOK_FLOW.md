# GoHighLevel to LangGraph Webhook Integration Flow

## Overview
This document explains how the webhook integration works between GoHighLevel (GHL) and the LangGraph deployment for the Meta Ryan multi-agent system.

## Architecture

```
GoHighLevel → Webhook → LangGraph Deployment → Supervisor → Agents → Response
                            ↓
                    Security Validation
```

## Components

### 1. GoHighLevel Webhook Configuration
**URL:** `https://meta-ryan-e63beed228015a5fbcf0b5408aa860fa.us.langgraph.app/ghl-webhook`

**Method:** POST

**Headers:**
```
Content-Type: application/json
```

**Body Format:**
```json
{
  "id": "{{contact.id}}",
  "name": "{{contact.name}}",
  "email": "{{contact.email}}",
  "phone": "{{contact.phone}}",
  "message": "{{message.body}}"
}
```

### 2. LangGraph Custom API Endpoint (`api.py`)
- Receives the webhook from GoHighLevel
- Formats phone number with country code
- Creates or finds thread for the contact
- Sends message to supervisor graph
- Returns response to GoHighLevel

### 3. Supervisor Graph Flow
```
1. Receive webhook data
   ↓
2. Security Agent validates phone number
   ↓
3. If authorized:
   - Route to appropriate agent (Meta or GHL)
   - Process request
   - Use GHL MCP tools to respond
   ↓
4. If unauthorized:
   - Return error message
```

### 4. Security Validation

#### Two-Layer Security:

**Layer 1: Webhook Secret (Optional)**
- Set `GHL_WEBHOOK_SECRET` environment variable in deployment
- GoHighLevel sends `X-Webhook-Secret` header
- Prevents unauthorized webhook calls

**Layer 2: Phone Number Validation (Required)**
- Supervisor routes to security_agent
- Checks against whitelist in `security_config.py`
- Authorized numbers:
  - `+13054870475` - Jaime Admin
  - `+17865551234` - Ryan Castro
  - Others configured in security_config.py

### 5. Agent Processing

**Meta Agent:**
- Searches Facebook/Instagram campaigns
- Retrieves ad metrics
- Updates campaign settings

**GHL Agent:** 
- Manages contacts
- Sends messages via GHL API
- Creates appointments
- Updates opportunities

### 6. Response Flow
```
Supervisor → GHL MCP Tools → GoHighLevel API → Customer
```

## File Structure

```
/Users/jaimeortiz/Visual Studio/Meta Ryan/
├── langgraph.json          # Deployment configuration
├── api.py                  # Custom webhook endpoint
├── app.py                  # Graph definitions
├── src/
│   ├── agents/
│   │   ├── supervisor_agent.py
│   │   ├── security_agent.py
│   │   ├── meta_agent.py
│   │   └── ghl_agent.py
│   ├── config/
│   │   └── security_config.py  # Phone whitelist
│   └── tools/
│       ├── meta_ads_tools.py
│       └── ghl_tools.py
└── .env                    # Environment variables
```

## Deployment Configuration

### langgraph.json
```json
{
  "dependencies": ["."],
  "graphs": {
    "supervisor": "./app.py:supervisor_graph",
    "meta_agent": "./app.py:graph",
    "ghl_agent": "./app.py:ghl_graph",
    "security": "./app.py:security_graph"
  },
  "api": "./api.py:app",  // Custom API routes
  "env": ".env"
}
```

## Environment Variables

Required in LangSmith deployment:
```
# Meta/Facebook
META_ACCESS_TOKEN=your_token
META_AD_ACCOUNT_ID=act_xxxxx
META_SYSTEM_USER_TOKEN=your_system_token

# GoHighLevel
GHL_API_KEY=your_ghl_api_key
GHL_LOCATION_ID=your_location_id

# Optional Security
GHL_WEBHOOK_SECRET=your_secret_key

# Phone Numbers
ADMIN_PHONE_NUMBER=+13054870475
RYAN_PHONE=+17865551234
```

## Testing the Webhook

### Local Test:
```bash
curl -X POST https://meta-ryan-e63beed228015a5fbcf0b5408aa860fa.us.langgraph.app/ghl-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-contact-123",
    "name": "Test User",
    "email": "test@example.com",
    "phone": "3054870475",
    "message": "Hello, I need help with my campaign"
  }'
```

### Expected Response:
```json
{
  "success": true,
  "thread_id": "uuid-here",
  "message": "Response from supervisor",
  "contact_id": "test-contact-123",
  "timestamp": "2025-08-14T00:00:00"
}
```

## Common Issues

### 503 Service Temporarily Unavailable
- Deployment is rebuilding after code push
- Wait 2-5 minutes for deployment to complete

### Missing authentication headers
- Custom API endpoint not deployed yet
- Check if `"api": "./api.py:app"` is in langgraph.json
- Verify deployment has completed

### Unauthorized phone number
- Phone not in security_config.py whitelist
- Add phone to SECURITY_CONFIG["whitelist"]

### Account temporarily locked
- Too many failed authentication attempts
- Wait for lockout period to expire (15 minutes)

## Workflow Summary

1. **Customer sends message in GoHighLevel**
2. **GHL triggers webhook** to LangGraph deployment
3. **Custom API endpoint** (`/ghl-webhook`) receives data
4. **Security validation** checks phone number
5. **Supervisor routes** to appropriate agent
6. **Agent processes** request (Meta search, etc.)
7. **Response sent back** via GHL MCP tools
8. **Customer receives** response in GoHighLevel

## Deployment Process

1. Make changes to code
2. Commit and push to GitHub
3. LangSmith automatically rebuilds deployment
4. Wait 2-5 minutes for deployment to complete
5. Test webhook endpoint

## Important URLs

- **Webhook Endpoint:** `https://meta-ryan-e63beed228015a5fbcf0b5408aa860fa.us.langgraph.app/ghl-webhook`
- **LangSmith Deployment:** https://smith.langchain.com/o/d46348af-8871-4fc1-bb27-5d17f0589bd5/projects/p/2bfd7798-2217-4c7a-b1a2-250cef2b0daa/deployments
- **GitHub Repository:** https://github.com/palinopr/ryan

## Next Steps

1. Ensure all environment variables are set in LangSmith deployment
2. Configure GoHighLevel webhook with correct format
3. Test with real contact messages
4. Monitor logs in LangSmith for debugging