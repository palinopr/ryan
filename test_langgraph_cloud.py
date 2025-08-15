#!/usr/bin/env python3
"""Test LangGraph Cloud Deployment with typo queries"""
import os
import asyncio
from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv()

async def test_cloud_deployment():
    """Test the cloud deployment with various queries"""
    
    # Initialize the LangGraph client
    # For local testing, use localhost:8000
    client = get_client(url="http://localhost:8000")
    
    print("🚀 Testing LangGraph Deployment")
    print("=" * 60)
    
    # Test queries with typos
    test_queries = [
        ("Which is the best citie", "Testing original typo"),
        ("wat is the bst performing city", "Multiple typos"),
        ("how many sales", "Correct query for comparison"),
        ("show me miami performnce", "City with typo"),
    ]
    
    for query, description in test_queries:
        print(f"\n📝 {description}")
        print(f"Query: '{query}'")
        print("-" * 40)
        
        try:
            # Create a thread
            thread = await client.threads.create()
            
            # Run the supervisor graph
            result = await client.runs.create(
                thread_id=thread["thread_id"],
                assistant_id="supervisor",  # The graph name
                input={
                    "messages": [{"role": "user", "content": query}],
                    "phone_number": "+13054870475",
                    "contact_id": "test123"
                }
            )
            
            # Wait for completion
            await client.runs.wait(
                thread_id=thread["thread_id"],
                run_id=result["run_id"]
            )
            
            # Get the final state
            state = await client.threads.get_state(
                thread_id=thread["thread_id"]
            )
            
            # Check the results
            values = state.get("values", {})
            
            # Check intent
            intent = values.get("intent", "unknown")
            print(f"✓ Intent: {intent}")
            
            # Check if query was corrected
            current_request = values.get("current_request", query)
            if current_request != query:
                print(f"✓ Corrected: '{query}' → '{current_request}'")
            
            # Check final response
            final_response = values.get("final_response", "")
            if final_response:
                # Check if we got city data
                if any(city in final_response.lower() for city in ["brooklyn", "miami", "houston", "chicago"]):
                    print(f"✅ Got city performance data!")
                    print(f"Response preview: {final_response[:200]}...")
                else:
                    print(f"⚠️ Generic response: {final_response[:150]}")
            
            # Check messages
            messages = values.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    content = last_message.content
                elif isinstance(last_message, dict):
                    content = last_message.get('content', '')
                else:
                    content = str(last_message)
                
                if "brooklyn" in content.lower() or "sales" in content.lower():
                    print(f"✅ Response contains actual data")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Test Complete")
    print("=" * 60)

async def test_streaming():
    """Test streaming responses"""
    
    client = get_client(url="http://localhost:8000")
    
    print("\n🔄 Testing Streaming Response")
    print("=" * 60)
    
    try:
        # Create a thread
        thread = await client.threads.create()
        
        # Stream the response
        async for chunk in client.runs.stream(
            thread_id=thread["thread_id"],
            assistant_id="supervisor",
            input={
                "messages": [{"role": "user", "content": "Which is the best city"}],
                "phone_number": "+13054870475",
                "contact_id": "test123"
            },
            stream_mode=["updates", "values"]
        ):
            # Process streaming chunks
            if chunk.get("event") == "updates":
                updates = chunk.get("data", {})
                if "intent" in updates:
                    print(f"Intent detected: {updates['intent']}")
                if "current_request" in updates:
                    print(f"Processing: {updates['current_request']}")
            elif chunk.get("event") == "values":
                values = chunk.get("data", {})
                if "final_response" in values:
                    response = values["final_response"]
                    if response:
                        print(f"\nFinal response received:")
                        print(response[:300])
                        break
    
    except Exception as e:
        print(f"❌ Streaming error: {e}")

if __name__ == "__main__":
    print("Testing LangGraph Cloud Deployment\n")
    
    # Run the tests
    asyncio.run(test_cloud_deployment())
    
    # Test streaming
    asyncio.run(test_streaming())