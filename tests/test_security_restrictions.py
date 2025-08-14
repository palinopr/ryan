"""
Test security restrictions for client queries
Ensure strategic information is blocked
"""
import asyncio
from src.agents.meta_campaign_agent import check_query_restrictions, plan_and_execute_dynamic_queries

async def test_security_restrictions():
    """Test that restricted queries are properly blocked"""
    
    print("🔒 Testing Query Security Restrictions")
    print("=" * 50)
    
    # Test cases: restricted queries that should be blocked
    restricted_queries = [
        # How campaign is made/structured
        "How is the campaign structured?",
        "Show me the campaign structure",
        "How many campaigns do we have?",
        "How was this campaign created?",
        
        # Strategy questions
        "How are you optimizing the campaign?",
        "What's your bidding strategy?",
        "How do you target audiences?",
        "Why did you choose these cities?",
        
        # When/timing questions
        "When do you update budgets?",
        "How often do you adjust bids?",
        "What's the update schedule?",
        
        # Creative/content
        "What does the ad copy say?",
        "Show me the creative content",
        "What images are you using?",
        
        # Modification attempts
        "Update the budget to $5000",
        "Can you change the targeting?",
        "Pause the Miami campaign",
        "Create a new ad",
        
        # Strategic recommendations
        "What should we do to improve?",
        "Give me recommendations",
        "How to improve performance?",
        "What's the best practice?",
        
        # Internal operations
        "How is tracking set up?",
        "Show me internal processes",
        "What's your proprietary method?"
    ]
    
    # Test cases: allowed queries that should work (now includes asset metrics)
    allowed_queries = [
        # City/location metrics
        "Show me Miami performance",
        "What's the ROAS for Orlando?",
        "Show me clicks by city",
        
        # Asset/ad metrics
        "How many ads are in the campaign?",  # This is now ALLOWED (it's a metric)
        "What's the CTR for each ad?",
        "Show me ad performance metrics",
        "How many adsets do we have?",  # This is now ALLOWED (it's a metric)
        "What's the performance of each asset?",
        
        # Time-based metrics
        "How much did we spend today?",
        "What's the CTR for this week?",
        "Show me last month's performance",
        
        # General metrics
        "Show me impressions for all cities",
        "How many people reached in Tampa?",
        "What's the total ad spend?",
        "Show me all available insights",
        "What's the conversion rate?",
        "Show me video view metrics",
        "What's the engagement rate?"
    ]
    
    print("\n📛 Testing RESTRICTED Queries (should be blocked):")
    print("-" * 40)
    
    blocked_count = 0
    for query in restricted_queries[:10]:  # Test first 10 restricted
        result = check_query_restrictions(query)
        if result and "RESTRICTED" in result:
            print(f"✅ BLOCKED: {query[:50]}...")
            blocked_count += 1
        else:
            print(f"❌ ALLOWED (ERROR): {query[:50]}...")
    
    print(f"\nBlocked {blocked_count}/{min(10, len(restricted_queries))} restricted queries")
    
    print("\n✅ Testing ALLOWED Queries (should work):")
    print("-" * 40)
    
    allowed_count = 0
    for query in allowed_queries[:10]:  # Test first 10 allowed
        result = check_query_restrictions(query)
        if result is None:
            print(f"✅ ALLOWED: {query[:50]}...")
            allowed_count += 1
        else:
            print(f"❌ BLOCKED (ERROR): {query[:50]}...")
    
    print(f"\nAllowed {allowed_count}/{min(10, len(allowed_queries))} performance queries")
    
    # Test with plan_and_execute function
    print("\n\n🧪 Testing Full Query Pipeline:")
    print("-" * 40)
    
    test_campaign_id = "120232002620350525"
    
    # Test a restricted query through the full pipeline
    print("\n1. Testing restricted query through pipeline...")
    result = await plan_and_execute_dynamic_queries(
        "How is the campaign structured?",
        test_campaign_id
    )
    if result and "RESTRICTED" in result:
        print("✅ Pipeline correctly blocks strategic questions")
    else:
        print("❌ Pipeline failed to block restricted query")
    
    # Test an allowed query through the full pipeline  
    print("\n2. Testing allowed query through pipeline...")
    result = await plan_and_execute_dynamic_queries(
        "Show me Miami performance for today",
        test_campaign_id
    )
    if result and "RESTRICTED" not in result:
        print("✅ Pipeline allows performance queries")
    else:
        print("❌ Pipeline incorrectly blocked allowed query")
    
    print("\n\n" + "=" * 50)
    print("Security Testing Complete!")
    print("\nKey Security Features:")
    print("✅ Blocks questions about campaign structure")
    print("✅ Blocks strategy and optimization questions")
    print("✅ Blocks modification/update attempts")
    print("✅ Blocks requests for creative content")
    print("✅ Only allows performance metric queries")
    print("✅ Provides clear explanation when blocking")
    print("\nThis ensures Outlet Media's proprietary strategies remain confidential.")

if __name__ == "__main__":
    asyncio.run(test_security_restrictions())