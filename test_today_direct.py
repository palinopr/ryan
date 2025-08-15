#!/usr/bin/env python3
"""
Direct test of Meta SDK with today preset
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
import json

def test_today_direct():
    """Test today preset directly with Meta SDK"""
    
    # Initialize
    app_id = os.getenv('META_APP_ID')
    app_secret = os.getenv('META_APP_SECRET')
    access_token = os.getenv('META_ACCESS_TOKEN')
    
    FacebookAdsApi.init(app_id, app_secret, access_token)
    
    campaign_id = "120232002620350525"
    campaign = Campaign(campaign_id)
    
    print("="*100)
    print("TESTING CAMPAIGN LEVEL - TODAY")
    print("="*100)
    
    # Test campaign level with today
    params = {'date_preset': 'today', 'level': 'campaign'}
    fields = ['impressions', 'clicks', 'spend', 'actions', 'action_values']
    
    insights = campaign.get_insights(fields=fields, params=params)
    insights_list = list(insights)
    
    print(f"Campaign insights for today: {len(insights_list)} records")
    for insight in insights_list:
        data = dict(insight)
        print(json.dumps(data, indent=2, default=str))
    
    print("\n" + "="*100)
    print("TESTING ADSET LEVEL - TODAY")
    print("="*100)
    
    # Get adsets
    adsets = campaign.get_ad_sets(fields=['id', 'name', 'status'], params={'limit': 5})
    
    total_impressions = 0
    total_clicks = 0
    total_spend = 0
    
    for adset in adsets:
        adset_id = adset['id']
        adset_name = adset.get('name', 'Unknown')
        print(f"\nAdSet: {adset_name} (ID: {adset_id})")
        
        adset_obj = AdSet(adset_id)
        params = {'date_preset': 'today', 'level': 'adset'}
        
        insights = adset_obj.get_insights(fields=fields, params=params)
        insights_list = list(insights)
        
        if insights_list:
            for insight in insights_list:
                data = dict(insight)
                imp = int(data.get('impressions', 0))
                clicks = int(data.get('clicks', 0))
                spend = float(data.get('spend', 0))
                
                total_impressions += imp
                total_clicks += clicks
                total_spend += spend
                
                print(f"  Impressions: {imp}")
                print(f"  Clicks: {clicks}")
                print(f"  Spend: ${spend}")
        else:
            print("  No data for today")
    
    print("\n" + "="*100)
    print("TOTALS FOR TODAY:")
    print(f"  Total Impressions: {total_impressions}")
    print(f"  Total Clicks: {total_clicks}")
    print(f"  Total Spend: ${total_spend:.2f}")
    
    if total_impressions == 0:
        print("\n⚠️ NO DATA FOR TODAY - This is why the system returns 0!")
        print("The campaign might not be running today or hasn't had activity yet.")
    else:
        print("\n✅ DATA EXISTS FOR TODAY")
        print("If the system shows 0, there's a processing issue in the pipeline.")

if __name__ == "__main__":
    test_today_direct()