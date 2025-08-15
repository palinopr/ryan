#!/usr/bin/env python3
"""
Test what query structure the AI generates for today requests
"""

import os
import sys
import json
import asyncio
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from src.agents.meta_campaign_agent import plan_and_execute_dynamic_queries

async def test_query_generation():
    """Test what query the AI generates for 'today' requests"""
    
    print("="*100)
    print("TESTING QUERY GENERATION FOR TODAY")
    print("="*100)
    
    # Monkey-patch to intercept the queries
    original_invoke = None
    captured_queries = []
    
    def capture_invoke(self, input_dict):
        """Capture the query being sent"""
        captured_queries.append(input_dict)
        print("\n📦 CAPTURED QUERY TO meta_sdk_query.invoke():")
        print(json.dumps(input_dict, indent=2))
        
        # Return fake data to avoid actual API call
        return [
            {
                "adset_name": "Test City",
                "impressions": "1000",
                "clicks": "100",
                "spend": "50.00"
            }
        ]
    
    # Patch the function
    from src.tools import meta_ads_tools
    original_invoke = meta_ads_tools.meta_sdk_query.invoke
    meta_ads_tools.meta_sdk_query.invoke = capture_invoke
    
    try:
        # Test 1: Query for today
        print("\n" + "="*50)
        print("TEST 1: How many tickets sold today")
        print("="*50)
        
        result = await plan_and_execute_dynamic_queries(
            question="How many tickets sold today",
            campaign_id="120232002620350525",
            date_hint="today",
            language="en"
        )
        
        print(f"\nResult: {result}")
        
        # Test 2: Query for all-time
        captured_queries.clear()
        
        print("\n" + "="*50)
        print("TEST 2: How many tickets sold (all-time)")
        print("="*50)
        
        result = await plan_and_execute_dynamic_queries(
            question="How many tickets sold",
            campaign_id="120232002620350525",
            date_hint="maximum",
            language="en"
        )
        
        print(f"\nResult: {result}")
        
    finally:
        # Restore original
        meta_ads_tools.meta_sdk_query.invoke = original_invoke
    
    print("\n" + "="*100)
    print("ANALYSIS:")
    print("="*100)
    
    if captured_queries:
        first_query = captured_queries[0]
        if "query" in first_query:
            inner_query = first_query["query"]
            print(f"Query structure: Wrapped in 'query' key")
            print(f"Inner query keys: {list(inner_query.keys())}")
            
            # Check for nested params
            if "params" in inner_query:
                print("❌ ISSUE FOUND: Query has nested 'params' structure!")
                print(f"   params content: {inner_query['params']}")
                if "date_preset" in inner_query.get("params", {}):
                    print(f"   date_preset is in params: {inner_query['params']['date_preset']}")
            elif "date_preset" in inner_query:
                print("✅ Query has flat structure with date_preset at top level")
                print(f"   date_preset value: {inner_query['date_preset']}")

if __name__ == "__main__":
    asyncio.run(test_query_generation())