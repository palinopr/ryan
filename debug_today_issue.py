#!/usr/bin/env python3
"""
Debug why system returns 0 when Meta SDK shows data for today
"""

import os
import sys
import json
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.tools.meta_ads_tools import DynamicMetaSDK
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_today_query():
    """Debug the exact flow when querying for today"""
    
    print("="*100)
    print("🔍 DEBUGGING TODAY QUERY ISSUE")
    print("="*100)
    
    # Initialize tools
    tools = DynamicMetaSDK()
    print(f"✅ DynamicMetaSDK initialized")
    print(f"   Access Token: {'✅ Set' if tools.access_token else '❌ Missing'}")
    
    campaign_id = "120232002620350525"
    print(f"\n📊 Testing Campaign: {campaign_id}")
    
    # Test 1: Direct get_adsets_insights with 'today'
    print("\n" + "-"*50)
    print("TEST 1: get_adsets_insights with date_preset='today'")
    print("-"*50)
    
    result_today = tools.get_adsets_insights(
        campaign_id=campaign_id,
        date_preset="today",
        fields=['impressions', 'clicks', 'spend', 'actions', 'action_values']
    )
    
    print(f"\n📊 Results for TODAY:")
    print(f"   Records returned: {len(result_today)}")
    
    if result_today:
        total_impressions = 0
        total_clicks = 0
        total_spend = 0
        total_purchases = 0
        
        for r in result_today:
            imp = int(r.get('impressions', 0))
            clicks = int(r.get('clicks', 0))
            spend = float(r.get('spend', 0))
            
            total_impressions += imp
            total_clicks += clicks
            total_spend += spend
            
            # Check for purchases
            actions = r.get('actions', [])
            for action in actions:
                if 'purchase' in action.get('action_type', ''):
                    total_purchases += int(action.get('value', 0))
            
            print(f"\n   AdSet: {r.get('adset_name', 'Unknown')}")
            print(f"     Impressions: {imp}")
            print(f"     Clicks: {clicks}")
            print(f"     Spend: ${spend}")
        
        print(f"\n   TOTALS:")
        print(f"     Total Impressions: {total_impressions}")
        print(f"     Total Clicks: {total_clicks}")
        print(f"     Total Spend: ${total_spend:.2f}")
        print(f"     Total Purchases: {total_purchases}")
    else:
        print("   ❌ No data returned!")
    
    # Test 2: Execute query through the wrapper
    print("\n" + "-"*50)
    print("TEST 2: execute_query with get_adsets_insights operation")
    print("-"*50)
    
    query = {
        "operation": "get_adsets_insights",
        "campaign_id": campaign_id,
        "date_preset": "today",
        "fields": ['impressions', 'clicks', 'spend', 'actions', 'action_values']
    }
    
    result_execute = tools.execute_query(query)
    
    print(f"\n📊 Results from execute_query:")
    print(f"   Type: {type(result_execute)}")
    
    if isinstance(result_execute, list):
        print(f"   Records: {len(result_execute)}")
        if result_execute:
            print(f"   First record: {json.dumps(result_execute[0], indent=2, default=str)[:500]}")
    elif isinstance(result_execute, dict) and 'error' in result_execute:
        print(f"   ❌ Error: {result_execute['error']}")
    else:
        print(f"   Result: {result_execute}")
    
    # Test 3: Check what the system does with the query
    print("\n" + "-"*50)
    print("TEST 3: Simulating system query flow")
    print("-"*50)
    
    # This simulates what plan_and_execute_dynamic_queries does
    system_query = {
        "queries": [
            {
                "operation": "get_adsets_insights",
                "query": {
                    "campaign_id": campaign_id,
                    "date_preset": "today",
                    "fields": ["impressions", "clicks", "spend", "ctr", "cpc", "cpm", "actions", "action_values", "purchase_roas"]
                }
            }
        ]
    }
    
    print(f"System query structure:")
    print(json.dumps(system_query, indent=2))
    
    # Execute like the system does
    for q in system_query['queries']:
        if 'query' in q:
            # This is how meta_sdk_query.invoke does it
            actual_query = q['query']
            actual_query['operation'] = q['operation']
        else:
            actual_query = q
        
        print(f"\nExecuting query:")
        print(json.dumps(actual_query, indent=2))
        
        result = tools.execute_query(actual_query)
        
        if result:
            print(f"✅ Got {len(result) if isinstance(result, list) else 'some'} results")
        else:
            print(f"❌ No results!")
    
    print("\n" + "="*100)
    print("💡 DIAGNOSIS:")
    print("="*100)
    
    if not result_today:
        print("""
    The get_adsets_insights function returned no data for 'today'.
    
    Possible issues:
    1. Permission/access check failing
    2. Error in the SDK call being silently caught
    3. Campaign ID mismatch
    4. Date handling issue in the Meta SDK wrapper
    
    Check the debug logs above for warnings/errors.
        """)
    else:
        print(f"""
    The function returned data successfully!
    - {total_impressions} impressions
    - {total_clicks} clicks  
    - ${total_spend:.2f} spend
    - {total_purchases} purchases
    
    If the system still shows 0, the issue is in how the response is formatted.
        """)

if __name__ == "__main__":
    debug_today_query()