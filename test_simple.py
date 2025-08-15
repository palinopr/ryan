#!/usr/bin/env python3
"""
Simple test of the local LangGraph deployment without streaming
"""
import requests
import json

def test_meta_agent():
    """Test the meta_agent with simple POST requests"""
    
    url = "http://localhost:2024/runs"
    
    # Test 1: Today's sales
    print("=" * 50)
    print("TEST 1: Asking for today's sales")
    print("=" * 50)
    
    payload = {
        "assistant_id": "meta_agent",
        "input": {
            "messages": [{
                "role": "user",
                "content": "how many sales today"
            }]
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "output" in data and "messages" in data["output"]:
                for msg in data["output"]["messages"]:
                    if isinstance(msg, dict) and "content" in msg:
                        print(f"Response: {msg['content']}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Test 2: All-time sales
    print("=" * 50)
    print("TEST 2: Asking for all-time sales")
    print("=" * 50)
    
    payload["input"]["messages"][0]["content"] = "how many sales"
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "output" in data and "messages" in data["output"]:
                for msg in data["output"]["messages"]:
                    if isinstance(msg, dict) and "content" in msg:
                        print(f"Response: {msg['content']}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing Local LangGraph Deployment (Non-streaming)")
    print("Server: http://localhost:2024")
    print()
    
    test_meta_agent()