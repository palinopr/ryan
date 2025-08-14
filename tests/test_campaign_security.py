"""
Test campaign-level security access control
"""
import os
from src.config.security_config import (
    get_allowed_campaigns, 
    can_access_campaign,
    filter_campaigns_by_access,
    get_campaign_access_level
)
from src.tools.meta_ads_tools import DynamicMetaSDK

def test_campaign_security():
    """Test campaign access control"""
    
    print("🔒 Testing Campaign Security Access Control")
    print("=" * 50)
    
    # Test users
    test_users = [
        {
            "phone": "+17865551234",  # Ryan Castro
            "name": "Ryan Castro",
            "expected_campaigns": ["120232002620350525"],
            "expected_access": "restricted"
        },
        {
            "phone": "+17865555678",  # Tour Manager
            "name": "Tour Manager",
            "expected_campaigns": ["120232002620350525"],
            "expected_access": "restricted"
        },
        {
            "phone": "+17865559999",  # Marketing Assistant
            "name": "Marketing Assistant",
            "expected_campaigns": [],
            "expected_access": "none"
        },
        {
            "phone": "+13055551234",  # Agency Admin
            "name": "Agency Admin",
            "expected_campaigns": ["*"],
            "expected_access": "all"
        },
        {
            "phone": "+19999999999",  # Unknown user
            "name": "Unknown User",
            "expected_campaigns": [],
            "expected_access": "none"
        }
    ]
    
    # Test campaign IDs
    ryan_campaign = "120232002620350525"
    other_campaign = "999999999999999999"
    
    for user in test_users:
        print(f"\n📱 Testing: {user['name']} ({user['phone']})")
        print("-" * 40)
        
        # Test get_allowed_campaigns
        allowed = get_allowed_campaigns(user['phone'])
        print(f"   Allowed campaigns: {allowed}")
        assert allowed == user['expected_campaigns'], f"Expected {user['expected_campaigns']}, got {allowed}"
        
        # Test get_campaign_access_level
        access_level = get_campaign_access_level(user['phone'])
        print(f"   Access level: {access_level}")
        assert access_level == user['expected_access'], f"Expected {user['expected_access']}, got {access_level}"
        
        # Test can_access_campaign for Ryan's campaign
        can_access_ryan = can_access_campaign(user['phone'], ryan_campaign)
        if user['name'] in ["Ryan Castro", "Tour Manager", "Agency Admin"]:
            assert can_access_ryan == True, f"{user['name']} should access Ryan's campaign"
            print(f"   ✅ Can access Ryan's campaign: {can_access_ryan}")
        else:
            assert can_access_ryan == False, f"{user['name']} should NOT access Ryan's campaign"
            print(f"   ❌ Can access Ryan's campaign: {can_access_ryan}")
        
        # Test can_access_campaign for other campaign
        can_access_other = can_access_campaign(user['phone'], other_campaign)
        if user['name'] == "Agency Admin":
            assert can_access_other == True, f"Agency Admin should access all campaigns"
            print(f"   ✅ Can access other campaigns: {can_access_other}")
        else:
            assert can_access_other == False, f"{user['name']} should NOT access other campaigns"
            print(f"   ❌ Can access other campaigns: {can_access_other}")
    
    # Test SDK integration
    print("\n\n🔧 Testing SDK Security Integration")
    print("=" * 50)
    
    sdk = DynamicMetaSDK()
    
    # Test with Ryan's context
    print("\n1. Setting Ryan Castro's context...")
    sdk.set_user_context("+17865551234")
    
    # Should be able to access Ryan's campaign
    can_access = sdk.check_campaign_access(ryan_campaign)
    print(f"   Can access campaign {ryan_campaign}: {can_access}")
    assert can_access == True, "Ryan should access his campaign"
    
    # Should NOT be able to access other campaign
    can_access = sdk.check_campaign_access(other_campaign)
    print(f"   Can access campaign {other_campaign}: {can_access}")
    assert can_access == False, "Ryan should NOT access other campaigns"
    
    # Test with unknown user context
    print("\n2. Setting unknown user context...")
    sdk.set_user_context("+19999999999")
    
    # Should NOT be able to access any campaign
    can_access = sdk.check_campaign_access(ryan_campaign)
    print(f"   Can access campaign {ryan_campaign}: {can_access}")
    assert can_access == False, "Unknown user should NOT access any campaign"
    
    # Test with agency admin context
    print("\n3. Setting agency admin context...")
    sdk.set_user_context("+13055551234")
    
    # Should be able to access ALL campaigns
    can_access = sdk.check_campaign_access(ryan_campaign)
    print(f"   Can access campaign {ryan_campaign}: {can_access}")
    assert can_access == True, "Agency admin should access all campaigns"
    
    can_access = sdk.check_campaign_access(other_campaign)
    print(f"   Can access campaign {other_campaign}: {can_access}")
    assert can_access == True, "Agency admin should access all campaigns"
    
    print("\n\n✅ All security tests passed!")
    print("=" * 50)
    print("Campaign-level security is working correctly:")
    print("• Ryan Castro can only see campaign 120232002620350525")
    print("• Tour Manager can only see campaign 120232002620350525")
    print("• Marketing Assistant cannot see any campaigns")
    print("• Agency Admin can see all campaigns")
    print("• Unknown users cannot access any campaigns")

if __name__ == "__main__":
    test_campaign_security()