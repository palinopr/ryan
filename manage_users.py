#!/usr/bin/env python3
"""
User Management Script for Meta Ryan AI System
Easily add, remove, and list authorized phone numbers
"""

import os
import sys
import json
from typing import Optional
from src.config.security_config import SECURITY_CONFIG

def list_users():
    """List all authorized users"""
    print("\n" + "="*60)
    print("AUTHORIZED USERS")
    print("="*60)
    
    for key, user in SECURITY_CONFIG["whitelist"].items():
        print(f"\n{key}:")
        print(f"  Name: {user['name']}")
        print(f"  Phone: {user['phone']}")
        print(f"  Role: {user['role']}")
        print(f"  Permissions: {', '.join(user['permissions']) if user['permissions'] != ['*'] else 'ALL'}")
        print(f"  Campaign Access: {user['campaign_access']}")
        if user['allowed_campaigns']:
            campaigns = 'ALL' if '*' in user['allowed_campaigns'] else ', '.join(user['allowed_campaigns'])
            print(f"  Allowed Campaigns: {campaigns}")

def add_user():
    """Interactive function to add a new user"""
    print("\n" + "="*60)
    print("ADD NEW USER")
    print("="*60)
    
    # Get user details
    name = input("\nEnter user's name: ").strip()
    phone = input("Enter phone number (with country code, e.g., +17865551234): ").strip()
    
    if not phone.startswith('+'):
        phone = '+' + phone
    
    print("\nSelect role:")
    print("1. admin - Full access")
    print("2. manager - Read, write, send")
    print("3. viewer - Read only")
    
    role_choice = input("\nEnter choice (1-3): ").strip()
    
    role_map = {
        '1': ('admin', ['*']),
        '2': ('manager', ['read', 'write', 'send', 'update']),
        '3': ('viewer', ['read'])
    }
    
    if role_choice not in role_map:
        print("Invalid choice!")
        return
    
    role, permissions = role_map[role_choice]
    
    # Campaign access
    campaign_access = input("\nAllow access to SENDÉ Tour campaign? (y/n): ").strip().lower()
    allowed_campaigns = ['120232002620350525'] if campaign_access == 'y' else []
    
    # Create user key
    user_key = name.lower().replace(' ', '_')
    
    print(f"\n" + "="*60)
    print("NEW USER CONFIGURATION")
    print("="*60)
    print(f"Key: {user_key}")
    print(f"Name: {name}")
    print(f"Phone: {phone}")
    print(f"Role: {role}")
    print(f"Permissions: {permissions}")
    print(f"Campaign Access: {'Yes' if allowed_campaigns else 'No'}")
    
    confirm = input("\nAdd this user? (y/n): ").strip().lower()
    
    if confirm == 'y':
        # Add to config
        new_user = f'''
        "{user_key}": {{
            "phone": "{phone}",
            "name": "{name}",
            "role": "{role}",
            "permissions": {json.dumps(permissions)},
            "allowed_campaigns": {json.dumps(allowed_campaigns)},
            "campaign_access": "{'restricted' if allowed_campaigns else 'none'}"
        }},'''
        
        print(f"\nAdd this to src/config/security_config.py in the whitelist section:")
        print(new_user)
        
        # Or add to .env
        env_var = f"{user_key.upper()}_PHONE"
        print(f"\nOr add to .env file:")
        print(f"{env_var}={phone}  # {name}")
        
        print(f"\nThen update security_config.py to use: os.getenv('{env_var}', '{phone}')")
        print("\n✅ User configuration generated successfully!")
    else:
        print("User addition cancelled.")

def remove_user():
    """Remove a user by phone number"""
    print("\n" + "="*60)
    print("REMOVE USER")
    print("="*60)
    
    phone = input("\nEnter phone number to remove: ").strip()
    
    if not phone.startswith('+'):
        phone = '+' + phone
    
    # Find user
    found = None
    for key, user in SECURITY_CONFIG["whitelist"].items():
        if user['phone'] == phone:
            found = (key, user)
            break
    
    if found:
        key, user = found
        print(f"\nFound user: {user['name']} ({key})")
        confirm = input("Remove this user? (y/n): ").strip().lower()
        
        if confirm == 'y':
            print(f"\nTo remove, delete the '{key}' entry from security_config.py")
            print("Or comment it out by adding # at the beginning of each line")
            print("\n✅ Instructions provided!")
    else:
        print(f"❌ No user found with phone: {phone}")

def test_access():
    """Test if a phone number has access"""
    print("\n" + "="*60)
    print("TEST ACCESS")
    print("="*60)
    
    phone = input("\nEnter phone number to test: ").strip()
    
    if not phone.startswith('+'):
        phone = '+' + phone
    
    # Check access
    from src.agents.security_agent import validate_access
    import asyncio
    
    async def test():
        result = await validate_access(phone, "test query")
        if result['authorized']:
            print(f"\n✅ AUTHORIZED")
            print(f"Role: {result.get('role')}")
            print(f"Permissions: {result.get('permissions')}")
        else:
            print(f"\n❌ DENIED")
            print(f"Reason: {result.get('error')}")
    
    asyncio.run(test())

def main():
    """Main menu"""
    while True:
        print("\n" + "="*60)
        print("META RYAN AI - USER MANAGEMENT")
        print("="*60)
        print("1. List all users")
        print("2. Add new user")
        print("3. Remove user")
        print("4. Test phone access")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            list_users()
        elif choice == '2':
            add_user()
        elif choice == '3':
            remove_user()
        elif choice == '4':
            test_access()
        elif choice == '5':
            print("\nGoodbye!")
            sys.exit(0)
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    main()