"""
Test script to simulate LangGraph Studio flow
Tests the complete security -> supervisor -> meta -> ghl flow
"""
import asyncio
import os
from langchain_core.messages import HumanMessage
from src.agents.supervisor_agent import supervisor_agent

async def test_studio_flow():
    """Test the flow as it runs in LangGraph Studio"""
    
    print("\n" + "="*70)
    print("🧪 TESTING LANGGRAPH STUDIO FLOW")
    print("="*70)
    
    # Test 1: With phone number (should work)
    print("\n📋 Test 1: WITH phone number (Ryan Admin)")
    print("-"*50)
    
    test_state_with_phone = {
        'messages': [HumanMessage(content='How is Miami campaign performing? What is the ROAS?')],
        'phone_number': '+17865551234',  # Ryan's phone (admin)
        'contact_id': 'test_contact_123'  # Simulate GHL contact
    }
    
    try:
        result = await supervisor_agent.ainvoke(test_state_with_phone)
        
        print(f"✅ Security: {'PASSED' if result.get('is_authorized') else 'FAILED'}")
        if result.get('user_role'):
            print(f"   Role: {result.get('user_role')}")
        
        if result.get('intent'):
            print(f"🎯 Intent detected: {result.get('intent')}")
        
        if result.get('meta_response'):
            meta = result.get('meta_response', {})
            if meta.get('data'):
                print(f"📊 Meta data: Retrieved")
                # Show first 100 chars of data
                data_preview = str(meta.get('data'))[:100]
                print(f"   Preview: {data_preview}...")
        
        if result.get('ghl_message_sent') is not None:
            print(f"📨 GHL message: {'Sent' if result.get('ghl_message_sent') else 'Failed'}")
            if result.get('mcp_instruction'):
                print("   MCP instruction prepared")
        
        if result.get('final_response'):
            print(f"📝 Final response length: {len(result.get('final_response'))} chars")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Without phone number (Studio default)
    print("\n📋 Test 2: WITHOUT phone number (Studio default)")
    print("-"*50)
    
    test_state_no_phone = {
        'messages': [HumanMessage(content='How is Miami campaign performing?')]
        # No phone_number - simulates Studio behavior
    }
    
    try:
        result = await supervisor_agent.ainvoke(test_state_no_phone)
        
        print(f"✅ Security: {'BYPASSED (dev mode)' if result.get('is_authorized') else 'FAILED'}")
        if result.get('user_role'):
            print(f"   Role: {result.get('user_role')} (default)")
        
        if result.get('intent'):
            print(f"🎯 Intent detected: {result.get('intent')}")
        
        if result.get('meta_response'):
            meta = result.get('meta_response', {})
            if meta.get('data'):
                data_preview = str(meta.get('data'))[:100]
                print(f"📊 Meta data preview: {data_preview}...")
        
        if result.get('ghl_message_sent') == False:
            print(f"📨 GHL message: Failed (no contact info)")
            if result.get('error'):
                print(f"   Error: {result.get('error')}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Unauthorized phone
    print("\n📋 Test 3: UNAUTHORIZED phone number")
    print("-"*50)
    
    test_state_unauthorized = {
        'messages': [HumanMessage(content='Show me campaign data')],
        'phone_number': '+19999999999'  # Not authorized
    }
    
    try:
        result = await supervisor_agent.ainvoke(test_state_unauthorized)
        
        print(f"✅ Security: {'PASSED' if result.get('is_authorized') else 'BLOCKED'}")
        if result.get('error'):
            print(f"   Error: {result.get('error')}")
        
        # Should not reach other agents
        if not result.get('meta_response'):
            print("✅ Correctly blocked before reaching Meta agent")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*70)
    print("✅ STUDIO FLOW TESTS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_studio_flow())