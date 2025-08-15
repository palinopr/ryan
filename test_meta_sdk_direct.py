#!/usr/bin/env python3
"""
Direct Meta SDK call to verify data exists for today
"""

import os
from dotenv import load_dotenv
load_dotenv()

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
import json

def test_meta_sdk_direct():
    """Direct Meta SDK call to check today's data"""
    
    print("="*100)
    print("🔧 DIRECT META SDK TEST")
    print("="*100)
    
    # Initialize the SDK
    app_id = os.getenv('META_APP_ID')
    app_secret = os.getenv('META_APP_SECRET')
    access_token = os.getenv('META_ACCESS_TOKEN')
    
    if not all([app_id, app_secret, access_token]):
        print("❌ Missing Meta API credentials in .env")
        return
    
    FacebookAdsApi.init(app_id, app_secret, access_token)
    print("✅ Meta SDK initialized")
    
    # Test campaign IDs from the codebase
    test_campaigns = [
        "120232002620350525",  # From previous traces
        "120210696387540704",  # Alternative campaign
    ]
    
    for campaign_id in test_campaigns:
        print(f"\n📊 Testing Campaign: {campaign_id}")
        print("-" * 50)
        
        try:
            campaign = Campaign(campaign_id)
            
            # Test 1: Get campaign info
            print("\n1️⃣ Campaign Info:")
            campaign_info = campaign.api_get(fields=['name', 'status', 'objective'])
            print(f"   Name: {campaign_info.get('name', 'N/A')}")
            print(f"   Status: {campaign_info.get('status', 'N/A')}")
            print(f"   Objective: {campaign_info.get('objective', 'N/A')}")
            
            # Test 2: Get insights for TODAY
            print("\n2️⃣ Insights for TODAY:")
            insights_today = campaign.get_insights(
                fields=[
                    'impressions',
                    'clicks', 
                    'spend',
                    'actions',
                    'action_values'
                ],
                params={
                    'date_preset': 'today',
                    'level': 'campaign'
                }
            )
            
            if insights_today:
                for insight in insights_today:
                    data = dict(insight)
                    print(f"   Impressions: {data.get('impressions', 0)}")
                    print(f"   Clicks: {data.get('clicks', 0)}")
                    print(f"   Spend: ${data.get('spend', 0)}")
                    
                    # Check for purchase actions
                    actions = data.get('actions', [])
                    purchases = 0
                    for action in actions:
                        if 'purchase' in action.get('action_type', ''):
                            purchases = int(action.get('value', 0))
                            print(f"   Purchases: {purchases}")
                    
                    if purchases == 0:
                        print(f"   Purchases: 0 (no purchase actions found)")
            else:
                print("   ❌ No data for today")
            
            # Test 3: Get insights for MAXIMUM (all-time)
            print("\n3️⃣ Insights for ALL-TIME (maximum):")
            insights_max = campaign.get_insights(
                fields=[
                    'impressions',
                    'clicks',
                    'spend',
                    'actions',
                    'action_values'
                ],
                params={
                    'date_preset': 'maximum',
                    'level': 'campaign'
                }
            )
            
            if insights_max:
                for insight in insights_max:
                    data = dict(insight)
                    print(f"   Impressions: {data.get('impressions', 0)}")
                    print(f"   Clicks: {data.get('clicks', 0)}")
                    print(f"   Spend: ${data.get('spend', 0)}")
                    
                    # Check for purchase actions
                    actions = data.get('actions', [])
                    purchases = 0
                    for action in actions:
                        if 'purchase' in action.get('action_type', ''):
                            purchases = int(action.get('value', 0))
                            print(f"   Purchases: {purchases}")
                    
                    if purchases == 0:
                        print(f"   Purchases: 0 (no purchase actions found)")
            else:
                print("   ❌ No all-time data")
            
            # Test 4: Get AdSets for the campaign
            print("\n4️⃣ AdSets in Campaign:")
            adsets = campaign.get_ad_sets(
                fields=['name', 'status', 'targeting'],
                params={'limit': 5}
            )
            
            adset_count = 0
            for adset in adsets:
                adset_count += 1
                print(f"   • {adset.get('name', 'Unnamed')} - Status: {adset.get('status', 'N/A')}")
                
                # Get today's data for this adset
                adset_obj = AdSet(adset['id'])
                adset_insights = adset_obj.get_insights(
                    fields=['impressions', 'clicks', 'spend'],
                    params={'date_preset': 'today'}
                )
                
                if adset_insights:
                    for insight in adset_insights:
                        data = dict(insight)
                        imp = data.get('impressions', 0)
                        clicks = data.get('clicks', 0)
                        spend = data.get('spend', 0)
                        print(f"     Today: {imp} impressions, {clicks} clicks, ${spend} spend")
                
                if adset_count >= 3:  # Limit to first 3 adsets
                    print(f"   ... and more")
                    break
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "="*100)
    print("💡 ANALYSIS:")
    print("="*100)
    print("""
    If you see 0 impressions/clicks/spend for TODAY but data for ALL-TIME:
    - The campaigns might not be actively running today
    - Or there simply hasn't been any activity yet today
    - This would explain why the system correctly returns 0 for "today" queries
    
    If you see data for TODAY:
    - Then there might be an issue with how the system is querying the API
    - Check the date_preset parameter being passed
    """)

if __name__ == "__main__":
    test_meta_sdk_direct()