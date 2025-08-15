#!/usr/bin/env python3
"""Test LangGraph deployment with typo queries using SDK"""
import os
import asyncio
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Import langgraph SDK
try:
    from langgraph_sdk import get_client
    HAS_SDK = True
except ImportError:
    HAS_SDK = False
    print("Warning: langgraph-sdk not installed. Using HTTP client.")

# For fallback HTTP testing
import aiohttp

load_dotenv()

async def test_with_sdk():
    """Test using LangGraph SDK"""
    if not HAS_SDK:
        print("Skipping SDK test - langgraph-sdk not installed")
        return
    
    print("🚀 Testing with LangGraph SDK")
    print("="*60)
    
    # Get client for local deployment
    client = get_client(url="http://localhost:8000")
    
    # Test queries
    test_queries = [
        ("Which is the best citie", "Original typo from trace"),
        ("wat is the bst performing city", "Multiple typos"),
        ("show me brookln sales", "City name typo"),
        ("Which city has the most sales", "Correct query for comparison"),
    ]
    
    for query, description in test_queries:
        print(f"\n📝 {description}")
        print(f"Query: '{query}'")
        print("-"*40)
        
        try:
            # Create thread
            thread = await client.threads.create()
            
            # Run the graph
            run = await client.runs.create(
                thread_id=thread["thread_id"],
                assistant_id="supervisor",
                input={
                    "messages": [{"role": "user", "content": query}],
                    "phone_number": "+13054870475",
                    "contact_id": "test_123"
                }
            )
            
            # Wait for completion
            await client.runs.wait(thread_id=thread["thread_id"], run_id=run["run_id"])
            
            # Get state
            state = await client.threads.get_state(thread_id=thread["thread_id"])
            
            # Analyze results
            values = state.get("values", {})
            
            # Check intent detection
            intent = values.get("intent", "unknown")
            print(f"✓ Intent: {intent}")
            
            # Check query correction
            corrected = values.get("current_request", query)
            if corrected != query:
                print(f"✅ Query corrected: '{query}' → '{corrected}'")
            
            # Check final response
            final_response = values.get("final_response", "")
            meta_response = values.get("meta_response", {})
            
            # Look for city data
            has_city_data = False
            if final_response:
                cities = ["brooklyn", "miami", "houston", "chicago", "los angeles"]
                if any(city in final_response.lower() for city in cities):
                    has_city_data = True
                    print(f"✅ Got city performance data!")
                    # Show snippet
                    lines = final_response.split('\n')
                    for line in lines[:5]:
                        if any(city in line.lower() for city in cities):
                            print(f"  → {line[:80]}")
            
            if meta_response.get("data"):
                data_str = str(meta_response["data"]).lower()
                if "brooklyn" in data_str or "miami" in data_str:
                    has_city_data = True
                    print("✅ Meta agent returned city data")
            
            if not has_city_data:
                print(f"❌ No city data found in response")
                if final_response:
                    print(f"Response preview: {final_response[:150]}...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "="*60)

async def test_with_http():
    """Test using direct HTTP calls"""
    print("\n🌐 Testing with HTTP Client")
    print("="*60)
    
    url = "http://localhost:8000"
    
    # Test query
    query = "Which is the best citie"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Create thread
            async with session.post(f"{url}/threads") as resp:
                if resp.status != 200:
                    print(f"❌ Failed to create thread: {resp.status}")
                    return
                thread = await resp.json()
                thread_id = thread["thread_id"]
            
            print(f"✓ Created thread: {thread_id}")
            
            # Run supervisor
            payload = {
                "assistant_id": "supervisor",
                "input": {
                    "messages": [{"role": "user", "content": query}],
                    "phone_number": "+13054870475",
                    "contact_id": "test_123"
                }
            }
            
            async with session.post(
                f"{url}/threads/{thread_id}/runs",
                json=payload
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Failed to create run: {resp.status}")
                    error = await resp.text()
                    print(f"Error: {error[:200]}")
                    return
                run = await resp.json()
                run_id = run["run_id"]
            
            print(f"✓ Created run: {run_id}")
            
            # Poll for completion
            max_attempts = 30
            for i in range(max_attempts):
                await asyncio.sleep(1)
                
                async with session.get(
                    f"{url}/threads/{thread_id}/runs/{run_id}"
                ) as resp:
                    if resp.status == 200:
                        run_status = await resp.json()
                        status = run_status.get("status")
                        
                        if status == "success":
                            print("✅ Run completed successfully")
                            break
                        elif status == "error":
                            print(f"❌ Run failed: {run_status.get('error')}")
                            return
                        else:
                            if i % 5 == 0:
                                print(f"  ⏳ Status: {status}")
            
            # Get final state
            async with session.get(
                f"{url}/threads/{thread_id}/state"
            ) as resp:
                if resp.status == 200:
                    state = await resp.json()
                    values = state.get("values", {})
                    
                    # Check results
                    intent = values.get("intent", "unknown")
                    print(f"\n✓ Intent detected: {intent}")
                    
                    corrected = values.get("current_request", query)
                    if corrected != query:
                        print(f"✅ Query corrected: '{query}' → '{corrected}'")
                    
                    final_response = values.get("final_response", "")
                    if final_response:
                        if "brooklyn" in final_response.lower():
                            print("✅ Got city performance data!")
                        else:
                            print(f"Response: {final_response[:150]}...")
                    
                else:
                    print(f"❌ Failed to get state: {resp.status}")
                    
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e}")

async def test_invoke_endpoint():
    """Test using the /invoke endpoint"""
    print("\n🎯 Testing /invoke Endpoint")
    print("="*60)
    
    url = "http://localhost:8000/supervisor/invoke"
    
    queries = [
        "Which is the best citie",
        "wat is the bst performing city"
    ]
    
    async with aiohttp.ClientSession() as session:
        for query in queries:
            print(f"\nTesting: '{query}'")
            print("-"*40)
            
            payload = {
                "input": {
                    "messages": [{"role": "user", "content": query}],
                    "phone_number": "+13054870475",
                    "contact_id": "test_123"
                }
            }
            
            try:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        output = result.get("output", {})
                        
                        # Check intent
                        intent = output.get("intent", "unknown")
                        print(f"✓ Intent: {intent}")
                        
                        # Check correction
                        corrected = output.get("current_request", query)
                        if corrected != query:
                            print(f"✅ Corrected: '{query}' → '{corrected}'")
                        
                        # Check response
                        final_response = output.get("final_response", "")
                        if final_response:
                            cities = ["brooklyn", "miami", "houston", "chicago"]
                            if any(city in final_response.lower() for city in cities):
                                print("✅ Got city data!")
                                # Show first city mention
                                for city in cities:
                                    if city in final_response.lower():
                                        idx = final_response.lower().index(city)
                                        snippet = final_response[max(0,idx-20):idx+50]
                                        print(f"  → ...{snippet}...")
                                        break
                            else:
                                print(f"❌ No city data: {final_response[:100]}...")
                    else:
                        print(f"❌ HTTP {resp.status}")
                        error = await resp.text()
                        print(f"Error: {error[:200]}")
                        
            except asyncio.TimeoutError:
                print("❌ Request timed out")
            except Exception as e:
                print(f"❌ Error: {e}")

async def main():
    """Run all tests"""
    print("🔧 LangGraph Deployment Tests")
    print("="*60)
    print(f"SDK Available: {HAS_SDK}")
    print(f"Test URL: http://localhost:8000")
    print("="*60)
    
    # Test with SDK if available
    if HAS_SDK:
        await test_with_sdk()
    
    # Test with HTTP client
    await test_with_http()
    
    # Test invoke endpoint
    await test_invoke_endpoint()
    
    print("\n" + "="*60)
    print("✅ All tests completed")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())