#!/usr/bin/env python3
"""
Direct test of Meta API to verify data access
"""
import os
from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign

load_dotenv()

# Initialize
FacebookAdsApi.init(access_token=os.getenv('META_ACCESS_TOKEN'))

# Get the campaign
campaign_id = os.getenv('DEFAULT_CAMPAIGN_ID', '120232002620350525')
campaign = Campaign(campaign_id)

# Get basic info
campaign_fields = campaign.api_get(fields=['name', 'status', 'objective'])
print(f"Campaign: {campaign_fields['name']}")
print(f"Status: {campaign_fields['status']}")

# Get insights for today
insights = campaign.get_insights(fields=[
    'impressions',
    'clicks', 
    'spend',
    'ctr',
    'purchase_roas'
], params={
    'date_preset': 'today'
})

if insights:
    for insight in insights:
        print(f"\nToday's Performance:")
        impressions = int(insight.get('impressions', 0))
        print(f"  Impressions: {impressions:,}")
        print(f"  Clicks: {insight.get('clicks', 0)}")
        print(f"  Spend: ${insight.get('spend', 0)}")
        print(f"  CTR: {insight.get('ctr', 0)}%")
        
        # ROAS might be in a nested structure
        roas_data = insight.get('purchase_roas', [])
        if roas_data and isinstance(roas_data, list) and len(roas_data) > 0:
            print(f"  ROAS: {roas_data[0].get('value', 'N/A')}")
        elif roas_data:
            print(f"  ROAS: {roas_data}")
else:
    print("No data for today yet")

# Get last 7 days
insights_week = campaign.get_insights(fields=[
    'impressions',
    'clicks',
    'spend'
], params={
    'date_preset': 'last_7d'
})

if insights_week:
    for insight in insights_week:
        print(f"\nLast 7 Days:")
        total_impressions = int(insight.get('impressions', 0))
        total_clicks = int(insight.get('clicks', 0))
        print(f"  Total Impressions: {total_impressions:,}")
        print(f"  Total Clicks: {total_clicks:,}")
        print(f"  Total Spend: ${insight.get('spend', 0)}")