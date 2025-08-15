#!/usr/bin/env python3
"""Test cloud deployment with typo queries"""
import os
import asyncio
import aiohttp
import json
from dotenv import load_dotenv

load_dotenv()

# Cloud deployment endpoint
CLOUD_URL = os.getenv("LANGGRAPH_CLOUD_URL", "https://api.langsmith.com")
API_KEY = os.getenv("LANGCHAIN_API_KEY")

async def test_cloud_query(query: str):
    """Test a query against the cloud deployment"""
    
    print(f"\n{'='*60}")
    print(f"Testing: '{query}'")
    print('='*60)
    
    # Prepare the request
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY if API_KEY else "",
    }
    
    # Payload for the supervisor graph
    payload = {
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "phone_number": "+13054870475",  # Admin phone
        "contact_id": "test_contact_123"
    }
    
    # Check if we're using local or cloud
    # For local testing via the LangGraph Studio API
    local_url = "http://localhost:8000/supervisor/invoke"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Try local deployment first
            async with session.post(
                local_url,
                json={"input": payload},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Extract key information
                    output = result.get("output", {})
                    
                    # Check intent
                    intent = output.get("intent", "unknown")
                    print(f"Intent Detected: {intent}")
                    
                    # Check if query was corrected
                    current_request = output.get("current_request", query)
                    if current_request != query:
                        print(f"✅ Query Corrected: '{query}' → '{current_request}'")
                    else:
                        print(f"⚠️ No correction applied")
                    
                    # Check language
                    language = output.get("language", "unknown")
                    print(f"Language: {language}")
                    
                    # Check final response
                    final_response = output.get("final_response", "No response")
                    
                    # Check if we got city data
                    if any(city in final_response.lower() for city in ["brooklyn", "miami", "houston", "chicago", "los angeles"]):
                        print(f"✅ Got city performance data!")
                        print(f"Response preview: {final_response[:200]}...")
                    else:
                        print(f"❌ Generic response: {final_response[:200]}")
                    
                    # Check meta response
                    meta_response = output.get("meta_response", {})
                    if meta_response and meta_response.get("data"):
                        data = meta_response["data"]
                        if "brooklyn" in data.lower() or "miami" in data.lower():
                            print("✅ Meta agent returned city data")
                    
                    return result
                else:
                    print(f"❌ Error: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"Error details: {error_text[:500]}")
                    
        except aiohttp.ClientError as e:
            print(f"❌ Connection error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    return None

async def main():
    """Run test queries"""
    
    print("🚀 Testing Cloud Deployment with Typo Queries")
    print("=" * 60)
    
    # Test queries with typos
    test_queries = [
        "Which is the best citie",  # Original problematic query
        "wat is the bst performing city",  # Multiple typos
        "hw many sales for miami",  # Typo in "how"
        "show me brookln performance",  # Typo in "Brooklyn"
        "which city has most sales",  # Correct query for comparison
    ]
    
    for query in test_queries:
        result = await test_cloud_query(query)
        await asyncio.sleep(1)  # Small delay between requests
    
    print("\n" + "=" * 60)
    print("✅ Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())