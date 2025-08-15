#!/usr/bin/env python3
"""Test cloud deployment API directly"""

import requests
import json
import time

def test_typo_query():
    """Test the supervisor with a typo query"""
    
    print("🚀 Testing LangGraph API with Typo Query")
    print("="*60)
    
    # The problematic query from the trace
    query = "Which is the best citie"
    
    print(f"Query: '{query}'")
    print("-"*40)
    
    # Prepare the request
    url = "http://localhost:8000/supervisor/invoke"
    payload = {
        "input": {
            "messages": [{"role": "user", "content": query}],
            "phone_number": "+13054870475",
            "contact_id": "test_123"
        },
        "config": {
            "configurable": {
                "thread_id": "test_thread_typo_1"
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("Sending request...")
        start_time = time.time()
        
        # Send request with timeout
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        elapsed = time.time() - start_time
        print(f"Response received in {elapsed:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract output
            output = result.get("output", {})
            
            # Check intent
            intent = output.get("intent", "unknown")
            print(f"\n✓ Intent: {intent}")
            
            # Check if query was corrected
            current_request = output.get("current_request", query)
            if current_request != query:
                print(f"✅ Query corrected: '{query}' → '{current_request}'")
            else:
                print(f"⚠️ No correction applied")
            
            # Check language
            language = output.get("language", "unknown")
            print(f"Language: {language}")
            
            # Check final response
            final_response = output.get("final_response", "")
            if final_response:
                print(f"\nFinal Response:")
                print("-"*40)
                # Check if we got city data
                cities = ["brooklyn", "miami", "houston", "chicago", "los angeles"]
                has_city_data = any(city in final_response.lower() for city in cities)
                
                if has_city_data:
                    print("✅ Got city performance data!")
                    # Show relevant parts
                    lines = final_response.split('\n')
                    for line in lines[:10]:
                        if any(city in line.lower() for city in cities):
                            print(f"  → {line}")
                else:
                    print("❌ No city data found")
                    print(f"Response: {final_response[:200]}...")
            
            # Check meta response
            meta_response = output.get("meta_response", {})
            if meta_response:
                if meta_response.get("success"):
                    print("\n✅ Meta agent responded successfully")
                    data = meta_response.get("data", "")
                    if "brooklyn" in str(data).lower() or "miami" in str(data).lower():
                        print("✅ Meta response contains city data")
                
            # Save full response for debugging
            with open("test_response.json", "w") as f:
                json.dump(result, f, indent=2)
                print("\n📄 Full response saved to test_response.json")
            
        else:
            print(f"❌ HTTP {response.status_code}")
            print(f"Error: {response.text[:500]}")
            
    except requests.Timeout:
        print("❌ Request timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
    
    print("\n" + "="*60)

def test_correct_query():
    """Test with a correct query for comparison"""
    
    print("\n🎯 Testing with Correct Query")
    print("="*60)
    
    query = "Which city has the best performance"
    
    print(f"Query: '{query}'")
    print("-"*40)
    
    url = "http://localhost:8000/supervisor/invoke"
    payload = {
        "input": {
            "messages": [{"role": "user", "content": query}],
            "phone_number": "+13054870475",
            "contact_id": "test_123"
        },
        "config": {
            "configurable": {
                "thread_id": "test_thread_correct_1"
            }
        }
    }
    
    try:
        print("Sending request...")
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            output = result.get("output", {})
            
            intent = output.get("intent", "unknown")
            print(f"✓ Intent: {intent}")
            
            final_response = output.get("final_response", "")
            if "brooklyn" in final_response.lower() or "miami" in final_response.lower():
                print("✅ Got city performance data!")
            else:
                print("❌ No city data in response")
                
        else:
            print(f"❌ HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("="*60)

if __name__ == "__main__":
    # Test with typo
    test_typo_query()
    
    # Test with correct query
    test_correct_query()
    
    print("\n✅ Tests Complete")