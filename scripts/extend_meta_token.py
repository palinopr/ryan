#!/usr/bin/env python3
"""
Meta Access Token Extension Script
Exchanges short-lived token for long-lived token (60+ days)
"""

import httpx
import asyncio
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta

load_dotenv()

async def extend_access_token():
    """
    Exchange short-lived Meta access token for long-lived token
    Long-lived tokens last 60 days and can be refreshed
    """
    
    # Get current credentials
    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")
    short_token = os.getenv("META_ACCESS_TOKEN")
    
    if not all([app_id, app_secret, short_token]):
        print("❌ Missing required credentials in .env file")
        return None
    
    print("🔄 Extending Meta access token...")
    print(f"App ID: {app_id}")
    print(f"Current token (first 20 chars): {short_token[:20]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Exchange for long-lived user token
            url = "https://graph.facebook.com/v21.0/oauth/access_token"
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token
            }
            
            response = await client.get(url, params=params, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                long_token = data.get("access_token")
                expires_in = data.get("expires_in", 0)
                
                if long_token:
                    print(f"✅ Successfully extended token!")
                    print(f"New token expires in: {expires_in // 86400} days")
                    print(f"Expiration date: {(datetime.now() + timedelta(seconds=expires_in)).strftime('%Y-%m-%d')}")
                    
                    # Save the new token
                    print("\n📝 New Long-Lived Access Token:")
                    print("=" * 60)
                    print(long_token)
                    print("=" * 60)
                    
                    # Optionally update .env file
                    update = input("\n📝 Update .env file with new token? (y/n): ").strip().lower()
                    if update == 'y':
                        # Read current .env
                        with open('.env', 'r') as f:
                            lines = f.readlines()
                        
                        # Update the token line
                        for i, line in enumerate(lines):
                            if line.startswith('META_ACCESS_TOKEN='):
                                lines[i] = f'META_ACCESS_TOKEN={long_token}\n'
                                break
                        
                        # Write back
                        with open('.env', 'w') as f:
                            f.writelines(lines)
                        
                        print("✅ .env file updated with new token")
                    
                    # Step 2: Get token info
                    print("\n🔍 Verifying new token...")
                    info_url = "https://graph.facebook.com/v21.0/debug_token"
                    info_params = {
                        "input_token": long_token,
                        "access_token": f"{app_id}|{app_secret}"
                    }
                    
                    info_response = await client.get(info_url, params=info_params, timeout=30.0)
                    if info_response.status_code == 200:
                        info_data = info_response.json()
                        token_info = info_data.get("data", {})
                        
                        print("\n📊 Token Information:")
                        print(f"App: {token_info.get('application', 'Unknown')}")
                        print(f"User ID: {token_info.get('user_id', 'Unknown')}")
                        print(f"Valid: {token_info.get('is_valid', False)}")
                        print(f"Expires: {datetime.fromtimestamp(token_info.get('expires_at', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        scopes = token_info.get('scopes', [])
                        if scopes:
                            print(f"Permissions: {', '.join(scopes)}")
                        
                        # Check for ads_read permission
                        if 'ads_read' in scopes:
                            print("✅ ads_read permission confirmed")
                        else:
                            print("⚠️ Warning: ads_read permission not found. You may need to re-authorize.")
                    
                    return long_token
                else:
                    print("❌ No access token in response")
                    return None
            else:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                print(f"❌ Failed to extend token: {error_msg}")
                
                # Common error solutions
                if 'expired' in error_msg.lower():
                    print("\n💡 Solution: Your token has expired. You need to:")
                    print("1. Go to https://developers.facebook.com/tools/explorer/")
                    print("2. Select your app: Outlet Media Method")
                    print("3. Click 'Generate Access Token'")
                    print("4. Select permissions: ads_read, ads_management")
                    print("5. Copy the new token and update .env file")
                elif 'invalid' in error_msg.lower():
                    print("\n💡 Solution: Token appears invalid. Regenerate it from Facebook Developer Tools.")
                
                return None
                
        except Exception as e:
            print(f"❌ Error extending token: {e}")
            return None


async def get_ad_accounts():
    """
    Get list of ad accounts accessible with current token
    Helps find the correct META_AD_ACCOUNT_ID
    """
    token = os.getenv("META_ACCESS_TOKEN")
    
    if not token:
        print("❌ No META_ACCESS_TOKEN found in .env")
        return
    
    print("\n🔍 Fetching accessible ad accounts...")
    
    async with httpx.AsyncClient() as client:
        try:
            url = "https://graph.facebook.com/v21.0/me/adaccounts"
            params = {
                "access_token": token,
                "fields": "id,name,account_id,account_status,currency,timezone_name"
            }
            
            response = await client.get(url, params=params, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                accounts = data.get('data', [])
                
                if accounts:
                    print(f"\n📊 Found {len(accounts)} ad account(s):")
                    print("-" * 60)
                    for acc in accounts:
                        print(f"ID: {acc.get('id', 'Unknown')}")
                        print(f"Name: {acc.get('name', 'Unknown')}")
                        print(f"Account ID: {acc.get('account_id', 'Unknown')}")
                        print(f"Status: {acc.get('account_status', 'Unknown')}")
                        print(f"Currency: {acc.get('currency', 'Unknown')}")
                        print(f"Timezone: {acc.get('timezone_name', 'Unknown')}")
                        print("-" * 60)
                    
                    print("\n💡 Use the 'ID' field (e.g., act_123456789) as META_AD_ACCOUNT_ID in .env")
                else:
                    print("❌ No ad accounts found. Check your permissions.")
            else:
                error_data = response.json()
                print(f"❌ Failed to fetch ad accounts: {error_data.get('error', {}).get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error fetching ad accounts: {e}")


async def test_campaign_access():
    """
    Test access to campaigns with current token
    """
    token = os.getenv("META_ACCESS_TOKEN")
    ad_account = os.getenv("META_AD_ACCOUNT_ID")
    
    if not token:
        print("❌ No META_ACCESS_TOKEN found in .env")
        return
    
    # If no ad account ID, try to get it first
    if not ad_account or ad_account == "act_your_ad_account_id_here":
        print("⚠️ No valid META_AD_ACCOUNT_ID found. Fetching ad accounts first...")
        await get_ad_accounts()
        print("\n📝 Please update META_AD_ACCOUNT_ID in .env file with one of the account IDs above")
        return
    
    print(f"\n🔍 Testing campaign access for account: {ad_account}")
    
    async with httpx.AsyncClient() as client:
        try:
            url = f"https://graph.facebook.com/v21.0/{ad_account}/campaigns"
            params = {
                "access_token": token,
                "fields": "id,name,status,objective,created_time",
                "limit": 5
            }
            
            response = await client.get(url, params=params, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                campaigns = data.get('data', [])
                
                if campaigns:
                    print(f"\n✅ Successfully accessed campaigns!")
                    print(f"Found {len(campaigns)} campaign(s):")
                    print("-" * 60)
                    for camp in campaigns:
                        print(f"ID: {camp.get('id', 'Unknown')}")
                        print(f"Name: {camp.get('name', 'Unknown')}")
                        print(f"Status: {camp.get('status', 'Unknown')}")
                        print(f"Objective: {camp.get('objective', 'Unknown')}")
                        print(f"Created: {camp.get('created_time', 'Unknown')}")
                        print("-" * 60)
                    
                    print("\n💡 Use any Campaign ID above to test the agent")
                else:
                    print("⚠️ No campaigns found in this ad account")
            else:
                error_data = response.json()
                print(f"❌ Failed to access campaigns: {error_data.get('error', {}).get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error accessing campaigns: {e}")


async def main():
    """Main menu for token management"""
    print("\n" + "="*60)
    print("  META ACCESS TOKEN MANAGER")
    print("  Outlet Media Method")
    print("="*60)
    
    while True:
        print("\nOptions:")
        print("1. Extend access token (60 days)")
        print("2. Get ad account IDs")
        print("3. Test campaign access")
        print("4. Exit")
        print("-" * 40)
        
        choice = input("Select option (1-4): ").strip()
        
        if choice == "1":
            await extend_access_token()
        elif choice == "2":
            await get_ad_accounts()
        elif choice == "3":
            await test_campaign_access()
        elif choice == "4":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")