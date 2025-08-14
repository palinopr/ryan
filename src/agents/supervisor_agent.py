"""
Supervisor Agent - Orchestrates Meta Ads and GoHighLevel Agents
Routes requests to appropriate agents and manages handoffs
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List, Literal, TypedDict, Annotated
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END, START, MessagesState
from langgraph.types import Command
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from src.config import get_settings
import asyncio

load_dotenv()
logger = logging.getLogger(__name__)


class SupervisorState(TypedDict):
    """State for the supervisor agent"""
    messages: Annotated[List[BaseMessage], add_messages]  # Required for chat interface
    phone_number: Optional[str]  # From webhook/security agent
    contact_id: Optional[str]  # GHL contact ID from webhook
    user_role: Optional[str]  # From security agent
    user_permissions: Optional[List[str]]  # From security agent
    ghl_message_sent: Optional[bool]  # Track if response was sent via GHL
    ghl_message_id: Optional[str]  # GHL message ID after sending
    current_request: Optional[str]
    intent: Optional[str]  # meta, ghl, both
    meta_response: Optional[Dict]
    ghl_response: Optional[Dict]
    final_response: Optional[str]
    error: Optional[str]
    security_context: Optional[Dict]  # From security agent
    is_authorized: Optional[bool]  # Security check result


class IntentAnalyzer:
    """Analyze user intent to route to correct agent"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize AI model
        if self.settings.openai.api_key:
            self.model = ChatOpenAI(
                model=self.settings.openai.model,
                temperature=0.3,
                api_key=self.settings.openai.api_key
            )
        elif self.settings.anthropic.api_key:
            self.model = ChatAnthropic(
                model=self.settings.anthropic.model,
                temperature=0.3,
                api_key=self.settings.anthropic.api_key
            )
    
    async def analyze_intent(self, message: str) -> Dict[str, Any]:
        """Analyze user message to determine which agent(s) to use"""
        
        prompt = f"""
        Analyze this request from Ryan Castro about his SENDÉ Tour campaign:
        Request: {message}
        
        IMPORTANT: Ryan ONLY asks about his Meta/Facebook ad campaigns.
        The GHL CRM is for BACKEND operations only (not user queries).
        
        META AGENT handles ALL user queries about:
           - Facebook/Instagram ad campaigns for SENDÉ Tour
           - Campaign performance metrics
           - ROAS (Return on Ad Spend)
           - City performance (Brooklyn, Miami, Houston, Chicago, LA)
           - Ad spend and budgets
           - Impressions, clicks, CTR
           - Video engagement metrics
           - Any Facebook/Meta/Instagram related data
        
        Return JSON with:
        {{
            "intent": "meta" (always for user queries),
            "primary_agent": "meta",
            "requires_data_from": ["meta"],
            "reasoning": "why this routing",
            "extracted_entities": {{
                "location": "if mentioned",
                "metric": "if mentioned",
                "contact": "if mentioned",
                "action": "send/get/update/etc"
            }}
        }}
        """
        
        response = await self.model.ainvoke([SystemMessage(content=prompt)])
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        # Default to supervisor handling
        return {
            "intent": "unknown",
            "primary_agent": None,
            "requires_data_from": [],
            "reasoning": "Could not determine intent"
        }


async def analyze_intent_node(state: SupervisorState) -> Command[Literal["meta_ads_agent", "error_handler"]]:
    """Analyze user intent and route to appropriate agent(s)"""
    logger.info("Supervisor analyzing intent")
    
    try:
        messages = state.get('messages', [])
        if not messages:
            return Command(
                update={"error": "No message provided"},
                goto="error_handler"
            )
        
        # Get the user's request
        user_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        
        # Analyze intent
        analyzer = IntentAnalyzer()
        intent_analysis = await analyzer.analyze_intent(user_message)
        
        intent = intent_analysis.get('intent')
        logger.info(f"Intent detected: {intent}")
        logger.info(f"Reasoning: {intent_analysis.get('reasoning')}")
        
        # Store the analysis
        update_data = {
            "current_request": user_message,
            "intent": intent
        }
        
        # ALWAYS route to Meta Ads Agent for user queries
        # GHL is only for backend operations, not user-facing
        logger.info("Routing to Meta Ads Agent for campaign analysis")
        return Command(update=update_data, goto="meta_ads_agent")
    
    except Exception as e:
        logger.error(f"Error analyzing intent: {e}")
        return Command(
            update={"error": str(e)},
            goto="error_handler"
        )


