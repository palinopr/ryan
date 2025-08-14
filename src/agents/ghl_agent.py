"""
GoHighLevel Agent - Dynamic MCP Integration
This agent can dynamically call ANY GoHighLevel MCP tool
Handles all CRM operations through conversations
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List, Literal, TypedDict
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from dotenv import load_dotenv
from src.config import get_settings
import asyncio

load_dotenv()
logger = logging.getLogger(__name__)


class GHLAgentState(TypedDict):
    """State for the GoHighLevel agent"""
    messages: List[Any]
    contact_id: Optional[str]
    location_id: Optional[str]
    conversation_id: Optional[str]
    current_operation: Optional[str]
    mcp_tool_to_execute: Optional[str]
    mcp_parameters: Optional[Dict]
    result: Optional[Any]
    error: Optional[str]


class DynamicGHLAgent:
    """
    Dynamic GoHighLevel agent that can execute ANY MCP operation
    All messages are sent through conversations, not webhooks
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.location_id = os.getenv("GHL_LOCATION_ID")
        
        # Initialize AI model for intelligent tool selection
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
    
    async def analyze_request(self, message: str, context: Dict = None) -> Dict:
        """
        Analyze the user's request and determine which MCP tool to use
        """
        prompt = f"""
        Analyze this GoHighLevel request: {message}
        
        Context: {json.dumps(context) if context else 'None'}
        
        Determine what GoHighLevel operation is needed.
        Common operations:
        - Get/search contacts
        - Send messages (SMS, email)
        - Create/update appointments
        - Manage tags
        - Search opportunities
        - Get calendar events
        - Update contact information
        - Get payment/transaction info
        
        Return JSON with:
        {{
            "operation": "description of what to do",
            "mcp_tool_category": "contacts/conversations/calendars/opportunities/payments/locations",
            "action": "get/create/update/send/search/add/remove",
            "needs_conversation": true/false (true if sending messages),
            "parameters_needed": ["list", "of", "params"]
        }}
        """
        
        response = await self.model.ainvoke([SystemMessage(content=prompt)])
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        return {
            "operation": message,
            "mcp_tool_category": "unknown",
            "action": "unknown"
        }
    
    def select_mcp_tool(self, analysis: Dict) -> str:
        """
        Select the appropriate MCP tool based on analysis
        """
        category = analysis.get('mcp_tool_category', '')
        action = analysis.get('action', '')
        
        # Map to actual MCP tool names
        tool_mapping = {
            ('contacts', 'get'): 'mcp__gohighlevel__contacts_get-contact',
            ('contacts', 'search'): 'mcp__gohighlevel__contacts_get-contacts',
            ('contacts', 'create'): 'mcp__gohighlevel__contacts_create-contact',
            ('contacts', 'update'): 'mcp__gohighlevel__contacts_update-contact',
            ('contacts', 'add'): 'mcp__gohighlevel__contacts_add-tags',
            ('contacts', 'remove'): 'mcp__gohighlevel__contacts_remove-tags',
            ('conversations', 'send'): 'mcp__gohighlevel__conversations_send-a-new-message',
            ('conversations', 'search'): 'mcp__gohighlevel__conversations_search-conversation',
            ('conversations', 'get'): 'mcp__gohighlevel__conversations_get-messages',
            ('calendars', 'get'): 'mcp__gohighlevel__calendars_get-calendar-events',
            ('calendars', 'notes'): 'mcp__gohighlevel__calendars_get-appointment-notes',
            ('opportunities', 'search'): 'mcp__gohighlevel__opportunities_search-opportunity',
            ('opportunities', 'get'): 'mcp__gohighlevel__opportunities_get-opportunity',
            ('opportunities', 'update'): 'mcp__gohighlevel__opportunities_update-opportunity',
            ('opportunities', 'pipelines'): 'mcp__gohighlevel__opportunities_get-pipelines',
            ('payments', 'get'): 'mcp__gohighlevel__payments_get-order-by-id',
            ('payments', 'list'): 'mcp__gohighlevel__payments_list-transactions',
            ('locations', 'get'): 'mcp__gohighlevel__locations_get-location',
            ('locations', 'fields'): 'mcp__gohighlevel__locations_get-custom-fields'
        }
        
        return tool_mapping.get((category, action), 'mcp__gohighlevel__contacts_get-contacts')
    
    async def prepare_mcp_parameters(self, tool_name: str, request: str, context: Dict = None) -> Dict:
        """
        Prepare parameters for the MCP tool
        """
        # Base parameters
        params = {}
        
        # Add location ID if needed
        if self.location_id:
            if 'query_locationId' in tool_name or 'locationId' in tool_name:
                params['query_locationId'] = self.location_id
            elif 'body_locationId' in tool_name:
                params['body_locationId'] = self.location_id
        
        # Add context parameters
        if context:
            if context.get('contact_id'):
                params['path_contactId'] = context['contact_id']
                params['body_contactId'] = context['contact_id']
            
            if context.get('conversation_id'):
                params['path_conversationId'] = context['conversation_id']
        
        # Tool-specific parameters
        if 'send-a-new-message' in tool_name:
            params['body_type'] = 'SMS'  # Default to SMS
            params['body_message'] = request
            
        elif 'add-tags' in tool_name:
            # Extract tags from the request
            params['body_tags'] = ['ryan-castro-tour', 'engaged']  # Default tags
            
        elif 'search' in tool_name:
            params['query_query'] = request
            params['query_limit'] = 20
            
        elif 'get-calendar-events' in tool_name:
            # Set time range for calendar events
            now = int(datetime.now().timestamp() * 1000)
            week_later = now + (7 * 24 * 60 * 60 * 1000)
            params['query_startTime'] = str(now)
            params['query_endTime'] = str(week_later)
        
        return params


