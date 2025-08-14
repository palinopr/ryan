"""
Test the LangGraph Studio API directly
"""
import requests
import json

def test_studio_api():
    """Test calling the Studio API"""
    
    # Studio API endpoint
    base_url = "http://localhost:2024"
    
    print("🔍 Testing LangGraph Studio API")
    print("=" * 50)
    
    # Test 1: Get assistants
    print("\n1. Getting assistants...")
    try:
        response = requests.get(f"{base_url}/assistants")
        if response.status_code == 200:
            assistants = response.json()
            print(f"   ✅ Found {len(assistants)} assistants")
            for assistant in assistants:
                print(f"      - {assistant.get('graph_id', 'unknown')}")
        else:
            print(f"   ❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Test Meta agent with intelligent query
    print("\n2. Testing Meta agent...")
    
    payload = {
        "messages": [
            {
                "content": "Show me how my campaigns are performing",
                "type": "human"
            }
        ]
    }
    
    try:
        # Create a thread
        thread_response = requests.post(
            f"{base_url}/threads",
            json={}
        )
        
        if thread_response.status_code != 200:
            print(f"   ❌ Failed to create thread: {thread_response.status_code}")
            return
        
        thread = thread_response.json()
        thread_id = thread["thread_id"]
        print(f"   ✅ Created thread: {thread_id}")
        
        # Run the graph
        run_response = requests.post(
            f"{base_url}/threads/{thread_id}/runs",
            json={
                "assistant_id": "meta_agent",
                "input": payload,
                "stream_mode": "values"
            }
        )
        
        if run_response.status_code == 200:
            print("   ✅ Run started successfully")
            
            # Stream the response
            for line in run_response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8').replace('data: ', ''))
                        if 'messages' in data:
                            for msg in data['messages']:
                                if msg.get('type') == 'ai':
                                    print(f"\n   Response: {msg.get('content', '')[:200]}...")
                    except:
                        pass
        else:
            print(f"   ❌ Failed to run: {run_response.status_code}")
            print(f"   Response: {run_response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_studio_api()