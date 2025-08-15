"""
Dynamic Meta Campaign Agent - Intelligent SDK usage
"""
import logging
import re
import json
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..config.settings import get_settings
from ..tools.meta_ads_tools import meta_sdk_query, meta_sdk_discover, intelligent_meta_query

logger = logging.getLogger(__name__)


class MetaCampaignState(MessagesState):
    """State for the Meta campaign agent"""
    query: Optional[str]
    time_period: Optional[str]
    location: Optional[str]
    query_params: Optional[Dict]
    raw_data: Optional[Dict]
    answer: Optional[str]
    error: Optional[str]


def extract_time_period(query: str) -> str:
    """Extract time period from query using simple pattern matching"""
    query_lower = query.lower()
    
    # Direct time mappings - no AI needed
    if 'today' in query_lower:
        return 'today'
    elif 'yesterday' in query_lower:
        return 'yesterday'
    elif 'last week' in query_lower or 'this week' in query_lower:
        return 'last_7d'
    elif 'last month' in query_lower or 'this month' in query_lower:
        return 'this_month'
    elif 'last 30' in query_lower:
        return 'last_30d'
    elif 'last 7' in query_lower:
        return 'last_7d'
    elif 'all time' in query_lower or 'total' in query_lower or 'overall' in query_lower:
        return 'maximum'
    
    # Default to maximum to show all data
    return 'maximum'


def extract_location(query: str) -> Optional[str]:
    """Extract location from query"""
    query_lower = query.lower()
    
    # Common tour locations
    locations = {
        'miami': 'Miami',
        'new york': 'New York',
        'los angeles': 'Los Angeles',
        'chicago': 'Chicago',
        'houston': 'Houston',
        'orlando': 'Orlando',
        'atlanta': 'Atlanta',
        'dallas': 'Dallas',
        'phoenix': 'Phoenix',
        'san diego': 'San Diego'
    }
    
    for key, value in locations.items():
        if key in query_lower:
            return value
    
    return None


async def parse_query_node(state: MetaCampaignState) -> Command:
    """Use AI to understand query and determine what SDK calls to make"""
    logger.info("Understanding user query")
    
    messages = state.get('messages', [])
    if not messages:
        return Command(
            update={'error': 'No query provided'},
            goto=END
        )
    
    # Get the user query
    query = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
    
    # Use AI to understand what the user wants
    settings = get_settings()
    
    # Initialize AI model
    model = None
    if settings.openai.api_key:
        model = ChatOpenAI(
            model=settings.openai.model,
            temperature=0.2,
            api_key=settings.openai.api_key
        )
    elif settings.anthropic.api_key:
        model = ChatAnthropic(
            model=settings.anthropic.model,
            temperature=0.2,
            api_key=settings.anthropic.api_key
        )
    
    if model:
        # Ask AI to determine what SDK operation to use
        prompt = f"""
        You have access to the Meta Ads SDK. Given this user query, determine what data to fetch.
        
        User Query: {query}
        
        Available SDK operations:
        1. get_campaign_insights - Get campaign level metrics (NOTE: may not aggregate all data correctly)
        2. get_adsets_insights - Get ad set level metrics (MORE ACCURATE for totals)
        
        IMPORTANT: For accurate sales/purchase totals, use get_adsets_insights at adset level
        
        Valid fields for insights:
        - spend, impressions, clicks, reach, frequency
        - cpm, cpc, ctr, cpp
        - actions (contains purchases, add_to_cart, etc.)
        - action_values (contains purchase revenue)
        - campaign_name, campaign_id, adset_name, adset_id
        
        For sales/purchases: use "actions" field
        For revenue: use "action_values" field
        
        Time periods: today, yesterday, last_7d, last_30d, maximum
        
        CRITICAL: Default to "maximum" (all-time data) UNLESS the user specifically mentions:
        - "today" → use "today"
        - "yesterday" → use "yesterday"
        - Otherwise → use "maximum"
        
        Return JSON:
        {{
            "operation": "get_adsets_insights",
            "campaign_id": "120232002620350525",
            "date_preset": "maximum or today or yesterday",
            "fields": ["adset_name", "actions", "action_values", "spend", "impressions", "clicks"],
            "level": "adset",
            "reasoning": "brief explanation"
        }}
        """
        
        response = await model.ainvoke([SystemMessage(content=prompt)])
        
        # Parse JSON from response
        import json
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            query_params = json.loads(json_match.group())
            logger.info(f"AI determined SDK params: {query_params}")
        else:
            # Fallback to simple extraction
            time_period = extract_time_period(query)
            query_params = {
                'operation': 'get_campaign_insights',
                'campaign_id': '120232002620350525',
                'date_preset': time_period,
                'fields': ['campaign_name', 'spend', 'impressions', 'clicks', 'actions', 'action_values'],
                'level': 'campaign'
            }
    else:
        # Fallback without AI
        time_period = extract_time_period(query)
        query_params = {
            'operation': 'get_campaign_insights',
            'campaign_id': '120232002620350525',
            'date_preset': time_period,
            'fields': ['campaign_name', 'spend', 'impressions', 'clicks', 'actions', 'action_values'],
            'level': 'campaign'
        }
    
    return Command(
        update={
            'query': query,
            'query_params': query_params,
            'time_period': query_params.get('date_preset', 'maximum'),
            'location': None  # Could extract from query if needed
        },
        goto='execute_query'
    )


