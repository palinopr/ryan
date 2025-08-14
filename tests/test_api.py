#!/usr/bin/env python3
"""
Test Ryan's Assistant via LangGraph API
"""
import requests
import json

# Test the LangGraph API
base_url = "http://localhost:8123"

print("=" * 70)
print("🎤 TESTING RYAN'S ASSISTANT VIA API")
print("=" * 70)

# Check health
response = requests.get(f"{base_url}/ok")
print(f"Health Check: {response.json()}")

# Try to invoke the agent
print("\nTesting agent invocation...")

# Create a thread
thread_response = requests.post(
    f"{base_url}/threads",
    headers={"Content-Type": "application/json"},
    json={}
)

if thread_response.status_code == 200:
    thread_id = thread_response.json().get("thread_id")
    print(f"Thread created: {thread_id}")
    
    # Send a message
    message_data = {
        "messages": [
            {
                "role": "human",
                "content": "How is my SENDÉ tour campaign doing?"
            }
        ]
    }
    
    # Invoke the agent
    invoke_response = requests.post(
        f"{base_url}/threads/{thread_id}/runs",
        headers={"Content-Type": "application/json"},
        json={
            "assistant_id": "agent",
            "input": message_data
        }
    )
    
    print(f"Invoke status: {invoke_response.status_code}")
    if invoke_response.status_code == 200:
        print("Response:", invoke_response.json())
else:
    print(f"Thread creation failed: {thread_response.status_code}")
    print(thread_response.text)

print("\n" + "=" * 70)
print("To visualize the graph, install LangGraph Studio:")
print("https://github.com/langchain-ai/langgraph-studio")
print("=" * 70)