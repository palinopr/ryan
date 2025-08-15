#!/usr/bin/env python3
"""
Test meta_sdk_query function directly to isolate the issue
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from src.tools.meta_ads_tools import meta_sdk_query
import json

def test_meta_sdk_query_today():
    """Test the meta_sdk_query function with today preset"""
    
    print("="*100)
    print("TESTING meta_sdk_query FUNCTION DIRECTLY")
    print("="*100)
    
    # Test query for today - similar to what the system generates
    query = {
        "operation": "get_adsets_insights",
        "campaign_id": "120232002620350525",
        "date_preset": "today",
        "fields": ["impressions", "clicks", "spend", "ctr", "cpc", "cpm", "actions", "action_values", "purchase_roas"],
        "level": "adset"
    }
    
    print("\nQuery being sent:")
    print(json.dumps(query, indent=2))
    
    print("\n" + "-"*50)
    print("Calling meta_sdk_query.invoke() as a tool...")
    print("-"*50)
    
    # Call as a tool (needs to be wrapped in "query" key)
    result = meta_sdk_query.invoke({"query": query})
    
    print(f"\nResult type: {type(result)}")
    
    if isinstance(result, list):
        print(f"Number of records: {len(result)}")
        
        if result:
            # Aggregate totals
            total_impressions = 0
            total_clicks = 0
            total_spend = 0
            
            for item in result:
                if isinstance(item, dict):
                    imp = int(item.get('impressions', 0))
                    clicks = int(item.get('clicks', 0))
                    spend = float(item.get('spend', 0))
                    
                    total_impressions += imp
                    total_clicks += clicks
                    total_spend += spend
                    
                    print(f"\nAdSet: {item.get('adset_name', 'Unknown')}")
                    print(f"  Impressions: {imp}")
                    print(f"  Clicks: {clicks}")
                    print(f"  Spend: ${spend}")
            
            print("\n" + "="*100)
            print("TOTALS:")
            print(f"  Total Impressions: {total_impressions}")
            print(f"  Total Clicks: {total_clicks}")
            print(f"  Total Spend: ${total_spend:.2f}")
            
            if total_impressions == 0:
                print("\n❌ ISSUE FOUND: meta_sdk_query returned data but totals are 0!")
            else:
                print("\n✅ SUCCESS: meta_sdk_query correctly returns today's data!")
        else:
            print("❌ ISSUE: Empty list returned!")
    elif isinstance(result, dict):
        if 'error' in result:
            print(f"❌ ERROR: {result}")
        else:
            print(f"Result: {json.dumps(result, indent=2, default=str)}")
    else:
        print(f"Unexpected result: {result}")
    

if __name__ == "__main__":
    test_meta_sdk_query_today()