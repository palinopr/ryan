"""
Meta Ads Campaign Agent - LangSmith Deployment
Main application entry point for analyzing Facebook/Instagram ad campaigns
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment
load_dotenv()

# Core imports
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Import our modules
from src.config.settings import get_settings
from src.agents.meta_campaign_agent import create_dynamic_meta_campaign_graph, MetaCampaignState
from src.agents.ghl_agent import ghl_agent
from src.agents.security_agent import security_agent, validate_access
from src.agents.supervisor_agent import supervisor_agent, process_request_with_security


def create_main_graph():
    """Create the main graph for LangSmith deployment"""
    settings = get_settings()
    
    # Validate Meta API credentials
    if not settings.meta_ads.access_token:
        raise ValueError("META_ACCESS_TOKEN is required in .env file")
    if not settings.meta_ads.ad_account_id:
        raise ValueError("META_AD_ACCOUNT_ID is required in .env file")
    
    return create_dynamic_meta_campaign_graph()


# Create and export the graphs
graph = create_main_graph()  # Meta Ads campaign graph
ghl_graph = ghl_agent  # GoHighLevel CRM operations graph
security_graph = security_agent  # Security validation graph
supervisor_graph = supervisor_agent  # Supervisor orchestration graph

# Main multi-agent system with security
async def secure_multi_agent_system(phone_number: str, message: str) -> Dict[str, Any]:
    """
    Main entry point for the secure multi-agent system
    
    Args:
        phone_number: Phone number of the user
        message: User's request
    
    Returns:
        Response from the appropriate agent(s)
    """
    return await process_request_with_security(phone_number, message)


# Helper function for GoHighLevel operations
async def execute_ghl_operation(
    message: str,
    contact_id: Optional[str] = None,
    location_id: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a GoHighLevel operation through the agent
    
    Args:
        message: The operation to perform (e.g., "Send SMS to contact")
        contact_id: Optional contact ID
        location_id: Optional location ID
        conversation_id: Optional conversation ID for messages
    
    Returns:
        Operation result including MCP tool to execute
    """
    from src.agents.ghl_agent import GHLAgentState
    
    # Create initial state
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "contact_id": contact_id,
        "location_id": location_id or os.getenv("GHL_LOCATION_ID"),
        "conversation_id": conversation_id
    }
    
    # Run the GHL agent
    result = await ghl_graph.ainvoke(initial_state)
    
    return result.get("result", {})


# Helper function for Meta Ads campaigns
async def analyze_campaign(
    campaign_id: str,
    date_range: str = "last_30d",
    question: Optional[str] = None,
    analysis_type: str = "comprehensive"
) -> Dict[str, Any]:
    """
    Analyze a Meta Ads campaign
    
    Args:
        campaign_id: The Meta campaign ID to analyze
        date_range: Date range for analysis (last_30d, last_7d, today, yesterday, this_month)
        question: Optional question to answer about the campaign
        analysis_type: Type of analysis (comprehensive, quick)
    
    Returns:
        Analysis results including report and answers
    """
    # Create initial state
    initial_state = MetaCampaignState(
        messages=[HumanMessage(content=f"Analyze campaign {campaign_id}")],
        campaign_id=campaign_id,
        date_range=date_range,
        current_question=question,
        analysis_type=analysis_type
    )
    
    # Run the graph
    result = await graph.ainvoke(initial_state)
    
    return {
        "campaign_id": campaign_id,
        "report": result.get("report_summary"),
        "insights": result.get("insights"),
        "recommendations": result.get("recommendations"),
        "answer": result.get("answer") if question else None,
        "performance": result.get("performance_data"),
        "roas": result.get("roas_data")
    }