async def execute_query_node(state: MetaCampaignState) -> Command:
    """Execute the Meta API query"""
    logger.info("Executing Meta API query")
    
    query_params = state.get('query_params')
    if not query_params:
        return Command(
            update={'error': 'No query parameters'},
            goto=END
        )
    
    try:
        # Use the existing meta_sdk_query function
        result = meta_sdk_query.invoke({'query': query_params})
        
        if isinstance(result, dict) and result.get('error'):
            return Command(
                update={'error': result['error']},
                goto=END
            )
        
        # Wrap result in expected format
        if isinstance(result, list):
            data = {'data': result}
        else:
            data = result
            
        logger.info(f"Query successful - {len(data.get('data', []))} campaigns found")
        
        return Command(
            update={'raw_data': data},
            goto='format_response'
        )
    
    except Exception as e:
        logger.error(f"Query error: {e}")
        return Command(
            update={'error': str(e)},
            goto=END
        )


async def format_response_node(state: MetaCampaignState) -> Command:
    """Format the response for the user - dynamically based on query"""
    logger.info("Formatting response")
    
    raw_data = state.get('raw_data', {})
    data = raw_data.get('data', [])
    time_period = state.get('time_period', 'maximum')
    location = state.get('location')
    query = state.get('query', '')
    query_params = state.get('query_params', {})
    
    if not data:
        response = f"No data found for {time_period}"
        if location:
            response += f" in {location}"
    else:
        # Use AI to understand what the user is asking for and format appropriately
        settings = get_settings()
        
        # Initialize AI model
        model = None
        if settings.openai.api_key:
            model = ChatOpenAI(
                model=settings.openai.model,
                temperature=0.2,
                api_key=settings.openai.api_key
            )
        elif settings.anthropic.api_key:
            model = ChatAnthropic(
                model=settings.anthropic.model,
                temperature=0.2,
                api_key=settings.anthropic.api_key
            )
        
        if model:
            # First, let's aggregate the data ourselves for accuracy
            total_purchases = 0
            total_revenue = 0
            total_spend = 0
            total_impressions = 0
            total_clicks = 0
            
            for item in data:
                # Extract spend, impressions, clicks
                total_spend += float(item.get('spend', 0))
                total_impressions += int(float(item.get('impressions', 0)))
                total_clicks += int(float(item.get('clicks', 0)))
                
                # Extract purchases from actions
                if 'actions' in item and isinstance(item['actions'], list):
                    for action in item['actions']:
                        if action.get('action_type') == 'purchase':
                            total_purchases += int(float(action.get('value', 0)))
                
                # Extract revenue from action_values
                if 'action_values' in item and isinstance(item['action_values'], list):
                    for av in item['action_values']:
                        if av.get('action_type') == 'purchase':
                            total_revenue += float(av.get('value', 0))
            
            # Now ask AI to format a nice response with the aggregated data
            format_prompt = f"""
            User asked: {query}
            Time period: {time_period}
            
            Aggregated data:
            - Total purchases/sales: {total_purchases}
            - Total revenue: ${total_revenue:.2f}
            - Total spend: ${total_spend:.2f}
            - Total impressions: {total_impressions:,}
            - Total clicks: {total_clicks:,}
            - CTR: {(total_clicks/total_impressions*100) if total_impressions > 0 else 0:.2f}%
            - ROAS: {(total_revenue/total_spend) if total_spend > 0 else 0:.2f}x
            
            Based on what the user asked, provide a direct answer.
            If they asked "how many sales today" and it's 0, say "0 sales today"
            If they asked "how many sales today" and it's 5, say "5 sales today"
            Be concise and direct.
            """
            
            response_ai = await model.ainvoke([SystemMessage(content=format_prompt)])
            response = response_ai.content
        else:
            # Fallback to basic aggregation
            metrics = {}
            
            # Aggregate all numeric fields dynamically
            for item in data:
                for key, value in item.items():
                    if isinstance(value, (int, float, str)):
                        try:
                            num_val = float(value)
                            metrics[key] = metrics.get(key, 0) + num_val
                        except:
                            pass
                    elif key == 'actions' and isinstance(value, list):
                        for action in value:
                            action_type = action.get('action_type', '')
                            metrics[f'action_{action_type}'] = metrics.get(f'action_{action_type}', 0) + float(action.get('value', 0))
                    elif key == 'action_values' and isinstance(value, list):
                        for av in value:
                            action_type = av.get('action_type', '')
                            metrics[f'revenue_{action_type}'] = metrics.get(f'revenue_{action_type}', 0) + float(av.get('value', 0))
            
            # Format based on query keywords
            if 'sales' in query.lower() or 'purchases' in query.lower():
                sales = int(metrics.get('action_purchase', 0))
                response = f"**{sales} sales {time_period}**"
            elif 'revenue' in query.lower():
                revenue = metrics.get('revenue_purchase', 0)
                response = f"**${revenue:,.2f} revenue {time_period}**"
            elif 'spend' in query.lower() or 'cost' in query.lower():
                spend = metrics.get('spend', 0)
                response = f"**${spend:,.2f} spent {time_period}**"
            elif 'impressions' in query.lower():
                impressions = int(metrics.get('impressions', 0))
                response = f"**{impressions:,} impressions {time_period}**"
            else:
                # Generic response with key metrics
                response = f"**Metrics for {time_period}:**\n"
                for key, value in sorted(metrics.items())[:10]:
                    if isinstance(value, float) and value > 0:
                        response += f"- {key}: {value:,.2f}\n"
        
    
    return Command(
        update={
            'answer': response,
            'messages': [AIMessage(content=response)]
        },
        goto=END
    )


def create_dynamic_meta_campaign_graph():
    """Create the simplified Meta campaign graph"""
    builder = StateGraph(MetaCampaignState)
    
    # Add nodes
    builder.add_node("parse_query", parse_query_node)
    builder.add_node("execute_query", execute_query_node)
    builder.add_node("format_response", format_response_node)
    
    # Set entry point
    builder.add_edge(START, "parse_query")
    
    # Add edges
    # parse_query -> execute_query or END (handled by Command)
    # execute_query -> format_response or END (handled by Command)
    # format_response -> END (handled by Command)
    
    return builder.compile()


# Alias for compatibility
meta_campaign_agent = create_dynamic_meta_campaign_graph()