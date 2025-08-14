"""
Security Configuration for Multi-Agent System
Only authorized phone numbers can access the system
"""
import os
from typing import Dict, List, Optional
from datetime import datetime

# Security Configuration
SECURITY_CONFIG = {
    "whitelist": {
        "ryan_castro": {
            "phone": os.getenv("RYAN_PHONE", "+17865551234"),  # Replace with actual
            "name": "Ryan Castro",
            "role": "admin",
            "permissions": ["*"],  # All permissions
            "allowed_campaigns": ["120232002620350525"],  # Ryan Castro's SENDÉ Tour campaign
            "campaign_access": "restricted"  # Can only see their campaigns
        },
        "jaime_admin": {
            "phone": os.getenv("ADMIN_PHONE_NUMBER", "+13054870475"),  # Jaime's admin phone
            "name": "Jaime Admin",
            "role": "admin",
            "permissions": ["*"],  # All permissions
            "allowed_campaigns": ["120232002620350525"],  # Access to SENDÉ Tour campaign
            "campaign_access": "restricted"  # Can only see their campaigns
        },
        "manager": {
            "phone": os.getenv("MANAGER_PHONE", "+17865555678"),  # Replace with actual
            "name": "Tour Manager",
            "role": "manager",
            "permissions": ["read", "write", "send", "update"],
            "allowed_campaigns": ["120232002620350525"],  # Same campaign access
            "campaign_access": "restricted"
        },
        "assistant": {
            "phone": os.getenv("ASSISTANT_PHONE", "+17865559999"),  # Replace with actual
            "name": "Marketing Assistant",
            "role": "viewer",
            "permissions": ["read"],
            "allowed_campaigns": [],  # No campaign access
            "campaign_access": "none"
        },
        "agency_admin": {
            "phone": os.getenv("AGENCY_PHONE", "+13055551234"),  # Agency admin
            "name": "Agency Admin",
            "role": "super_admin",
            "permissions": ["*"],
            "allowed_campaigns": ["*"],  # Can see all campaigns
            "campaign_access": "all"
        }
    },
    
    "permission_definitions": {
        "read": [
            "view_metrics",
            "get_campaign_data",
            "list_contacts",
            "view_messages"
        ],
        "write": [
            "create_campaign",
            "update_contact",
            "add_tags",
            "create_appointment"
        ],
        "send": [
            "send_message",
            "send_email",
            "send_campaign"
        ],
        "update": [
            "update_tags",
            "update_contact_info",
            "update_appointment"
        ],
        "delete": [
            "delete_contact",
            "remove_tags",
            "cancel_appointment"
        ],
        "admin": [
            "add_user",
            "remove_user",
            "change_permissions",
            "view_audit_logs"
        ]
    },
    
    "rate_limits": {
        "admin": {
            "requests_per_hour": 1000,
            "requests_per_minute": 100
        },
        "manager": {
            "requests_per_hour": 500,
            "requests_per_minute": 50
        },
        "viewer": {
            "requests_per_hour": 100,
            "requests_per_minute": 10
        }
    },
    
    "audit": {
        "log_all_requests": True,
        "log_denied_attempts": True,
        "alert_on_unauthorized": True,
        "alert_on_permission_denied": True,
        "store_duration_days": 90,
        "alert_channels": ["email", "sms"]  # Where to send alerts
    },
    
    "security_settings": {
        "require_phone_verification": True,
        "session_timeout_minutes": 60,
        "max_failed_attempts": 3,
        "lockout_duration_minutes": 15,
        "require_2fa_for_admin": False  # Can enable later
    }
}


class AuditEntry:
    """Represents an audit log entry"""
    
    def __init__(
        self,
        phone: str,
        action: str,
        result: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        self.timestamp = datetime.utcnow().isoformat()
        self.phone = phone
        self.action = action
        self.result = result  # "allowed", "denied", "blocked"
        self.details = details
        self.ip_address = ip_address
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "phone": self.phone,
            "action": self.action,
            "result": self.result,
            "details": self.details,
            "ip_address": self.ip_address
        }


def get_authorized_numbers() -> List[str]:
    """Get list of all authorized phone numbers"""
    numbers = []
    for user_data in SECURITY_CONFIG["whitelist"].values():
        numbers.append(user_data["phone"])
    return numbers


def get_user_permissions(phone: str) -> List[str]:
    """Get permissions for a specific phone number"""
    for user_data in SECURITY_CONFIG["whitelist"].values():
        if user_data["phone"] == phone:
            permissions = user_data["permissions"]
            if "*" in permissions:
                # Admin has all permissions
                return ["read", "write", "send", "update", "delete", "admin"]
            return permissions
    return []


def get_user_role(phone: str) -> Optional[str]:
    """Get role for a specific phone number"""
    for user_data in SECURITY_CONFIG["whitelist"].values():
        if user_data["phone"] == phone:
            return user_data["role"]
    return None


def get_rate_limit(role: str) -> Dict[str, int]:
    """Get rate limits for a role"""
    return SECURITY_CONFIG["rate_limits"].get(
        role,
        {"requests_per_hour": 10, "requests_per_minute": 1}  # Default strict limits
    )


def get_allowed_campaigns(phone: str) -> List[str]:
    """Get list of campaign IDs this phone number can access"""
    for user_data in SECURITY_CONFIG["whitelist"].values():
        if user_data["phone"] == phone:
            allowed = user_data.get("allowed_campaigns", [])
            if "*" in allowed:
                return ["*"]  # Access to all campaigns
            return allowed
    return []  # No access by default


def can_access_campaign(phone: str, campaign_id: str) -> bool:
    """Check if a phone number can access a specific campaign"""
    allowed_campaigns = get_allowed_campaigns(phone)
    
    # Check if user has access to all campaigns
    if "*" in allowed_campaigns:
        return True
    
    # Check if specific campaign is in allowed list
    return campaign_id in allowed_campaigns


def filter_campaigns_by_access(phone: str, campaigns: List[Dict]) -> List[Dict]:
    """Filter a list of campaigns to only those the user can access"""
    allowed = get_allowed_campaigns(phone)
    
    # If user has access to all campaigns
    if "*" in allowed:
        return campaigns
    
    # Filter to only allowed campaigns
    filtered = []
    for campaign in campaigns:
        campaign_id = campaign.get("id", campaign.get("campaign_id"))
        if campaign_id in allowed:
            filtered.append(campaign)
    
    return filtered


def get_campaign_access_level(phone: str) -> str:
    """Get the campaign access level for a phone number"""
    for user_data in SECURITY_CONFIG["whitelist"].values():
        if user_data["phone"] == phone:
            return user_data.get("campaign_access", "none")
    return "none"