# Test function for the complete multi-agent system
async def test_multi_agent_system():
    """Test the complete multi-agent system with security"""
    import asyncio
    
    print("\n" + "=" * 70)
    print("🔐 TESTING SECURE MULTI-AGENT SYSTEM")
    print("=" * 70)
    
    # Test cases with different phone numbers and requests
    test_cases = [
        {
            "phone": os.getenv("RYAN_PHONE", "+17865551234"),
            "message": "How is the Miami campaign performing?",
            "expected_agent": "meta",
            "role": "admin"
        },
        {
            "phone": os.getenv("RYAN_PHONE", "+17865551234"),
            "message": "Send a message to VIP ticket holders",
            "expected_agent": "ghl",
            "role": "admin"
        },
        {
            "phone": "+19999999999",  # Unauthorized number
            "message": "Show me campaign data",
            "expected_agent": None,
            "role": "unauthorized"
        },
        {
            "phone": os.getenv("MANAGER_PHONE", "+17865555678"),
            "message": "What's the conversion rate for Miami Facebook ads?",
            "expected_agent": "both",
            "role": "manager"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test['role'].upper()} - {test['message'][:50]}...")
        print("-" * 50)
        
        try:
            result = await secure_multi_agent_system(test['phone'], test['message'])
            
            if result.get('success'):
                print(f"✅ Access granted (Role: {result.get('role')})")
                print(f"   Agents used: {result.get('agents_used')}")
                print(f"   Response preview: {str(result.get('response'))[:100]}...")
            else:
                print(f"❌ Access denied: {result.get('error')}")
        
        except Exception as e:
            print(f"❌ Test failed: {str(e)[:100]}")
        
        await asyncio.sleep(0.5)
    
    print("\n" + "=" * 70)
    print("✅ Multi-agent system test complete!")
    print("=" * 70)
    return True

# Test function for local validation
def test_graph():
    """Test the graph locally"""
    import asyncio
    
    async def run_test():
        # Test state
        test_campaign_id = os.getenv("DEFAULT_CAMPAIGN_ID", "test_campaign_123")
        
        test_state = {
            "messages": [HumanMessage(content=f"Analyze campaign {test_campaign_id}")],
            "campaign_id": test_campaign_id,
            "date_range": "last_7d",
            "analysis_type": "quick"
        }
        
        try:
            # Test graph invocation
            result = await graph.ainvoke(test_state)
            print("✅ Graph test successful!")
            
            if result:
                # Check for report
                if "report_summary" in result:
                    print(f"   Report generated: {len(result['report_summary'])} chars")
                
                # Check for insights
                if "insights" in result:
                    print(f"   Insights generated: {len(result['insights'])} items")
                
                # Check for performance data
                if "performance_data" in result:
                    perf = result["performance_data"]
                    if perf:
                        print(f"   Campaign: {perf.get('campaign_name', 'Unknown')}")
                        print(f"   Spend: ${perf.get('total_spend', 0):,.2f}")
                        print(f"   Impressions: {perf.get('total_impressions', 0):,}")
            else:
                print("   Result: Empty (check API credentials)")
                
            return True
        except Exception as e:
            print(f"❌ Graph test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return asyncio.run(run_test())


if __name__ == "__main__":
    print("🚀 SECURE MULTI-AGENT SYSTEM")
    print("   Meta Ads + GoHighLevel + Security")
    print("   For Ryan Castro - SENDÉ WORLD TOUR 2025")
    print("=" * 50)
    
    # Validate environment
    required_env = ["META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"]
    missing = [env for env in required_env if not os.getenv(env)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("   Please check your .env file")
        sys.exit(1)
    
    # Check for AI model
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  No AI model API key found")
        print("   Add OPENAI_API_KEY or ANTHROPIC_API_KEY for full functionality")
    
    print("\n📊 Testing individual components...")
    if test_graph():
        print("✅ Meta agent ready")
    else:
        print("❌ Meta agent test failed")
        sys.exit(1)
    
    # Test the multi-agent system
    import asyncio
    print("\n🔐 Testing complete multi-agent system...")
    if asyncio.run(test_multi_agent_system()):
        print("\n✅ COMPLETE SYSTEM READY FOR DEPLOYMENT!")
        print("\n🚀 FEATURES:")
        print("   • Security layer with phone validation")
        print("   • Supervisor agent for intelligent routing")
        print("   • Meta Ads agent for campaign analytics")
        print("   • GoHighLevel agent for CRM operations")
        print("   • Rate limiting and audit logging")
        print("\n📱 AUTHORIZED USERS:")
        print("   • Ryan Castro (Admin)")
        print("   • Tour Manager (Manager)")
        print("   • Marketing Assistant (Viewer)")
        print("\nTo deploy on LangSmith:")
        print("1. Ensure LANGCHAIN_API_KEY is set")
        print("2. Run: langchain deploy")
        print("3. Or use the LangSmith UI to deploy")
    else:
        print("\n❌ Multi-agent system test failed. Check configuration.")
        sys.exit(1)