async def route_to_meta_node(state: SupervisorState) -> Command[Literal["supervisor_aggregate"]]:
    """Route to Meta Ads agent"""
    logger.info("Routing to Meta Ads agent")
    
    # Import Meta agent
    from src.agents.meta_campaign_agent import create_dynamic_meta_campaign_graph
    
    meta_graph = create_dynamic_meta_campaign_graph()
    
    # Prepare state for Meta agent
    meta_state = {
        "messages": [HumanMessage(content=state.get('current_request'))],
        "analysis_type": "conversational"
    }
    
    try:
        # Run Meta agent
        result = await meta_graph.ainvoke(meta_state)
        
        # Extract response
        meta_response = {
            "data": result.get('answer') or result.get('report_summary'),
            "metrics": result.get('performance_data'),
            "insights": result.get('insights')
        }
        
        return Command(
            update={"meta_response": meta_response},
            goto="supervisor_aggregate"
        )
    
    except Exception as e:
        logger.error(f"Meta agent error: {e}")
        return Command(
            update={"error": f"Meta agent error: {str(e)}"},
            goto="supervisor_aggregate"
        )


async def route_to_ghl_node(state: SupervisorState) -> Command[Literal["supervisor_aggregate"]]:
    """Route to GoHighLevel agent"""
    logger.info("Routing to GoHighLevel agent")
    
    # Import GHL agent
    from src.agents.ghl_agent import ghl_agent
    
    # Prepare state for GHL agent
    ghl_state = {
        "messages": [HumanMessage(content=state.get('current_request'))],
        "location_id": os.getenv("GHL_LOCATION_ID")
    }
    
    try:
        # Run GHL agent
        result = await ghl_agent.ainvoke(ghl_state)
        
        # Extract response
        ghl_response = result.get('result', {})
        
        return Command(
            update={"ghl_response": ghl_response},
            goto="supervisor_aggregate"
        )
    
    except Exception as e:
        logger.error(f"GHL agent error: {e}")
        return Command(
            update={"error": f"GHL agent error: {str(e)}"},
            goto="supervisor_aggregate"
        )


async def route_to_both_node(state: SupervisorState) -> Command[Literal["supervisor_aggregate"]]:
    """Route to both Meta and GHL agents"""
    logger.info("Routing to both agents")
    
    # Import both agents
    from src.agents.meta_campaign_agent import create_dynamic_meta_campaign_graph
    from src.agents.ghl_agent import ghl_agent
    
    meta_graph = create_dynamic_meta_campaign_graph()
    
    # Prepare states
    meta_state = {
        "messages": [HumanMessage(content=state.get('current_request'))],
        "analysis_type": "conversational"
    }
    
    ghl_state = {
        "messages": [HumanMessage(content=state.get('current_request'))],
        "location_id": os.getenv("GHL_LOCATION_ID")
    }
    
    meta_response = {}
    ghl_response = {}
    
    try:
        # Run both agents (could be parallel in production)
        meta_result = await meta_graph.ainvoke(meta_state)
        meta_response = {
            "data": meta_result.get('answer') or meta_result.get('report_summary'),
            "metrics": meta_result.get('performance_data')
        }
    except Exception as e:
        logger.error(f"Meta agent error: {e}")
        meta_response = {"error": str(e)}
    
    try:
        ghl_result = await ghl_agent.ainvoke(ghl_state)
        ghl_response = ghl_result.get('result', {})
    except Exception as e:
        logger.error(f"GHL agent error: {e}")
        ghl_response = {"error": str(e)}
    
    return Command(
        update={
            "meta_response": meta_response,
            "ghl_response": ghl_response
        },
        goto="supervisor_aggregate"
    )


