"""
Security Agent - Phone Verification and Permission Management
Validates phone numbers and enforces permissions before allowing access
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List, Literal, TypedDict
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from dotenv import load_dotenv
from src.config.security_config import (
    SECURITY_CONFIG,
    AuditEntry,
    get_authorized_numbers,
    get_user_permissions,
    get_user_role,
    get_rate_limit
)

load_dotenv()
logger = logging.getLogger(__name__)


class SecurityState(TypedDict):
    """State for the security agent"""
    messages: List[Any]
    phone_number: str
    user_role: Optional[str]
    user_permissions: Optional[List[str]]
    requested_action: str
    requested_agent: Optional[str]  # meta or ghl
    validation_result: Optional[str]  # authorized, denied, blocked
    rate_limit_check: Optional[bool]
    audit_logged: Optional[bool]
    error: Optional[str]
    next_agent: Optional[str]  # Which agent to route to


class RateLimiter:
    """Simple rate limiter for tracking requests"""
    
    def __init__(self):
        self.requests = {}  # phone -> [(timestamp, action)]
    
    def check_rate_limit(self, phone: str, role: str) -> tuple[bool, str]:
        """Check if user is within rate limits"""
        limits = get_rate_limit(role)
        now = datetime.utcnow()
        
        # Initialize if new phone
        if phone not in self.requests:
            self.requests[phone] = []
        
        # Clean old entries (older than 1 hour)
        cutoff = now - timedelta(hours=1)
        self.requests[phone] = [
            (ts, action) for ts, action in self.requests[phone]
            if ts > cutoff
        ]
        
        # Check hourly limit
        hour_ago = now - timedelta(hours=1)
        hour_count = sum(1 for ts, _ in self.requests[phone] if ts > hour_ago)
        
        if hour_count >= limits.get('requests_per_hour', 100):
            return False, f"Hourly limit exceeded ({limits['requests_per_hour']}/hour)"
        
        # Check minute limit
        minute_ago = now - timedelta(minutes=1)
        minute_count = sum(1 for ts, _ in self.requests[phone] if ts > minute_ago)
        
        if minute_count >= limits.get('requests_per_minute', 10):
            return False, f"Minute limit exceeded ({limits['requests_per_minute']}/min)"
        
        return True, "Within limits"
    
    def record_request(self, phone: str, action: str):
        """Record a request for rate limiting"""
        if phone not in self.requests:
            self.requests[phone] = []
        self.requests[phone].append((datetime.utcnow(), action))


# Global rate limiter instance
rate_limiter = RateLimiter()


class FailedAttemptTracker:
    """Track failed authentication attempts"""
    
    def __init__(self):
        self.attempts = {}  # phone -> [(timestamp, reason)]
        self.lockouts = {}  # phone -> lockout_until
    
    def is_locked_out(self, phone: str) -> tuple[bool, Optional[datetime]]:
        """Check if phone is locked out"""
        if phone in self.lockouts:
            lockout_until = self.lockouts[phone]
            if datetime.utcnow() < lockout_until:
                return True, lockout_until
            else:
                # Lockout expired
                del self.lockouts[phone]
        return False, None
    
    def record_failed_attempt(self, phone: str, reason: str):
        """Record a failed attempt"""
        settings = SECURITY_CONFIG['security_settings']
        
        if phone not in self.attempts:
            self.attempts[phone] = []
        
        self.attempts[phone].append((datetime.utcnow(), reason))
        
        # Check if we need to lockout
        recent_cutoff = datetime.utcnow() - timedelta(minutes=15)
        recent_attempts = [
            a for a in self.attempts[phone] 
            if a[0] > recent_cutoff
        ]
        
        if len(recent_attempts) >= settings.get('max_failed_attempts', 3):
            lockout_duration = settings.get('lockout_duration_minutes', 15)
            self.lockouts[phone] = datetime.utcnow() + timedelta(minutes=lockout_duration)
            logger.warning(f"Phone {phone} locked out for {lockout_duration} minutes")
    
    def clear_attempts(self, phone: str):
        """Clear failed attempts after successful auth"""
        if phone in self.attempts:
            del self.attempts[phone]


# Global tracker instance
attempt_tracker = FailedAttemptTracker()


class AuditLogger:
    """Audit logger for security events"""
    
    def __init__(self):
        self.log_file = "security_audit.json"
        self.logs = []
    
    def log(self, entry: AuditEntry):
        """Log an audit entry"""
        log_data = entry.to_dict()
        self.logs.append(log_data)
        
        # Also log to file if configured
        if SECURITY_CONFIG['audit']['log_all_requests']:
            try:
                # Append to file
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(log_data) + '\n')
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
        
        # Send alerts if needed
        if log_data['result'] == 'denied' and SECURITY_CONFIG['audit']['log_denied_attempts']:
            self._send_alert(f"Denied access attempt from {log_data['phone']}")
        
        if log_data['result'] == 'blocked' and SECURITY_CONFIG['audit']['alert_on_unauthorized']:
            self._send_alert(f"UNAUTHORIZED ACCESS ATTEMPT from {log_data['phone']}")
    
    def _send_alert(self, message: str):
        """Send security alert"""
        channels = SECURITY_CONFIG['audit'].get('alert_channels', [])
        for channel in channels:
            logger.warning(f"[SECURITY ALERT - {channel}] {message}")
            # In production, send actual email/SMS alerts


# Global audit logger
audit_logger = AuditLogger()


async def validate_phone_node(state: SecurityState) -> Command[Literal["check_permissions", "deny_access"]]:
    """Validate if the phone number is authorized"""
    logger.info("Validating phone number")
    
    phone = state.get('phone_number', '')
    
    # Check if phone is provided
    if not phone:
        audit_logger.log(AuditEntry(
            phone="unknown",
            action="access_attempt",
            result="denied",
            details="No phone number provided"
        ))
        return Command(
            update={
                "validation_result": "denied",
                "error": "Phone number required for access"
            },
            goto="deny_access"
        )
    
    # Normalize phone number format (remove spaces, parentheses, dashes)
    import re
    normalized_phone = re.sub(r'[\s\(\)\-]', '', phone)
    if not normalized_phone.startswith('+'):
        normalized_phone = '+' + normalized_phone
    logger.info(f"Normalized phone from '{phone}' to '{normalized_phone}'")
    
    # Check if locked out (use normalized phone)
    is_locked, until = attempt_tracker.is_locked_out(normalized_phone)
    if is_locked:
        audit_logger.log(AuditEntry(
            phone=normalized_phone,
            action="access_attempt",
            result="blocked",
            details=f"Account locked until {until}"
        ))
        return Command(
            update={
                "validation_result": "blocked",
                "error": f"Account temporarily locked. Try again after {until.strftime('%H:%M')}"
            },
            goto="deny_access"
        )
    
    # Check if phone is authorized
    authorized_numbers = get_authorized_numbers()
    if normalized_phone not in authorized_numbers:
        attempt_tracker.record_failed_attempt(normalized_phone, "unauthorized_number")
        audit_logger.log(AuditEntry(
            phone=normalized_phone,
            action="access_attempt",
            result="denied",
            details="Unauthorized phone number"
        ))
        return Command(
            update={
                "validation_result": "denied",
                "error": "Unauthorized phone number. Access denied."
            },
            goto="deny_access"
        )
    
    # Phone is authorized
    user_role = get_user_role(normalized_phone)
    user_permissions = get_user_permissions(normalized_phone)
    
    # Clear failed attempts on successful auth
    attempt_tracker.clear_attempts(normalized_phone)
    
    logger.info(f"Phone {phone} authorized with role: {user_role}")
    
    return Command(
        update={
            "validation_result": "authorized",
            "user_role": user_role,
            "user_permissions": user_permissions
        },
        goto="check_permissions"
    )


async def check_permissions_node(state: SecurityState) -> Command[Literal["check_rate_limit", "deny_access"]]:
    """Check if user has permission for requested action"""
    logger.info("Checking permissions")
    
    phone = state.get('phone_number')
    requested_action = state.get('requested_action', '')
    user_permissions = state.get('user_permissions', [])
    
    # Parse the requested action to determine permission needed
    action_lower = requested_action.lower()
    
    # Map actions to permissions
    permission_needed = None
    if any(word in action_lower for word in ['view', 'get', 'show', 'list', 'how']):
        permission_needed = 'read'
    elif any(word in action_lower for word in ['send', 'message', 'email', 'notify']):
        permission_needed = 'send'
    elif any(word in action_lower for word in ['create', 'add', 'new']):
        permission_needed = 'write'
    elif any(word in action_lower for word in ['update', 'change', 'modify', 'edit']):
        permission_needed = 'update'
    elif any(word in action_lower for word in ['delete', 'remove', 'cancel']):
        permission_needed = 'delete'
    elif any(word in action_lower for word in ['admin', 'configure', 'settings']):
        permission_needed = 'admin'
    else:
        permission_needed = 'read'  # Default to read permission
    
    # Check if user has permission
    if '*' in user_permissions or permission_needed in user_permissions:
        logger.info(f"Permission granted for {permission_needed}")
        
        # Determine which agent to route to
        if any(word in action_lower for word in ['campaign', 'ad', 'roas', 'facebook', 'instagram', 'meta', 'performance']):
            next_agent = 'meta'
        elif any(word in action_lower for word in ['contact', 'message', 'sms', 'email', 'appointment', 'ghl', 'crm']):
            next_agent = 'ghl'
        else:
            next_agent = 'supervisor'  # Let supervisor decide
        
        return Command(
            update={"next_agent": next_agent},
            goto="check_rate_limit"
        )
    else:
        audit_logger.log(AuditEntry(
            phone=phone,
            action=requested_action,
            result="denied",
            details=f"Missing permission: {permission_needed}"
        ))
        return Command(
            update={
                "validation_result": "denied",
                "error": f"Permission denied. You need '{permission_needed}' permission for this action."
            },
            goto="deny_access"
        )


async def check_rate_limit_node(state: SecurityState) -> Command[Literal["allow_access", "deny_access"]]:
    """Check rate limits"""
    logger.info("Checking rate limits")
    
    phone = state.get('phone_number')
    user_role = state.get('user_role')
    requested_action = state.get('requested_action')
    
    # Check rate limit
    within_limit, message = rate_limiter.check_rate_limit(phone, user_role)
    
    if within_limit:
        # Record the request
        rate_limiter.record_request(phone, requested_action)
        
        # Log successful access
        audit_logger.log(AuditEntry(
            phone=phone,
            action=requested_action,
            result="allowed",
            details=f"Access granted with role: {user_role}"
        ))
        
        return Command(
            update={"rate_limit_check": True},
            goto="allow_access"
        )
    else:
        audit_logger.log(AuditEntry(
            phone=phone,
            action=requested_action,
            result="denied",
            details=f"Rate limit exceeded: {message}"
        ))
        return Command(
            update={
                "validation_result": "denied",
                "error": f"Rate limit exceeded: {message}. Please wait before trying again."
            },
            goto="deny_access"
        )


async def allow_access_node(state: SecurityState) -> Command[Literal[END]]:
    """Allow access and route to appropriate agent"""
    logger.info("Access granted")
    
    phone = state.get('phone_number')
    next_agent = state.get('next_agent', 'supervisor')
    user_role = state.get('user_role')
    
    # Create access token/context for next agent
    security_context = {
        "authenticated": True,
        "phone": phone,
        "role": user_role,
        "permissions": state.get('user_permissions'),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    result = {
        "status": "authorized",
        "next_agent": next_agent,
        "security_context": security_context,
        "message": f"Access granted. Routing to {next_agent} agent."
    }
    
    return Command(
        update={
            "messages": state.get('messages', []) + [
                AIMessage(content=f"✅ Access granted for {phone} (Role: {user_role})")
            ],
            "validation_result": "authorized"
        },
        goto=END
    )


async def deny_access_node(state: SecurityState) -> Command[Literal[END]]:
    """Deny access and log the attempt"""
    logger.warning("Access denied")
    
    phone = state.get('phone_number', 'unknown')
    error = state.get('error', 'Access denied')
    
    result = {
        "status": "denied",
        "error": error,
        "message": "Access denied. This incident has been logged."
    }
    
    return Command(
        update={
            "messages": state.get('messages', []) + [
                AIMessage(content=f"❌ {error}")
            ]
        },
        goto=END
    )


def build_security_graph():
    """Build the security agent graph"""
    builder = StateGraph(SecurityState)
    
    # Add nodes
    builder.add_node("validate_phone", validate_phone_node)
    builder.add_node("check_permissions", check_permissions_node)
    builder.add_node("check_rate_limit", check_rate_limit_node)
    builder.add_node("allow_access", allow_access_node)
    builder.add_node("deny_access", deny_access_node)
    
    # Set entry point
    builder.set_entry_point("validate_phone")
    
    # Set finish point
    builder.set_finish_point("allow_access")
    builder.set_finish_point("deny_access")
    
    return builder.compile()


# Create the security agent
security_agent = build_security_graph()


# Helper function to validate access
async def validate_access(
    phone_number: str,
    requested_action: str,
    requested_agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate if a phone number has access to perform an action
    
    Args:
        phone_number: The phone number requesting access
        requested_action: Description of the action they want to perform
        requested_agent: Optional specific agent they want to access (meta/ghl)
    
    Returns:
        Dictionary with validation result and next steps
    """
    initial_state = SecurityState(
        messages=[HumanMessage(content=requested_action)],
        phone_number=phone_number,
        requested_action=requested_action,
        requested_agent=requested_agent
    )
    
    result = await security_agent.ainvoke(initial_state)
    
    return {
        "authorized": result.get("validation_result") == "authorized",
        "next_agent": result.get("next_agent"),
        "role": result.get("user_role"),
        "permissions": result.get("user_permissions"),
        "error": result.get("error")
    }