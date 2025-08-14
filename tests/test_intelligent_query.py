"""
Test the intelligent Meta SDK query system
"""
import asyncio
import json
from src.tools.meta_ads_tools import intelligent_meta_query

async def test_intelligent_queries():
    """Test various natural language queries"""
    
    queries = [
        "How is Miami campaign performing?",
        "Show me the CTR and spend for today",
        "What's my ROAS for the last week?",
        "Get demographic breakdown for my campaigns",
        "Show me all active campaigns with their budgets",
        "How much did I spend on ads yesterday?",
        "Which adsets are performing best?",
        "Show me conversion metrics for the last 30 days"
    ]
    
    print("Testing Intelligent Meta SDK Queries\n")
    print("=" * 50)
    
    for query in queries:
        print(f"\n📝 Query: '{query}'")
        print("-" * 40)
        
        try:
            result = await intelligent_meta_query.ainvoke({"request": query})
            
            if isinstance(result, dict) and "error" in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(f"✅ Success!")
                print(f"Result type: {type(result)}")
                if isinstance(result, list):
                    print(f"Number of records: {len(result)}")
                    if result:
                        print(f"Sample data: {json.dumps(result[0], indent=2)[:500]}...")
                elif isinstance(result, dict):
                    print(f"Data: {json.dumps(result, indent=2)[:500]}...")
        
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        await asyncio.sleep(1)  # Rate limiting

if __name__ == "__main__":
    asyncio.run(test_intelligent_queries())