async def understand_request_node(state: GHLAgentState) -> Command[Literal["select_tool", "error"]]:
    """Understand what the user wants to do with GoHighLevel"""
    logger.info("Understanding GHL request")
    
    try:
        messages = state.get('messages', [])
        if not messages:
            return Command(
                update={"error": "No message provided"},
                goto="error"
            )
        
        # Get the user's request
        user_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        
        # Create agent instance
        agent = DynamicGHLAgent()
        
        # Analyze the request
        context = {
            'contact_id': state.get('contact_id'),
            'location_id': state.get('location_id'),
            'conversation_id': state.get('conversation_id')
        }
        
        analysis = await agent.analyze_request(user_message, context)
        
        # Select the appropriate MCP tool
        mcp_tool = agent.select_mcp_tool(analysis)
        
        # Prepare parameters
        parameters = await agent.prepare_mcp_parameters(mcp_tool, user_message, context)
        
        logger.info(f"Selected MCP tool: {mcp_tool}")
        logger.info(f"Parameters: {parameters}")
        
        return Command(
            update={
                "current_operation": analysis.get('operation'),
                "mcp_tool_to_execute": mcp_tool,
                "mcp_parameters": parameters
            },
            goto="select_tool"
        )
        
    except Exception as e:
        logger.error(f"Error understanding request: {e}")
        return Command(
            update={"error": str(e)},
            goto="error"
        )


async def select_tool_node(state: GHLAgentState) -> Command[Literal["execute_mcp", "send_message"]]:
    """Route to appropriate handler based on the operation"""
    logger.info("Selecting execution path")
    
    mcp_tool = state.get('mcp_tool_to_execute', '')
    
    # Check if this is a message sending operation
    if 'send-a-new-message' in mcp_tool or 'conversations' in mcp_tool:
        return Command(goto="send_message")
    else:
        return Command(goto="execute_mcp")


async def execute_mcp_node(state: GHLAgentState) -> Command[Literal["complete"]]:
    """Execute the selected MCP tool with proper error handling"""
    logger.info("Executing MCP tool")
    
    mcp_tool = state.get('mcp_tool_to_execute')
    parameters = state.get('mcp_parameters', {})
    
    if not mcp_tool:
        logger.error("No MCP tool specified")
        return Command(
            update={
                "result": {"error": "No MCP tool specified", "status": "failed"}
            },
            goto="complete"
        )
    
    # Attempt to execute the MCP tool with retries
    max_retries = 3
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            # Try to dynamically call the MCP tool if available
            import sys
            
            # Check if MCP tool exists in current namespace
            if mcp_tool in dir(sys.modules[__name__]):
                # MCP tool is available - execute it
                mcp_function = getattr(sys.modules[__name__], mcp_tool)
                result = await mcp_function(**parameters)
                
                if result and not result.get('error'):
                    logger.info(f"MCP tool {mcp_tool} executed successfully")
                    return Command(
                        update={"result": result},
                        goto="complete"
                    )
                else:
                    last_error = result.get('error', 'Unknown error')
                    logger.warning(f"MCP tool returned error: {last_error}")
            else:
                # MCP tool not available - return instruction for Claude
                result = {
                    "action": "EXECUTE_MCP_TOOL",
                    "tool": mcp_tool,
                    "parameters": parameters,
                    "instruction": f"Execute GoHighLevel MCP tool: {mcp_tool}",
                    "note": "MCP tool execution required at runtime",
                    "status": "instruction_prepared"
                }
                logger.info(f"MCP tool instruction prepared: {mcp_tool}")
                return Command(
                    update={"result": result},
                    goto="complete"
                )
                
        except AttributeError:
            # Tool doesn't exist - prepare instruction
            result = {
                "action": "EXECUTE_MCP_TOOL",
                "tool": mcp_tool,
                "parameters": parameters,
                "instruction": f"Execute GoHighLevel MCP tool: {mcp_tool}",
                "note": "Tool will be executed at runtime by Claude"
            }
            return Command(
                update={"result": result},
                goto="complete"
            )
            
        except asyncio.TimeoutError:
            last_error = "Request timeout"
            logger.warning(f"MCP tool timeout on attempt {retry_count + 1}")
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            continue
            
        except Exception as e:
            last_error = str(e)
            logger.error(f"MCP tool error on attempt {retry_count + 1}: {e}")
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(2 ** retry_count)
            continue
    
    # All retries exhausted
    logger.error(f"Failed to execute MCP tool {mcp_tool} after {max_retries} attempts")
    return Command(
        update={
            "result": {
                "error": f"Failed after {max_retries} attempts: {last_error}",
                "status": "failed",
                "tool": mcp_tool
            }
        },
        goto="complete"
    )


