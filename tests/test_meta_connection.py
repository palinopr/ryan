#!/usr/bin/env python3
"""
Test Meta API connection and extend token
"""

import asyncio
from extend_meta_token import extend_access_token, get_ad_accounts, test_campaign_access

async def main():
    print("=" * 60)
    print("  TESTING META API CONNECTION")
    print("=" * 60)
    
    # Step 1: Extend the token
    print("\n📌 Step 1: Extending access token...")
    new_token = await extend_access_token()
    
    # Step 2: Get ad accounts
    print("\n📌 Step 2: Getting ad accounts...")
    await get_ad_accounts()
    
    # Step 3: Test campaign access
    print("\n📌 Step 3: Testing campaign access...")
    await test_campaign_access()
    
    print("\n✅ Connection test complete!")

if __name__ == "__main__":
    asyncio.run(main())