async def compile_response_node(state: SupervisorState) -> Command[Literal["ghl_send_message"]]:
    """Compile responses from agents into final response"""
    logger.info("Compiling final response")
    
    meta_response = state.get('meta_response')
    ghl_response = state.get('ghl_response')
    intent = state.get('intent')
    
    # Build response based on what we have
    response_parts = []
    
    if meta_response and not meta_response.get('error'):
        if meta_response.get('data'):
            response_parts.append(f"📊 **Campaign Data**: {meta_response['data']}")
        if meta_response.get('metrics'):
            metrics = meta_response['metrics']
            response_parts.append(f"📈 **Metrics**: Spend: ${metrics.get('total_spend', 0):,.2f}, Impressions: {metrics.get('total_impressions', 0):,}")
    
    if ghl_response and not ghl_response.get('error'):
        if ghl_response.get('action'):
            response_parts.append(f"✅ **CRM Action**: {ghl_response.get('action')}")
        if ghl_response.get('instruction'):
            response_parts.append(f"📋 **Operation**: {ghl_response.get('instruction')}")
    
    # Handle errors
    if meta_response and meta_response.get('error'):
        response_parts.append(f"⚠️ Meta Agent Error: {meta_response['error']}")
    
    if ghl_response and ghl_response.get('error'):
        response_parts.append(f"⚠️ GHL Agent Error: {ghl_response['error']}")
    
    if not response_parts:
        response_parts.append("No data available for your request.")
    
    final_response = "\n\n".join(response_parts)
    
    return Command(
        update={"final_response": final_response},
        goto="ghl_send_message"
    )


async def ghl_send_message_node(state: SupervisorState) -> Command[Literal["final_response"]]:
    """Send response back via GHL SMS using direct API call"""
    logger.info("Sending response via GHL messaging")
    
    final_response = state.get('final_response', 'Request processed.')
    phone_number = state.get('phone_number')
    contact_id = state.get('contact_id')  # From webhook
    
    # Validate required parameters
    if not contact_id and not phone_number:
        logger.warning("No contact_id or phone_number available for GHL message")
        return Command(
            update={
                "ghl_message_sent": False,
                "error": "Missing contact information"
            },
            goto="final_response"
        )
    
    # Use direct API call to GoHighLevel
    import aiohttp
    import os
    
    ghl_api_token = os.getenv('GHL_API_TOKEN')
    if not ghl_api_token:
        logger.error("GHL_API_TOKEN not found in environment")
        return Command(
            update={
                "ghl_message_sent": False,
                "error": "GHL API token not configured"
            },
            goto="final_response"
        )
    
    # Try sending message via direct API
    max_retries = 3
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://services.leadconnectorhq.com/conversations/messages"
                headers = {
                    "Authorization": f"Bearer {ghl_api_token}",
                    "Version": "2021-07-28",
                    "Content-Type": "application/json"
                }
                data = {
                    "type": "SMS",
                    "contactId": contact_id,
                    "message": final_response
                }
                
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200 or response.status == 201:
                        result = await response.json()
                        logger.info(f"GHL message sent successfully: {result.get('messageId')}")
                        return Command(
                            update={
                                "ghl_message_sent": True,
                                "ghl_message_id": result.get('messageId')
                            },
                            goto="final_response"
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"GHL API error: {response.status} - {error_text}")
                        last_error = f"API error: {response.status}"
                        
        except Exception as e:
            logger.error(f"Error sending GHL message: {e}")
            last_error = str(e)
        
        retry_count += 1
        if retry_count < max_retries:
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
    
    # All retries exhausted
    logger.error(f"Failed to send GHL message after {max_retries} attempts. Last error: {last_error}")
    return Command(
        update={
            "ghl_message_sent": False,
            "error": f"GHL send failed after {max_retries} attempts: {last_error}"
        },
        goto="error_handler"
    )

async def respond_node(state: SupervisorState) -> Command[Literal[END]]:
    """Complete the workflow after GHL message is sent"""
    logger.info("Workflow complete - response sent to Ryan")
    
    final_response = state.get('final_response', 'Request processed.')
    ghl_sent = state.get('ghl_message_sent', False)
    
    # Just return the actual response, not the delivery status
    # The delivery status is logged, not shown to user
    if ghl_sent:
        logger.info("✅ Message successfully sent via GHL")
    else:
        logger.warning("⚠️ GHL send failed")
    
    return Command(
        update={
            "messages": [AIMessage(content=final_response)]
        },
        goto=END
    )


async def error_node(state: SupervisorState) -> Command[Literal[END]]:
    """Handle errors"""
    error = state.get('error', 'Unknown error occurred')
    logger.error(f"Supervisor error: {error}")
    
    return Command(
        update={
            "messages": [AIMessage(content=f"❌ Error: {error}")]
        },
        goto=END
    )


