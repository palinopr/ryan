#!/usr/bin/env python3
"""
Test if the fix works for nested params structure
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from src.tools.meta_ads_tools import meta_sdk_query
import json

def test_nested_params():
    """Test both flat and nested query structures"""
    
    print("="*100)
    print("TESTING FIX FOR NESTED PARAMS STRUCTURE")
    print("="*100)
    
    # Test 1: Nested structure (what AI generates)
    nested_query = {
        "operation": "get_adsets_insights",
        "object_id": "120232002620350525",
        "fields": ["impressions", "clicks", "spend"],
        "params": {
            "date_preset": "today",
            "level": "adset"
        }
    }
    
    print("\nTEST 1: Nested params structure")
    print("Query:")
    print(json.dumps(nested_query, indent=2))
    
    result = meta_sdk_query.invoke({"query": nested_query})
    
    if isinstance(result, list) and result:
        total_imp = sum(int(item.get('impressions', 0)) for item in result if isinstance(item, dict))
        total_spend = sum(float(item.get('spend', 0)) for item in result if isinstance(item, dict))
        print(f"\n✅ SUCCESS: Got {len(result)} records")
        print(f"   Total Impressions: {total_imp}")
        print(f"   Total Spend: ${total_spend:.2f}")
    else:
        print(f"\n❌ FAILED: {result}")
    
    # Test 2: Flat structure (backward compatibility)
    flat_query = {
        "operation": "get_adsets_insights",
        "campaign_id": "120232002620350525",
        "date_preset": "today",
        "fields": ["impressions", "clicks", "spend"],
        "level": "adset"
    }
    
    print("\n" + "-"*50)
    print("\nTEST 2: Flat structure (backward compatibility)")
    print("Query:")
    print(json.dumps(flat_query, indent=2))
    
    result = meta_sdk_query.invoke({"query": flat_query})
    
    if isinstance(result, list) and result:
        total_imp = sum(int(item.get('impressions', 0)) for item in result if isinstance(item, dict))
        total_spend = sum(float(item.get('spend', 0)) for item in result if isinstance(item, dict))
        print(f"\n✅ SUCCESS: Got {len(result)} records")
        print(f"   Total Impressions: {total_imp}")
        print(f"   Total Spend: ${total_spend:.2f}")
    else:
        print(f"\n❌ FAILED: {result}")
    
    # Test 3: Mixed structure (date_preset flat, other params nested)
    mixed_query = {
        "operation": "get_adsets_insights",
        "campaign_id": "120232002620350525",
        "date_preset": "today",  # Flat
        "fields": ["impressions", "clicks", "spend"],
        "params": {
            "level": "adset"  # Nested
        }
    }
    
    print("\n" + "-"*50)
    print("\nTEST 3: Mixed structure")
    print("Query:")
    print(json.dumps(mixed_query, indent=2))
    
    result = meta_sdk_query.invoke({"query": mixed_query})
    
    if isinstance(result, list) and result:
        total_imp = sum(int(item.get('impressions', 0)) for item in result if isinstance(item, dict))
        total_spend = sum(float(item.get('spend', 0)) for item in result if isinstance(item, dict))
        print(f"\n✅ SUCCESS: Got {len(result)} records")
        print(f"   Total Impressions: {total_imp}")
        print(f"   Total Spend: ${total_spend:.2f}")
    else:
        print(f"\n❌ FAILED: {result}")
    
    print("\n" + "="*100)
    print("SUMMARY: All query structures should now work with 'today' preset!")

if __name__ == "__main__":
    test_nested_params()