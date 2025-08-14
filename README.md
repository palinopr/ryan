# Meta Ryan - Tour Campaign Client Portal

## Overview
A secure, read-only client portal for viewing Meta Ads tour campaign performance data. Built with LangGraph for intelligent multi-agent orchestration.

**Property of**: Outlet Media  
**Client Access**: Read-only performance metrics  
**Security**: Phone-based access control with campaign-level restrictions

## Features

### Client Portal (Read-Only)
- **City Performance Reports**: View metrics by tour location
- **Campaign Insights**: Access all performance data for any date range
- **Asset Metrics**: See ad, adset, and campaign performance
- **ROAS Tracking**: Return on ad spend by city
- **Client-Friendly Formatting**: Clear, non-technical reports

### Security Features
- **Phone-Based Access Control**: Only authorized numbers can access
- **Campaign-Level Restrictions**: Users only see their assigned campaigns
- **Strategy Protection**: All optimization methods and strategies are hidden
- **Query Filtering**: Blocks questions about HOW campaigns work

## Project Structure

```
Meta Ryan/
├── app.py                    # Main LangGraph Studio entry point
├── langgraph.json           # LangGraph configuration
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project configuration
├── .env                    # Environment variables (not in git)
├── .gitignore             # Git ignore rules
│
├── src/                   # Source code
│   ├── agents/           # LangGraph agents
│   │   ├── meta_campaign_agent.py  # Main Meta Ads agent
│   │   ├── ghl_agent.py           # GoHighLevel CRM agent
│   │   ├── security_agent.py      # Security validation
│   │   └── supervisor_agent.py    # Multi-agent orchestrator
│   │
│   ├── config/          # Configuration
│   │   ├── settings.py           # App settings
│   │   └── security_config.py   # Access control config
│   │
│   └── tools/           # Integration tools
│       ├── meta_ads_tools.py        # Meta SDK wrapper
│       └── meta_ads_intelligence.py # Analysis tools
│
├── tests/              # Test suite
│   ├── test_campaign_security.py    # Security tests
│   ├── test_city_formatting.py      # Output formatting
│   └── ...                          # Other tests
│
├── scripts/            # Utility scripts
│   └── extend_meta_token.py  # Token renewal utility
│
└── docs/              # Documentation
    ├── ARCHITECTURE.md
    └── system_flow_diagram.md
```

## Setup

### 1. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file with:
```env
# Meta API Credentials
META_ACCESS_TOKEN=your_token_here
META_AD_ACCOUNT_ID=act_123456789
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret

# AI Model (choose one)
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# LangGraph Studio
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=meta-ryan
```

### 3. Configure Access Control
Edit `src/config/security_config.py` to set authorized phone numbers and campaign access.

## Running the System

### LangGraph Studio (Recommended)
```bash
source venv/bin/activate
langgraph dev
```
Then access at http://localhost:8123

### Available Graphs
- `meta_agent` - Meta Ads campaign analysis
- `ghl_agent` - GoHighLevel CRM operations  
- `security` - Security validation
- `supervisor` - Multi-agent orchestrator

## Client Access

### What Clients CAN Access
✅ All performance metrics and insights:
- Campaign, AdSet, Ad, and Asset metrics
- City/location performance data
- CTR, CPC, CPM, ROAS, impressions, clicks, spend
- Any date range analysis
- Video views, engagement, conversions

### What Clients CANNOT Access
🔒 Proprietary Outlet Media information:
- How campaigns are structured or created
- Optimization strategies and methods
- When/how budgets are updated
- Creative content and messaging
- Targeting strategies
- Any modification capabilities

## Security Model

### Phone-Based Access
```python
# Ryan Castro - can only see campaign 120232002620350525
"+17865551234": ["120232002620350525"]

# Agency Admin - can see all campaigns
"+13055551234": ["*"]
```

### Query Filtering
The system automatically blocks:
- Questions about campaign structure
- Strategy and optimization queries
- Modification attempts
- Creative content requests

## Testing

Run security tests:
```bash
python tests/test_campaign_security.py
python tests/test_security_restrictions.py
```

Run formatting tests:
```bash
python tests/test_city_formatting.py
```

## Maintenance

### Extending Meta Token
Meta access tokens expire after 60 days. To renew:
```bash
python scripts/extend_meta_token.py
```

### Adding New Users
Edit `src/config/security_config.py` and add phone numbers with campaign access.

## Support

For technical issues, check:
1. `.env` file has correct credentials
2. Phone number is authorized in security_config.py
3. Campaign ID exists and user has access
4. Meta token is not expired

## License

Proprietary - Outlet Media. All rights reserved.