#!/usr/bin/env python3
"""
Test the local LangGraph deployment
"""
import asyncio
import json
from langgraph_sdk import get_client

async def test_meta_agent():
    """Test querying sales data through meta_agent"""
    client = get_client(url="http://localhost:2024")
    
    # Test 1: Ask for today's sales
    print("=" * 50)
    print("TEST 1: Asking for today's sales")
    print("=" * 50)
    
    response_data = None
    async for chunk in client.runs.stream(
        None,  # Threadless run
        "meta_agent",  # Using meta_agent directly
        input={
            "messages": [{
                "role": "user",
                "content": "how many sales today"
            }]
        },
        stream_mode="values"
    ):
        if chunk.event == "values":
            response_data = chunk.data
            print(f"Event: {chunk.event}")
            if "messages" in chunk.data:
                for msg in chunk.data["messages"]:
                    if hasattr(msg, "content"):
                        print(f"Response: {msg.content}")
    
    print("\n" + "=" * 50)
    print("TEST 2: Asking for all-time sales")
    print("=" * 50)
    
    async for chunk in client.runs.stream(
        None,  # Threadless run
        "meta_agent",
        input={
            "messages": [{
                "role": "user", 
                "content": "how many sales"
            }]
        },
        stream_mode="values"
    ):
        if chunk.event == "values":
            print(f"Event: {chunk.event}")
            if "messages" in chunk.data:
                for msg in chunk.data["messages"]:
                    if hasattr(msg, "content"):
                        print(f"Response: {msg.content}")
    
    print("\n" + "=" * 50)
    print("TEST 3: Asking for yesterday's sales")
    print("=" * 50)
    
    async for chunk in client.runs.stream(
        None,
        "meta_agent",
        input={
            "messages": [{
                "role": "user",
                "content": "how many sales yesterday"
            }]
        },
        stream_mode="values"
    ):
        if chunk.event == "values":
            print(f"Event: {chunk.event}")
            if "messages" in chunk.data:
                for msg in chunk.data["messages"]:
                    if hasattr(msg, "content"):
                        print(f"Response: {msg.content}")

if __name__ == "__main__":
    print("Testing Local LangGraph Deployment")
    print("Server: http://localhost:2024")
    print()
    
    asyncio.run(test_meta_agent())