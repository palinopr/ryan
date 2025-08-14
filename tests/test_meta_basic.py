"""
Test basic Meta SDK connection
"""
import os
from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

load_dotenv()

def test_basic_connection():
    """Test if we can connect to Meta API"""
    
    access_token = os.getenv("META_ACCESS_TOKEN")
    app_id = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")
    account_id = os.getenv("META_AD_ACCOUNT_ID")
    
    print("🔍 Testing Meta SDK Connection")
    print("=" * 50)
    
    # Check credentials
    print(f"✓ Access Token: {'Present' if access_token else 'Missing'}")
    print(f"✓ App ID: {'Present' if app_id else 'Missing'}")
    print(f"✓ App Secret: {'Present' if app_secret else 'Missing'}")
    print(f"✓ Account ID: {account_id if account_id else 'Missing'}")
    
    if not all([access_token, app_id, app_secret, account_id]):
        print("\n❌ Missing credentials! Check your .env file")
        return
    
    # Initialize SDK
    try:
        FacebookAdsApi.init(
            app_id=app_id,
            app_secret=app_secret,
            access_token=access_token,
            api_version="v21.0"
        )
        print("\n✅ SDK initialized successfully")
    except Exception as e:
        print(f"\n❌ SDK initialization failed: {e}")
        return
    
    # Format account ID
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
    
    # Try to get account info
    try:
        account = AdAccount(account_id)
        account_data = account.api_get(fields=['name', 'account_status'])
        
        print(f"\n✅ Connected to account: {account_data.get('name', 'Unknown')}")
        print(f"   Status: {account_data.get('account_status', 'Unknown')}")
        
        # Try to get campaigns count
        campaigns = account.get_campaigns(params={'limit': 1})
        campaign_list = list(campaigns)
        print(f"\n✅ Can access campaigns (found at least {len(campaign_list)})")
        
    except Exception as e:
        print(f"\n❌ API call failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Check if it's a token issue
        if "OAuthException" in str(e):
            print("\n⚠️  Token may be expired or invalid")
            print("   Try refreshing your access token")

if __name__ == "__main__":
    test_basic_connection()