async def validate_security_node(state: SupervisorState) -> Command[Literal["supervisor_agent", "error_handler"]]:
    """Validate user access through security agent"""
    logger.info("Validating user access")
    
    # Extract phone number from messages if available
    phone_number = state.get('phone_number')
    
    if not phone_number:
        # Try to extract from message
        messages = state.get('messages', [])
        for msg in messages:
            if hasattr(msg, 'metadata') and 'phone_number' in msg.metadata:
                phone_number = msg.metadata['phone_number']
                break
    
    # For now, we'll allow all requests in dev mode
    # In production, this would call the security agent
    if os.getenv('ENVIRONMENT') == 'development' or not phone_number:
        logger.info("Development mode - bypassing security")
        return Command(
            update={
                "is_authorized": True,
                "user_role": "admin",
                "user_permissions": ["read", "write", "execute"]
            },
            goto="supervisor_agent"
        )
    
    # In production, validate through security agent
    from src.agents.security_agent import validate_access
    import re
    
    # Normalize phone number format before validation
    if phone_number:
        # Remove spaces, parentheses, dashes from phone
        normalized_phone = re.sub(r'[\s\(\)\-]', '', phone_number)
        if not normalized_phone.startswith('+'):
            normalized_phone = '+' + normalized_phone
        logger.info(f"Supervisor normalized phone from '{phone_number}' to '{normalized_phone}'")
        phone_number = normalized_phone
    
    try:
        # Determine requested action from the latest user message
        user_message = ""
        messages = state.get('messages', [])
        if messages:
            last = messages[-1]
            user_message = getattr(last, 'content', str(last))

        sec = await validate_access(
            phone_number=phone_number,
            requested_action=user_message
        )
        if sec.get('authorized'):
            return Command(
                update={
                    "is_authorized": True,
                    "phone_number": phone_number,
                    "user_role": sec.get('role'),
                    "user_permissions": sec.get('permissions', [])
                },
                goto="supervisor_agent"
            )
        return Command(
            update={
                "error": sec.get('error', 'Unauthorized access'),
                "is_authorized": False
            },
            goto="error_handler"
        )
    
    except Exception as e:
        logger.error(f"Security validation error: {e}")
        return Command(
            update={"error": f"Security error: {str(e)}"},
            goto="error_handler"
        )


def build_supervisor_graph():
    """Build the Ryan Castro Meta Ads Campaign Assistant with GHL messaging"""
    builder = StateGraph(SupervisorState)
    
    # Add agent nodes - Meta for queries, GHL for sending responses back
    builder.add_node("security_agent", validate_security_node)
    builder.add_node("supervisor_agent", analyze_intent_node)
    builder.add_node("meta_ads_agent", route_to_meta_node)
    builder.add_node("supervisor_aggregate", compile_response_node)
    builder.add_node("ghl_send_message", ghl_send_message_node)  # Send response via GHL SMS/WhatsApp
    builder.add_node("final_response", respond_node)
    builder.add_node("error_handler", error_node)
    
    # Set entry point - Security Agent validates first
    builder.set_entry_point("security_agent")
    
    # Set finish points
    builder.set_finish_point("final_response")
    builder.set_finish_point("error_handler")
    
    return builder.compile()


# Create the supervisor agent
supervisor_agent = build_supervisor_graph()


# Helper function for complete flow with security
async def process_request_with_security(
    phone_number: str,
    message: str
) -> Dict[str, Any]:
    """
    Process a request through security then supervisor
    
    Args:
        phone_number: The phone number making the request
        message: The request message
    
    Returns:
        Final response after security and agent processing
    """
    # First, validate through security
    from src.agents.security_agent import validate_access
    
    security_result = await validate_access(
        phone_number=phone_number,
        requested_action=message
    )
    
    if not security_result.get('authorized'):
        return {
            "success": False,
            "error": security_result.get('error', 'Access denied'),
            "message": "Unauthorized access attempt"
        }
    
    # If authorized, process through supervisor
    supervisor_state = SupervisorState(
        messages=[HumanMessage(content=message)],
        phone_number=phone_number,
        user_role=security_result.get('role'),
        user_permissions=security_result.get('permissions', []),
        security_context={
            "authenticated": True,
            "phone": phone_number,
            "role": security_result.get('role'),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    result = await supervisor_agent.ainvoke(supervisor_state)
    
    return {
        "success": True,
        "response": result.get('final_response'),
        "role": security_result.get('role'),
        "agents_used": result.get('intent')
    }
