#!/usr/bin/env python3
"""
Test streaming from the LangGraph server
"""
import requests
import json

def test_streaming():
    """Test the meta_agent with streaming"""
    
    url = "http://localhost:2024/runs/stream"
    
    # Test: Today's sales
    print("=" * 50)
    print("Asking: how many sales today")
    print("=" * 50)
    
    payload = {
        "assistant_id": "meta_agent",
        "input": {
            "messages": [{
                "role": "user",
                "content": "how many sales today"
            }]
        },
        "stream_mode": "values"
    }
    
    try:
        response = requests.post(url, json=payload, stream=True, timeout=30)
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    if data_str and data_str != '[DONE]':
                        try:
                            data = json.loads(data_str)
                            # Look for the final answer in messages
                            if 'messages' in data:
                                for msg in data['messages']:
                                    if isinstance(msg, dict):
                                        role = msg.get('type', msg.get('role'))
                                        content = msg.get('content', '')
                                        if role in ['ai', 'assistant'] and content:
                                            print(f"\n📊 Answer: {content}")
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing LangGraph Streaming Response")
    print("Server: http://localhost:2024")
    print()
    
    test_streaming()