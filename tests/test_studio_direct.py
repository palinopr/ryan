#!/usr/bin/env python3
"""
Test the agent directly like the Studio UI does - without providing campaign_id
This simulates clicking in the Studio UI and typing a message
"""
import asyncio
from langgraph_sdk import get_client

async def test_studio_direct():
    """Test exactly like the Studio UI - just sending a message"""
    
    print("=" * 70)
    print("🎮 TESTING LIKE STUDIO UI (Direct Message)")
    print("=" * 70)
    print("Simulating: User types in Studio UI without any campaign_id")
    print("=" * 70)
    
    # Connect to the local LangGraph server
    client = get_client(url="http://localhost:8123")
    
    try:
        print("\n⏳ Sending message just like Studio UI would...")
        
        # This is exactly what the Studio UI sends - just a message, no campaign_id
        async for chunk in client.runs.stream(
            None,  # No thread (creates new)
            "agent",  # Assistant name
            input={
                "messages": [{
                    "role": "human",
                    "content": "Can you give me a summary of how our current Facebook ad campaign is performing? What's our return on ad spend?"
                }]
                # NOTE: No campaign_id, date_range, or other fields!
            },
            stream_mode="updates"
        ):
            if chunk.event == "updates":
                data = chunk.data
                
                # Print what's happening
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key == "performance_data" and value:
                            print(f"\n✅ Fetched data for campaign: {value.get('campaign_name', 'Unknown')}")
                            print(f"   Campaign ID: {value.get('campaign_id', 'Unknown')}")
                            print(f"   Status: {value.get('status', 'Unknown')}")
                            print(f"   Spend: ${value.get('total_spend', 0):,.2f}")
                            print(f"   CTR: {value.get('average_ctr', 0):.2f}%")
                        
                        elif key == "roas_data" and value:
                            print(f"\n💰 ROAS: {value.get('roas', 0):.2f}x")
                            print(f"   Revenue: ${value.get('total_revenue', 0):,.2f}")
                        
                        elif key == "answer" and value:
                            print("\n" + "=" * 70)
                            print("📢 AGENT'S ANSWER:")
                            print("=" * 70)
                            print(value)
                        
                        elif key == "error" and value:
                            print(f"\n❌ ERROR: {value}")
        
        print("\n" + "=" * 70)
        print("✅ Test completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 Testing agent exactly like Studio UI does")
    print("   (No campaign_id in input, should use default from .env)")
    print("")
    
    asyncio.run(test_studio_direct())