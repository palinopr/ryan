# Deployment Guide for Meta Ryan

## LangSmith Cloud Deployment

### Prerequisites
1. LangSmith account with API key
2. GitHub repository (already set up at https://github.com/palinopr/ryan)
3. Required environment variables configured

### Step 1: Configure GitHub Secrets

Go to your GitHub repository settings and add these secrets:

1. **Settings > Secrets and variables > Actions**
2. Add the following repository secrets:

```
LANGCHAIN_API_KEY=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
META_ACCESS_TOKEN=<your_meta_token>
META_APP_ID=<your_meta_app_id>
META_APP_SECRET=<your_meta_app_secret>
META_AD_ACCOUNT_ID=act_787610255314938
OPENAI_API_KEY=<your_openai_key>
GHL_API_TOKEN=pit-a8542e9c-acdd-480d-a04d-097e2ee5f77e
GHL_LOCATION_ID=j1F264MGsBFACNi0z7qE
```

### Step 2: Deploy to LangSmith

#### Option A: GitHub Actions (Automatic)
The repository is configured with GitHub Actions for automatic deployment.
- Push to `main` branch triggers deployment
- Or manually trigger via Actions tab

#### Option B: Manual Deployment via CLI

1. Install LangGraph CLI:
```bash
pip install -U langchain-cli
```

2. Set environment variables:
```bash
export LANGCHAIN_API_KEY=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
export LANGCHAIN_PROJECT=meta-ryan
```

3. Deploy from project root:
```bash
langchain deploy
```

### Step 3: LangSmith Platform Configuration

1. Go to https://smith.langchain.com/
2. Navigate to your project: `meta-ryan`
3. Configure the deployment settings:
   - **Runtime**: Python 3.11
   - **Instance Type**: Standard
   - **Region**: us-west-2

### Step 4: Environment Variables in LangSmith

In LangSmith deployment settings, add these environment variables:

```env
# Meta API
META_ACCESS_TOKEN=<your_token>
META_APP_ID=1349075236218599
META_APP_SECRET=7c301f1ac1404565f26462e3c734194c
META_AD_ACCOUNT_ID=act_787610255314938
DEFAULT_CAMPAIGN_ID=120232002620350525

# OpenAI
OPENAI_API_KEY=<your_key>
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.3

# GoHighLevel
GHL_API_TOKEN=pit-a8542e9c-acdd-480d-a04d-097e2ee5f77e
GHL_LOCATION_ID=j1F264MGsBFACNi0z7qE
GHL_BASE_URL=https://rest.gohighlevel.com/v1

# Security
RYAN_PHONE=+17865551234
MANAGER_PHONE=+17865555678
AGENCY_PHONE=+13055551234
```

### Step 5: Test Deployment

1. **Via LangSmith UI**:
   - Go to your deployed application
   - Test with sample inputs
   - Monitor traces and logs

2. **Via API**:
```python
from langsmith import Client

client = Client()
# Test your deployed graph
response = client.run(
    project_name="meta-ryan",
    inputs={"messages": [{"role": "user", "content": "Show me Miami performance"}]},
    config={"phone_number": "+17865551234"}
)
```

### Step 6: Monitor and Debug

1. **LangSmith Dashboard**:
   - View traces: https://smith.langchain.com/projects/meta-ryan
   - Monitor performance metrics
   - Debug failed runs

2. **Logs**:
   - Check deployment logs in LangSmith
   - GitHub Actions logs for deployment issues

## Local Development

For local testing before deployment:

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally with LangGraph Studio
langgraph dev

# Access at http://localhost:8123
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify LANGCHAIN_API_KEY is correct
   - Check GitHub secrets are properly set

2. **Meta API Issues**:
   - Token may be expired (use scripts/extend_meta_token.py)
   - Verify campaign access permissions

3. **GHL Integration**:
   - Confirm API token is valid
   - Check location ID matches your account

### Support Contacts

- **Technical Issues**: Check LangSmith documentation
- **Meta Ads API**: Facebook Developer Support
- **GoHighLevel**: GHL Support Portal

## Security Notes

- Never commit `.env` file to GitHub
- Rotate API keys regularly
- Use phone-based access control for client restrictions
- All strategic information is automatically filtered