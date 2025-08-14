"""
Test the SDK directly without the tool wrapper
"""
import os
import asyncio
from dotenv import load_dotenv
from src.tools.meta_ads_tools import DynamicMetaSDK

load_dotenv()

async def test_sdk_directly():
    """Test SDK methods directly"""
    
    sdk = DynamicMetaSDK()
    
    print("🔍 Testing Direct SDK Methods")
    print("=" * 50)
    
    # Test 1: Get all campaigns
    print("\n1. Testing get_all_campaigns()...")
    try:
        campaigns = sdk.get_all_campaigns(limit=5)
        if isinstance(campaigns, dict) and "error" in campaigns:
            print(f"   ❌ Error: {campaigns['error']}")
        else:
            print(f"   ✅ Found {len(campaigns)} campaigns")
            if campaigns:
                print(f"   First campaign: {campaigns[0].get('name', 'Unknown')}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 2: Execute a query
    print("\n2. Testing execute_query()...")
    query = {
        "operation": "get_all_campaigns",
        "fields": ["name", "status", "objective"],
        "limit": 3
    }
    try:
        result = sdk.execute_query(query)
        if isinstance(result, dict) and "error" in result:
            print(f"   ❌ Error: {result['error']}")
        else:
            print(f"   ✅ Query executed successfully")
            if isinstance(result, list):
                print(f"   Found {len(result)} items")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 3: Understand a request
    print("\n3. Testing understand_request()...")
    try:
        understanding = await sdk.understand_request("Show me campaign performance")
        print(f"   ✅ Request understood as: {understanding}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_sdk_directly())