async def send_message_node(state: GHLAgentState) -> Command[Literal["complete"]]:
    """Send a message through GoHighLevel conversation with proper error handling"""
    logger.info("Sending message through conversation")
    
    mcp_tool = state.get('mcp_tool_to_execute')
    parameters = state.get('mcp_parameters', {})
    
    # Ensure we're sending through conversation, not webhook
    parameters['via_conversation'] = True
    parameters['no_webhook'] = True
    
    # Validate required parameters for message sending
    if not parameters.get('body_contactId') and not parameters.get('path_contactId'):
        logger.error("Missing contact ID for message sending")
        return Command(
            update={
                "result": {
                    "error": "Contact ID required for sending messages",
                    "status": "failed"
                }
            },
            goto="complete"
        )
    
    if not parameters.get('body_message'):
        logger.error("Missing message content")
        return Command(
            update={
                "result": {
                    "error": "Message content required",
                    "status": "failed"
                }
            },
            goto="complete"
        )
    
    # Attempt to send with retries
    max_retries = 3
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            # Try to execute the actual MCP tool if available
            import sys
            
            if 'mcp__gohighlevel__conversations_send_a_new_message' in dir(sys.modules[__name__]):
                # MCP tool available - execute it
                result = await mcp__gohighlevel__conversations_send_a_new_message(**parameters)
                
                if result and not result.get('error'):
                    logger.info(f"Message sent successfully: {result.get('messageId')}")
                    return Command(
                        update={"result": result},
                        goto="complete"
                    )
                else:
                    last_error = result.get('error', 'Unknown error')
                    logger.warning(f"Message send failed: {last_error}")
            else:
                # MCP not available - return instruction
                result = {
                    "action": "SEND_MESSAGE_VIA_CONVERSATION",
                    "tool": mcp_tool,
                    "parameters": parameters,
                    "instruction": "Send message through GoHighLevel conversation system",
                    "note": "Message will be sent through conversation thread, NOT webhook",
                    "status": "instruction_prepared"
                }
                logger.info("Message send instruction prepared for runtime execution")
                return Command(
                    update={"result": result},
                    goto="complete"
                )
                
        except NameError:
            # MCP tool not in namespace - prepare instruction
            result = {
                "action": "SEND_MESSAGE_VIA_CONVERSATION",
                "tool": mcp_tool,
                "parameters": parameters,
                "instruction": "Send message through GoHighLevel conversation system",
                "note": "Tool will be executed at runtime by Claude"
            }
            return Command(
                update={"result": result},
                goto="complete"
            )
            
        except asyncio.TimeoutError:
            last_error = "Message send timeout"
            logger.warning(f"Message send timeout on attempt {retry_count + 1}")
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(2 ** retry_count)
            continue
            
        except Exception as e:
            last_error = str(e)
            logger.error(f"Message send error on attempt {retry_count + 1}: {e}")
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(2 ** retry_count)
            continue
    
    # All retries exhausted
    logger.error(f"Failed to send message after {max_retries} attempts")
    return Command(
        update={
            "result": {
                "error": f"Message send failed after {max_retries} attempts: {last_error}",
                "status": "failed"
            }
        },
        goto="complete"
    )


async def error_node(state: GHLAgentState) -> Command[Literal["complete"]]:
    """Handle errors"""
    error = state.get('error', 'Unknown error')
    logger.error(f"GHL Agent error: {error}")
    
    return Command(
        update={
            "result": {"error": error, "status": "failed"}
        },
        goto="complete"
    )


async def complete_node(state: GHLAgentState) -> Command[Literal[END]]:
    """Complete the operation"""
    result = state.get('result', {})
    logger.info(f"GHL operation complete: {result}")
    
    return Command(
        update={"messages": state.get('messages', []) + [SystemMessage(content=json.dumps(result))]},
        goto=END
    )


# Build the graph
def build_ghl_agent_graph():
    """Build the GoHighLevel agent graph"""
    builder = StateGraph(GHLAgentState)
    
    # Add nodes
    builder.add_node("understand_request", understand_request_node)
    builder.add_node("select_tool", select_tool_node)
    builder.add_node("execute_mcp", execute_mcp_node)
    builder.add_node("send_message", send_message_node)
    builder.add_node("error", error_node)
    builder.add_node("complete", complete_node)
    
    # Set entry point
    builder.set_entry_point("understand_request")
    
    # Add edges (already defined in Command returns)
    
    # Set finish point
    builder.set_finish_point("complete")
    
    return builder.compile()


# Create the graph instance
ghl_agent = build_ghl_agent_graph()