"""
Meta Ads Campaign Report Agent - Dynamic Version
Uses intelligent SDK access to fetch any data dynamically
"""
import logging
import json
import re
import os
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..config.settings import get_settings
from ..tools.meta_ads_tools import (
    meta_sdk_query,
    meta_sdk_discover,
    intelligent_meta_query
)
from ..tools.meta_ads_intelligence import (
    analyze_campaign_health,
    detect_performance_anomalies,
    predict_campaign_performance,
    generate_optimization_plan,
    compare_campaign_performance,
    export_campaign_report,
    create_alert_rules,
    get_competitive_benchmarks
)

logger = logging.getLogger(__name__)


async def check_query_restrictions(question: str) -> Optional[str]:
    """
    Use AI to understand if a query is asking for restricted strategic information.
    Returns an error message if restricted, None if allowed.
    
    Clients can ask about ANY metrics/insights but NOT about strategy/structure.
    """
    settings = get_settings()
    
    # Get AI model
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
    
    if not model:
        # Fallback: allow all queries if no AI available
        return None
    
    prompt = f"""
    You are a security filter for a Meta Ads reporting system.
    The client has READ-ONLY access to view metrics and performance data.
    
    Analyze this question: {question}
    
    ALWAYS ALLOWED (return "allowed"):
    - "How is [city/location] doing?" - asking for performance metrics
    - "How is [campaign] performing?" - asking for results
    - Performance metrics (CTR, CPC, spend, impressions, ROAS, etc.)
    - Campaign/adset/ad data and results
    - Geographic performance (Miami, LA, NYC, etc.)
    - Time-based reports (today, yesterday, this week)
    - Comparisons between cities or time periods
    - Any questions about WHAT the results/metrics are
    
    ONLY RESTRICTED (return "restricted"):
    - "How do you create campaigns?" - asking about creation process
    - "How is the campaign structured?" - asking about internal structure
    - WHY certain strategies are used
    - WHEN we make updates/changes internally
    - Optimization methods or strategies
    - Creative content details
    - Requests to modify/change anything
    - Internal processes or algorithms
    
    IMPORTANT: "How is X doing?" or "How is X performing?" means show me the METRICS, not the strategy.
    
    Return ONLY one word: "allowed" or "restricted"
    """
    
    try:
        response = await model.ainvoke([SystemMessage(content=prompt)])
        decision = response.content.strip().lower()
        
        if "restricted" in decision:
            return (
                "🔒 **RESTRICTED INFORMATION**\n\n"
                "This information is proprietary to Outlet Media and cannot be shared.\n\n"
                "You have access to view all performance metrics and insights:\n"
                "• Campaign, AdSet, Ad, and Asset performance metrics\n"
                "• All available insights for any date range\n"
                "• City/location performance data\n"
                "• CTR, CPC, CPM, ROAS, impressions, clicks, spend, etc.\n\n"
                "For strategic questions, please contact your Outlet Media account manager."
            )
        return None
    except:
        # On error, be permissive
        return None


class MetaCampaignState(MessagesState):
    """State for Meta campaign analysis with dynamic SDK access"""
    # Input
    campaign_id: Optional[str] = None
    date_range: str = "last_30d"
    analysis_type: str = "comprehensive"
    current_question: Optional[str] = None
    phone_number: Optional[str] = None  # User's phone for security context
    language: str = "en"  # Language for responses (es, en, etc.)
    
    # Intent detection
    question_intent: Optional[str] = None  # quick_stat, location, comparison, report, etc.
    detected_entities: Optional[Dict] = None  # {location: "Miami", metric: "CTR", etc.}
    
    # Dynamic data fetched via SDK
    campaign_data: Optional[Dict[str, Any]] = None
    insights_data: Optional[List[Dict]] = None
    adsets_data: Optional[List[Dict]] = None
    ads_data: Optional[List[Dict]] = None
    demographics_data: Optional[Dict] = None
    custom_data: Optional[Dict] = None
    
    # Analysis results
    insights: List[str] = []
    recommendations: List[str] = []
    report_summary: Optional[str] = None
    answer: Optional[str] = None
    
    # Workflow
    stage: str = "initializing"
    error: Optional[str] = None


class DynamicMetaCampaignAnalyzer:
    """AI-powered analyzer with dynamic SDK access"""
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.model = self._get_model()
    
    def _get_model(self):
        """Get configured AI model"""
        if self.settings.openai.api_key:
            return ChatOpenAI(
                model=self.settings.openai.model,
                temperature=self.settings.openai.temperature,
                api_key=self.settings.openai.api_key
            )
        elif self.settings.anthropic.api_key:
            return ChatAnthropic(
                model=self.settings.anthropic.model,
                temperature=self.settings.anthropic.temperature,
                api_key=self.settings.anthropic.api_key
            )
        else:
            raise ValueError("No AI model API key configured")
    
    async def analyze_with_intelligence(self, state: MetaCampaignState) -> Dict[str, Any]:
        """
        Use AI to intelligently analyze the data and determine what else to fetch
        """
        campaign_data = state.get('campaign_data', {})
        insights_data = state.get('insights_data', [])
        
        analysis_prompt = f"""You are an expert Meta Ads analyst with access to the full Meta SDK.
        
Current campaign data:
{json.dumps(campaign_data, indent=2)[:1000]}

Current insights:
{json.dumps(insights_data, indent=2)[:1000]}

User's question: {state.get('current_question', 'General campaign analysis')}

Based on this data and the user's question, determine:
1. What additional data should we fetch from Meta SDK to provide a complete answer?
2. What specific insights can you derive from the current data?
3. What recommendations would you make?

Provide your response as JSON with these keys:
- additional_queries: List of Meta SDK queries to fetch more data
- insights: List of key insights
- recommendations: List of actionable recommendations
- needs_more_data: Boolean indicating if more data is needed
"""
        
        response = await self.model.ainvoke([SystemMessage(content=analysis_prompt)])
        
        try:
            # Parse AI response
            content = response.content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "additional_queries": [],
            "insights": ["Campaign is active and running"],
            "recommendations": ["Continue monitoring performance"],
            "needs_more_data": False
        }


# --- Dynamic NL-to-SDK Planner/Executor ------------------------------------
async def plan_and_execute_dynamic_queries(question: str,
                                           campaign_id: Optional[str],
                                           date_hint: Optional[str] = None,
                                           language: str = "en") -> Optional[str]:
    """
    Use an LLM to plan Meta SDK queries from natural language, execute them via tools,
    and synthesize an answer. Returns None on failure (caller should fallback).
    """
    # Check for restricted queries FIRST
    restriction_msg = await check_query_restrictions(question)
    if restriction_msg:
        return restriction_msg
    
    # Use default campaign if not provided
    if not campaign_id:
        campaign_id = os.getenv("DEFAULT_CAMPAIGN_ID", "120232002620350525")
    
    settings = get_settings()

    # Choose model if available
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

    if model is None:
        return None

    # Describe the allowed schema to the model
    schema_prompt = f"""
You translate a user's Meta Ads question into one or more SDK queries.
Return STRICT JSON with keys: queries, needs_search, search (optional), answer_style.

Schema:
{{
  "needs_search": boolean,
  "search": {{"type": "campaigns|adsets|ads", "term": string}} | null,
  "answer_style": "bullet|narrative|table",
  "queries": [
    {{
      "operation": "custom_query|get_campaign_insights|get_adsets_insights|get_all_campaigns",
      "object_type": "campaign|adset|ad|adaccount|null",
      "object_id": string | null,
      "edge": "insights|ads|adsets|null",
      "fields": [string,...],
      "params": {{
        "date_preset": "today|yesterday|last_7d|last_30d|this_month",
        "breakdowns": [string,...],
        "level": "campaign|adset|ad|null",
        "time_increment": "1|7|null"
      }}
    }}
  ]
}}

Rules:
- IMPORTANT: Cities/locations in Meta Ads are represented as AdSet names. When user asks for city-level data, use get_adsets_insights.
- Prefer operations that match user intent; use get_campaign_insights for high-level metrics and breakdowns; get_adsets_insights when asking per-adset/city; use custom_query when fetching object fields or non-insights edges.
- If a campaign is implied but no ID provided, set needs_search=true and populate search with type="campaigns" and a term (e.g., "SENDÉ Tour").
- Include fields needed to answer (e.g., impressions, clicks, spend, ctr, cpc, cpm, actions, action_values, purchase_roas). If asking about conversions/ROAS, include actions and action_values.
- Always include a date_preset. If none given, use "{date_hint or 'last_7d'}".
- Never use "city" as a breakdown - cities are AdSet names in Meta Ads.

User question: {question}
Campaign id (if known): {campaign_id or 'null'}
Return only JSON.
"""

    try:
        resp = await model.ainvoke([SystemMessage(content=schema_prompt)])
        import re, json as _json
        m = re.search(r"\{[\s\S]*\}", resp.content)
        if not m:
            return None
        plan = _json.loads(m.group())
    except Exception:
        return None

    # Resolve search if needed
    try:
        if plan.get("needs_search"):
            s = plan.get("search") or {}
            search_type = s.get("type", "campaigns")
            term = s.get("term") or ""
            if term:
                matches = meta_sdk_search.invoke(search_type, term)  # type: ignore[arg-type]
                first = next((m for m in matches if isinstance(m, dict) and m.get("id")), None)
                if first:
                    found_id = first.get("id")
                    # Back-fill object_id for any query missing it
                    for q in plan.get("queries", []):
                        if q.get("object_type") in ("campaign", None) and not q.get("object_id"):
                            q["object_id"] = found_id
                    if not campaign_id:
                        campaign_id = found_id

        # Ensure campaign_id presence when appropriate
        if campaign_id:
            for q in plan.get("queries", []):
                # For get_adsets_insights, we need campaign_id
                if q.get("operation") == "get_adsets_insights":
                    if not q.get("campaign_id"):
                        q["campaign_id"] = campaign_id
                    # Also set object_id if not present (for compatibility)
                    if not q.get("object_id"):
                        q["object_id"] = campaign_id
                # For other campaign operations
                elif q.get("object_type") in (None, "campaign") and not q.get("object_id"):
                    q["object_id"] = campaign_id
    except Exception:
        # If search fails, continue; downstream may still work for generic ops
        pass

    # Execute queries
    results = []
    try:
        queries = plan.get("queries", [])
        for q in queries:
            # meta_sdk_query expects a dict under key "query" or full dict? It accepts a dict directly (our tool wrapper sends execute_query)
            res = meta_sdk_query.invoke({"query": q})
            results.append(res)
    except Exception:
        return None

    # Synthesize a simple answer
    try:
        # Collect all result items
        items = []
        for res in results:
            if isinstance(res, list):
                items.extend([r for r in res if isinstance(r, dict)])
            elif isinstance(res, dict):
                items.append(res)
        
        # Check if this is city/adset data (cities are represented as adsets)
        is_city_data = False
        if items:
            # Check if results contain adset_name or city field, or if query was for adsets
            first_item = items[0]
            if ('adset_name' in first_item or 'city' in first_item or 
                any(q.get('operation') == 'get_adsets_insights' for q in queries)):
                is_city_data = True
            
            # Don't hardcode cities - let the data tell us if it's city/location data
            # Cities are represented as adsets in the campaign
        
        # If it's city data, use the client-friendly formatter
        if is_city_data and items:
            return format_city_data_for_client(items, question)
        
        # Otherwise, use the original aggregation logic
        def pick(v, k, default=0):
            try:
                return float(v.get(k, default))
            except Exception:
                return default

        aggregates = {"spend": 0.0, "impressions": 0.0, "clicks": 0.0, "revenue": 0.0}
        
        for it in items:
            aggregates["spend"] += pick(it, "spend")
            aggregates["impressions"] += pick(it, "impressions")
            aggregates["clicks"] += pick(it, "clicks")
            # Attempt revenue from action_values
            if isinstance(it.get("action_values"), list):
                for av in it["action_values"]:
                    if "purchase" in str(av.get("action_type", "")).lower():
                        try:
                            aggregates["revenue"] += float(av.get("value", 0))
                        except Exception:
                            pass

        ctr = (aggregates["clicks"] / aggregates["impressions"] * 100.0) if aggregates["impressions"] else 0.0
        roas = (aggregates["revenue"] / aggregates["spend"]) if aggregates["spend"] else 0.0
        summary = (
            f"Results for {date_hint or 'recent period'}: "
            f"${aggregates['spend']:.2f} spend, {int(aggregates['impressions']):,} impressions, "
            f"{int(aggregates['clicks'])} clicks (CTR {ctr:.2f}%), ROAS {roas:.2f}x."
        )

        # Add a few top lines if present
        sample = items[:3]
        extras = []
        for s in sample:
            name = s.get("campaign_name") or s.get("adset_name") or s.get("ad_name") or s.get("name")
            if name:
                extras.append(f"• {name}: spend ${pick(s,'spend'):.2f}, clicks {int(pick(s,'clicks'))}, CTR {pick(s,'ctr'):.2f}%")
        if extras:
            summary += "\n" + "\n".join(extras)

        return summary
    except Exception:
        return None


def format_city_data_for_client(data: List[Dict], question: str = None, language: str = "en") -> str:
    """Format city/adset data based on the user's question context - dynamically discovers cities"""
    if not data:
        if language == "es":
            return "No hay datos de campaña disponibles para el período seleccionado."
        return "No campaign data available for the selected period."
    
    # Intelligently determine what the user is asking for
    question_lower = question.lower() if question else ""
    
    # Dynamically discover what cities/locations are in the data
    available_cities = {}
    for item in data:
        adset_name = item.get('adset_name', '').replace('Sende Tour - ', '').replace('SENDE Tour - ', '')
        if adset_name:
            available_cities[adset_name.lower()] = adset_name
    
    # Check if user is asking about a specific city (without hardcoding)
    city_mentioned = None
    for city_key, city_name in available_cities.items():
        # Check if the city name appears in the question
        if city_key in question_lower:
            city_mentioned = city_name
            break
    
    # If a specific city is mentioned and user is asking about it specifically
    # (not just mentioning it in passing)
    if city_mentioned and not any(word in question_lower for word in ['all', 'cities', 'compare', 'versus', 'vs', 'other']):
        # Filter for that specific city
        city_data = None
        for item in data:
            adset_name = item.get('adset_name', '').replace('Sende Tour - ', '')
            if city_mentioned.lower() in adset_name.lower():
                city_data = item
                break
        
        if city_data:
            # Format focused response for single city - Clean WhatsApp format
            city_name = city_data.get('adset_name', '').replace('Sende Tour - ', '').replace('SENDE Tour - ', '')
            
            spend = float(city_data.get('spend', 0))
            impressions = int(city_data.get('impressions', 0))
            clicks = int(city_data.get('clicks', 0))
            ctr = float(city_data.get('ctr', 0))
            
            # Calculate sales/revenue from actions
            sales = 0
            revenue = 0
            for action in city_data.get('actions', []):
                if 'purchase' in action.get('action_type', '').lower():
                    sales = int(action.get('value', 0))
            for action in city_data.get('action_values', []):
                if 'purchase' in action.get('action_type', '').lower():
                    revenue = float(action.get('value', 0))
            
            roas = (revenue / spend) if spend > 0 else 0
            
            # Clean WhatsApp format - bilingual support
            if language == "es":
                formatted = f"*Campaña {city_name.upper()}*\n\n"
                
                # Performance summary in Spanish
                if 'como' in question_lower or 'va' in question_lower or 'está' in question_lower:
                    if roas > 20:
                        formatted += "✅ ¡Excelente rendimiento!\n\n"
                    elif roas > 15:
                        formatted += "🔥 Muy buenos resultados\n\n"
                    elif roas > 10:
                        formatted += "👍 Buen progreso\n\n"
                    elif roas > 5:
                        formatted += "📈 Avanzando bien\n\n"
                    else:
                        formatted += "🎯 Construyendo momentum\n\n"
                
                # Core metrics in Spanish
                formatted += f"Alcance: {impressions:,} personas\n"
                formatted += f"Interacciones: {clicks} clics\n"
                formatted += f"Inversión: ${spend:.2f}\n"
                
                if sales > 0:
                    formatted += f"\n💰 Resultados:\n"
                    formatted += f"• {sales} tickets vendidos\n"
                    formatted += f"• ${revenue:,.2f} en ventas\n"
                    formatted += f"• {roas:.1f}x retorno"
                elif clicks > 0:
                    formatted += f"\n📊 Tasa de interacción: {ctr:.1f}%"
            else:
                formatted = f"*{city_name.upper()} Campaign Update*\n\n"
                
                # Performance summary in English
                if 'how' in question_lower or 'como' in question_lower or 'va' in question_lower:
                    if roas > 20:
                        formatted += "✅ Crushing it!\n\n"
                    elif roas > 15:
                        formatted += "🔥 Performing excellently\n\n"
                    elif roas > 10:
                        formatted += "👍 Going strong\n\n"
                    elif roas > 5:
                        formatted += "📈 Steady progress\n\n"
                    else:
                        formatted += "🎯 Building momentum\n\n"
                
                # Core metrics in English
                formatted += f"Reach: {impressions:,} people\n"
                formatted += f"Engagement: {clicks} clicks\n"
                formatted += f"Investment: ${spend:.2f}\n"
                
                if sales > 0:
                    formatted += f"\n💰 Results:\n"
                    formatted += f"• {sales} tickets sold\n"
                    formatted += f"• ${revenue:,.2f} revenue\n"
                    formatted += f"• {roas:.1f}x ROAS"
                elif clicks > 0:
                    formatted += f"\n📊 Engagement Rate: {ctr:.1f}%"
            
            return formatted
        else:
            return f"No data available for {city_mentioned}."
    
    # If asking for full report or comparison
    formatted = "*SENDÉ TOUR - All Cities Report*\n\n"
    
    # Calculate totals
    total_reach = sum(int(city.get('impressions', 0)) for city in data)
    total_clicks = sum(int(city.get('clicks', 0)) for city in data)
    total_spend = sum(float(city.get('spend', 0)) for city in data)
    total_sales = 0
    total_revenue = 0
    
    # Process each city
    city_reports = []
    for city in data:
        city_name = city.get('city', city.get('adset_name', 'Unknown')).replace('Sende Tour - ', '').replace('SENDE Tour - ', '')
        impressions = int(city.get('impressions', 0))
        clicks = int(city.get('clicks', 0))
        spend = float(city.get('spend', 0))
        ctr = float(city.get('ctr', 0))
        
        # Extract purchase data
        purchases = 0
        revenue = 0
        actions = city.get('actions', [])
        action_values = city.get('action_values', [])
        
        for action in actions:
            if 'purchase' in action.get('action_type', ''):
                purchases = int(action.get('value', 0))
                break
        
        for value in action_values:
            if value.get('action_type') == 'purchase':
                revenue = float(value.get('value', 0))
                break
        
        total_sales += purchases
        total_revenue += revenue
        
        # Calculate ROAS
        roas = (revenue / spend) if spend > 0 else 0
        
        city_report = f"""*{city_name.upper()}*
Reach: {impressions:,}
Clicks: {clicks}
Spend: ${spend:.2f}
Sales: {purchases} tickets = ${revenue:,.2f}
ROAS: {roas:.1f}x

"""
        city_reports.append((roas, city_report))
    
    # Sort by performance (ROAS)
    city_reports.sort(key=lambda x: x[0], reverse=True)
    
    # Add summary at top
    overall_roas = (total_revenue / total_spend) if total_spend > 0 else 0
    avg_ctr = (total_clicks / total_reach * 100) if total_reach > 0 else 0
    
    formatted += f"""*Campaign Summary*
Total Reach: {total_reach:,} people
Total Engagement: {total_clicks:,} clicks
Investment: ${total_spend:.2f}

💰 *Results*
Tickets Sold: {total_sales}
Revenue: ${total_revenue:,.2f}
ROAS: {overall_roas:.1f}x

---
*By City:*

"""
    
    # Add city reports
    for _, report in city_reports:
        formatted += report
    
    return formatted


# Node functions for dynamic LangGraph workflow
async def initialize_node(state: MetaCampaignState) -> Command[Literal["analyze"]]:
    """Initialize the campaign analysis"""
    logger.info("Initializing dynamic Meta campaign analysis")
    
    # Get campaign_id with fallback
    campaign_id = state.get('campaign_id') or os.getenv("DEFAULT_CAMPAIGN_ID", "120232002620350525")
    
    return Command(
        update={
            "campaign_id": campaign_id,
            "stage": "analyzing"
        },
        goto="analyze"
    )


async def analyze_node(state: MetaCampaignState) -> Command[Literal["complete"]]:
    """Unified analysis node that handles all question types"""
    logger.info("Analyzing user question and fetching data")
    
    # Set user context for security filtering
    phone_number = state.get('phone_number', os.getenv("RYAN_PHONE", "+17865551234"))
    from ..tools.meta_ads_tools import meta_sdk
    meta_sdk.set_user_context(phone_number)
    
    question = state.get('current_question', '').lower() if state.get('current_question') else ''
    messages = state.get('messages', [])
    
    # Get the actual user message
    user_message = ''
    for msg in messages:
        if hasattr(msg, 'content'):
            user_message = msg.content
            break
    
    # Combine question and message for analysis
    full_query = f"{question} {user_message}".strip()
    
    # Check for restricted queries FIRST
    restriction_msg = await check_query_restrictions(full_query)
    if restriction_msg:
        return Command(
            update={
                "answer": restriction_msg,
                "messages": [AIMessage(content=restriction_msg)]
            },
            goto="complete"
        )
    
    # Continue with normal processing
    full_query = full_query.lower()
    
    # Detect intent patterns
    detected_entities = {}
    
    # Dynamically discover available metrics from Meta SDK
    try:
        # Get available fields from the SDK
        discovery = meta_sdk_discover.invoke({
            "object_type": "campaign",
            "object_id": state.get('campaign_id')
        })
        
        available_fields = discovery.get('insights_fields', []) + discovery.get('available_fields', [])
        
        # Use AI to match user's question to available fields
        if available_fields:
            settings = get_settings()
            model = None
            if settings.openai.api_key:
                model = ChatOpenAI(
                    model=settings.openai.model,
                    temperature=0.3,
                    api_key=settings.openai.api_key
                )
            elif settings.anthropic.api_key:
                model = ChatAnthropic(
                    model=settings.anthropic.model,
                    temperature=0.3,
                    api_key=settings.anthropic.api_key
                )

            prompt = f"""
            User asked: {full_query}
            
            Available Meta SDK metrics/fields:
            {json.dumps(available_fields, indent=2)}
            
            IMPORTANT: In Meta Ads, cities/locations are represented as AdSet names, not geographic breakdowns.
            If the user asks for city-level or location data, we need to fetch AdSet insights.
            
            Identify what the user is asking about:
            - metric: list of exact field names from available fields (e.g., ['impressions', 'clicks', 'spend', 'ctr', 'purchase_roas'])
            - location: "cities" if asking about all cities/locations, or specific city name
            - time_period: detected time period (today, yesterday, last_7d, etc.)
            
            Be flexible - match 'video views' to 'video_views', 'link clicks' to 'inline_link_clicks', etc.
            """
            
            try:
                if model is not None:
                    response = await model.ainvoke([SystemMessage(content=prompt)])
                    content = response.content
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        ai_entities = json.loads(json_match.group())
                        detected_entities.update(ai_entities)
            except:
                pass
    except:
        # Fallback to basic detection if SDK discovery fails
        pass
    
    # Use AI to detect entities instead of hardcoded patterns
    if model:
        entity_prompt = f"""
        Extract entities from this query: {full_query}
        
        Look for:
        1. Location/City mentions (any city name, not from a fixed list)
        2. Time references (today, yesterday, last week, this month, specific dates, etc.)
        3. Metrics (CTR, clicks, impressions, ROAS, spend, etc.)
        4. Comparison intent (best, worst, highest, lowest, compare, etc.)
        
        Return as JSON:
        {{
            "location": "detected city or null",
            "time": "Meta API date_preset format (today, yesterday, last_7d, last_30d, etc.) or null",
            "metric": "detected metric or null",
            "comparison_type": "best/worst/compare or null"
        }}
        """
        
        try:
            entity_response = await model.ainvoke([SystemMessage(content=entity_prompt)])
            import json
            json_match = re.search(r'\{.*\}', entity_response.content, re.DOTALL)
            if json_match:
                ai_entities = json.loads(json_match.group())
                detected_entities.update(ai_entities)
        except:
            pass
        
    # Let AI determine intent instead of keyword matching
    is_comparison = detected_entities.get('comparison_type') is not None
    is_metric_question = detected_entities.get('metric') is not None
    
    logger.info(f"Question: {full_query}, Entities: {detected_entities}")
    
    try:
        campaign_id = state.get('campaign_id')
        answer = ""
        
        # First try dynamic NL-to-SDK planning for arbitrary questions with language support
        dynamic_answer = await plan_and_execute_dynamic_queries(
            question=full_query or user_message,
            campaign_id=campaign_id,
            date_hint=detected_entities.get('time'),
            language=state.get('language', 'en')
        )
        if dynamic_answer:
            return Command(
                update={
                    "answer": dynamic_answer,
                    "stage": "complete"
                },
                goto="complete"
            )

        # Otherwise, handle specific known patterns as a robust fallback
        # Handle different question types in one place
        if is_comparison and is_metric_question:
            # Handle metric comparison across cities
            logger.info("Comparing metrics across cities")
            metric = detected_entities.get('metric', 'ctr')
            
            # Fetch ad set data for all cities
            query = {
                "operation": "get_adsets_insights",
                "campaign_id": campaign_id,
                "date_preset": detected_entities.get('time') or 'today',
                "fields": [
                    'adset_name', 'impressions', 'clicks', 'spend', 'ctr', 'cpc', 'cpm',
                    'conversions', 'purchase_roas', 'actions', 'action_values'
                ],
                "level": "adset"
            }
            
            result = meta_sdk_query.invoke({"query": query})
            
            if result and isinstance(result, list):
                # Process city data
                cities_data = []
                metric_mapping = {
                    'ctr': 'ctr',
                    'clicks': 'clicks',
                    'impressions': 'impressions',
                    'spend': 'spend',
                    'cpc': 'cpc',
                    'roas': 'purchase_roas'
                }
                
                actual_metric = metric_mapping.get(metric.lower(), metric.lower())
                
                for adset in result:
                    if isinstance(adset, dict):
                        city_name = adset.get('adset_name', 'Unknown').replace('Sende Tour - ', '')
                        metric_value = float(adset.get(actual_metric, 0))
                        
                        # Special handling for ROAS
                        if actual_metric == 'purchase_roas':
                            action_values = adset.get('action_values', [])
                            revenue = 0
                            for value in action_values:
                                if 'purchase' in value.get('action_type', '').lower():
                                    revenue = float(value.get('value', 0))
                                    break
                            spend = float(adset.get('spend', 0))
                            metric_value = revenue / spend if spend > 0 else 0
                        
                        cities_data.append({
                            'city': city_name,
                            'metric_value': metric_value
                        })
                
                # Sort and create answer
                cities_data.sort(key=lambda x: x['metric_value'], reverse=True)
                
                if 'best' in full_query or 'highest' in full_query:
                    best = cities_data[0] if cities_data else None
                    if best:
                        unit = '%' if actual_metric == 'ctr' else ('x' if actual_metric == 'purchase_roas' else '')
                        if state.get('language') == 'es':
                            answer = f"{best['city']} tiene el mejor {metric.upper()} con {best['metric_value']:.2f}{unit}. "
                            others = [f"{c['city']} ({c['metric_value']:.2f}{unit})" for c in cities_data[1:4]]
                            if others:
                                answer += f"Las otras ciudades son: {', '.join(others)}."
                        else:
                            answer = f"{best['city']} has the best {metric.upper()} at {best['metric_value']:.2f}{unit}. "
                            others = [f"{c['city']} ({c['metric_value']:.2f}{unit})" for c in cities_data[1:4]]
                            if others:
                                answer += f"The other cities are: {', '.join(others)}."
                elif 'worst' in full_query or 'lowest' in full_query:
                    worst = cities_data[-1] if cities_data else None
                    if worst:
                        unit = '%' if actual_metric == 'ctr' else ('x' if actual_metric == 'purchase_roas' else '')
                        if state.get('language') == 'es':
                            answer = f"{worst['city']} tiene el {metric.upper()} más bajo con {worst['metric_value']:.2f}{unit}. "
                            better = [f"{c['city']} ({c['metric_value']:.2f}{unit})" for c in cities_data[:3]]
                            if better:
                                answer += f"Ciudades con mejor rendimiento: {', '.join(better)}."
                        else:
                            answer = f"{worst['city']} has the lowest {metric.upper()} at {worst['metric_value']:.2f}{unit}. "
                            better = [f"{c['city']} ({c['metric_value']:.2f}{unit})" for c in cities_data[:3]]
                            if better:
                                answer += f"Better performing cities: {', '.join(better)}."
                else:
                    unit = '%' if actual_metric == 'ctr' else ('x' if actual_metric == 'purchase_roas' else '')
                    if state.get('language') == 'es':
                        answer = f"Aquí está el desglose de {metric.upper()} por ciudad: "
                        city_list = [f"{c['city']}: {c['metric_value']:.2f}{unit}" for c in cities_data[:5]]
                        answer += ", ".join(city_list)
                    else:
                        answer = f"Here's the {metric.upper()} breakdown by city: "
                        city_list = [f"{c['city']}: {c['metric_value']:.2f}{unit}" for c in cities_data[:5]]
                        answer += ", ".join(city_list)
            else:
                if state.get('language') == 'es':
                    answer = "No pude obtener los datos de comparación. Por favor intenta de nuevo."
                else:
                    answer = "I couldn't fetch the comparison data. Please try again."
                
        else:
            # Default: Quick overview of campaign performance
            logger.info("Providing quick campaign overview")
            
            # Check if asking for maximum/all-time data
            time_period = detected_entities.get('time') or 'today'
            if any(word in full_query for word in ['maximum', 'max', 'all time', 'lifetime', 'total', 'overall']):
                time_period = 'maximum'
            
            query = {
                "operation": "get_adsets_insights",
                "campaign_id": campaign_id,
                "date_preset": time_period,
                "fields": [
                    'adset_name', 'impressions', 'clicks', 'spend', 'ctr', 
                    'conversions', 'purchase_roas', 'actions', 'action_values'
                ],
                "level": "adset"
            }
            
            result = meta_sdk_query.invoke({"query": query})
            
            # Aggregate totals
            totals = {
                'spend': 0,
                'impressions': 0,
                'clicks': 0,
                'revenue': 0,
                'cities': []
            }
            
            for adset in result if isinstance(result, list) else []:
                if isinstance(adset, dict):
                    city = adset.get('adset_name', 'Unknown').replace('Sende Tour - ', '')
                    spend = float(adset.get('spend', 0))
                    impressions = int(adset.get('impressions', 0))
                    clicks = int(adset.get('clicks', 0))
                    
                    totals['spend'] += spend
                    totals['impressions'] += impressions
                    totals['clicks'] += clicks
                    totals['cities'].append(city)
                    
                    # Get revenue
                    action_values = adset.get('action_values', [])
                    for value in action_values:
                        if 'purchase' in value.get('action_type', '').lower():
                            totals['revenue'] += float(value.get('value', 0))
            
            # Calculate overall metrics
            overall_ctr = (totals['clicks'] / totals['impressions'] * 100) if totals['impressions'] > 0 else 0
            overall_roas = (totals['revenue'] / totals['spend']) if totals['spend'] > 0 else 0
            
            # Check if user wants detailed report - bilingual
            spanish_report_words = ['reporte', 'desglose', 'detalles', 'cada ciudad', 'todas']
            english_report_words = ['report', 'breakdown', 'details', 'each city', 'all']
            report_words = spanish_report_words if state.get('language') == 'es' else english_report_words
            
            if any(word in full_query for word in report_words):
                # Detailed city-by-city breakdown
                answer = f"📊 SENDÉ TOUR CAMPAIGN REPORT ({time_period.upper()})\n\n"
                answer += f"OVERVIEW:\n"
                answer += f"• Total Spend: ${totals['spend']:.2f}\n"
                answer += f"• Total Impressions: {totals['impressions']:,}\n"
                answer += f"• Total Clicks: {totals['clicks']:,}\n"
                answer += f"• Overall CTR: {overall_ctr:.2f}%\n"
                if overall_roas > 0:
                    answer += f"• Overall ROAS: {overall_roas:.2f}x\n"
                
                answer += f"\nCITY BREAKDOWN:\n"
                for adset in result if isinstance(result, list) else []:
                    if isinstance(adset, dict):
                        city = adset.get('adset_name', 'Unknown').replace('Sende Tour - ', '')
                        spend = float(adset.get('spend', 0))
                        impressions = int(adset.get('impressions', 0))
                        clicks = int(adset.get('clicks', 0))
                        ctr = float(adset.get('ctr', 0))
                        
                        answer += f"\n📍 {city}:\n"
                        answer += f"  • Spend: ${spend:.2f}\n"
                        answer += f"  • Impressions: {impressions:,}\n"
                        answer += f"  • Clicks: {clicks}\n"
                        answer += f"  • CTR: {ctr:.2f}%\n"
            else:
                # Quick summary - bilingual
                if state.get('language') == 'es':
                    answer = f"Tu campaña de la Gira SENDÉ está activa en {len(totals['cities'])} ciudades "
                    answer += f"({', '.join(totals['cities'][:3])}{'...' if len(totals['cities']) > 3 else ''}). "
                    answer += f"Rendimiento {time_period}: ${totals['spend']:.2f} gastados, "
                    answer += f"{totals['impressions']:,} impresiones, {totals['clicks']} clics "
                    answer += f"({overall_ctr:.2f}% CTR)"
                    if overall_roas > 0:
                        answer += f", {overall_roas:.2f}x ROAS"
                    answer += "."
                else:
                    answer = f"Your SENDÉ Tour campaign is running in {len(totals['cities'])} cities "
                    answer += f"({', '.join(totals['cities'][:3])}{'...' if len(totals['cities']) > 3 else ''}). "
                    answer += f"{time_period.title()} performance: ${totals['spend']:.2f} spent, "
                    answer += f"{totals['impressions']:,} impressions, {totals['clicks']} clicks "
                    answer += f"({overall_ctr:.2f}% CTR)"
                    if overall_roas > 0:
                        answer += f", {overall_roas:.2f}x ROAS"
                    answer += "."
        
        return Command(
            update={
                "answer": answer,
                "stage": "complete"
            },
            goto="complete"
        )
        
    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        error_msg = (f"Encontré un error analizando tu campaña: {str(e)}. Por favor intenta de nuevo." 
                    if state.get('language') == 'es' 
                    else f"I encountered an error analyzing your campaign: {str(e)}. Please try again.")
        return Command(
            update={
                "answer": error_msg,
                "stage": "complete"
            },
            goto="complete"
        )

# REMOVED - Consolidated into analyze_node
# async def discover_data_node(state: MetaCampaignState) -> Command[Literal["fetch_dynamic_data", "handle_error"]]:
    """Discover what data is available for the campaign"""
    logger.info("Discovering available data via Meta SDK")
    
    try:
        campaign_id = state.get('campaign_id')
        
        # Discover available fields and capabilities
        discovery = meta_sdk_discover.invoke({
            "object_type": "campaign",
            "object_id": campaign_id
        })
        
        logger.info(f"Discovered capabilities: {discovery}")
        
        return Command(
            update={
                "stage": "fetching"
            },
            goto="fetch_dynamic_data"
        )
        
    except Exception as e:
        logger.error(f"Error in discovery: {e}")
        return Command(
            update={
                "error": str(e),
                "stage": "error"
            },
            goto="handle_error"
        )


# async def fetch_dynamic_data_node(state: MetaCampaignState) -> Command[Literal["analyze_intelligently", "handle_error"]]:
    """Fetch data dynamically using the Meta SDK"""
    logger.info("Fetching data dynamically via Meta SDK")
    
    try:
        campaign_id = state.get('campaign_id')
        date_range = state.get('date_range', 'today')
        
        # Prepare batch queries - ALWAYS USE ADSET LEVEL DATA
        queries = [
            # Get campaign details
            {
                "operation": "custom_query",
                "object_type": "campaign",
                "object_id": campaign_id,
                "fields": [
                    "name", "objective", "status", "effective_status",
                    "daily_budget", "lifetime_budget", "spend_cap",
                    "created_time", "start_time", "stop_time",
                    "bid_strategy"
                ]
            },
            # Get adsets under this campaign with insights
            {
                "operation": "custom_query",
                "object_type": "campaign",
                "object_id": campaign_id,
                "edge": "adsets",
                "fields": [
                    "name", "status", "effective_status", "daily_budget",
                    "bid_strategy", "optimization_goal", "targeting",
                    "insights{impressions,clicks,ctr,cpc,cpm,spend,reach,frequency,conversions,purchase_roas,actions,action_values}"
                ]
            },
            # Get aggregated insights from all adsets
            {
                "operation": "get_adsets_insights",
                "campaign_id": campaign_id,
                "date_preset": date_range if date_range != 'lifetime' else 'maximum',
                "fields": [
                    "adset_name", "impressions", "clicks", "ctr", "cpc", "cpm",
                    "spend", "reach", "frequency", "conversions", "purchase_roas",
                    "actions", "action_values", "cost_per_action_type",
                    "video_p25_watched_actions", "video_p50_watched_actions",
                    "video_p75_watched_actions", "video_p100_watched_actions",
                    "inline_link_clicks", "inline_link_click_ctr",
                    "website_purchase_roas"
                ],
                "level": "adset",
                "time_increment": "all_days"
            },
            # Get ads under this campaign
            {
                "operation": "custom_query",
                "object_type": "campaign",
                "object_id": campaign_id,
                "edge": "ads",
                "fields": [
                    "name", "status", "effective_status", "creative"
                ]
            }
        ]
        
        # Add demographic insights if comprehensive analysis
        if state.get('analysis_type') == 'comprehensive':
            # Note: Meta API doesn't allow multiple breakdowns in one call
            # We'll get age/gender breakdown first
            queries.append({
                "operation": "get_campaign_insights",
                "campaign_id": campaign_id,
                "date_preset": date_range,
                "fields": ["impressions", "clicks", "spend", "conversions"],
                "breakdowns": ["age", "gender"]
            })
        
        # Execute all queries in batch
        results = meta_sdk_batch_query.invoke({"queries": queries})
        
        # Process results - ADSET DATA IS PRIMARY
        campaign_data = results[0] if len(results) > 0 else {}
        adsets_data = results[1] if len(results) > 1 else []
        adsets_insights = results[2] if len(results) > 2 else []
        ads_data = results[3] if len(results) > 3 else []
        demographics_data = results[4] if len(results) > 4 else {}
        
        # Aggregate adset insights to get total campaign metrics
        total_metrics = {
            'impressions': 0,
            'clicks': 0,
            'spend': 0,
            'reach': 0,
            'conversions': 0,
            'revenue': 0
        }
        
        for adset in adsets_insights:
            total_metrics['impressions'] += int(adset.get('impressions', 0))
            total_metrics['clicks'] += int(adset.get('clicks', 0))
            total_metrics['spend'] += float(adset.get('spend', 0))
            total_metrics['reach'] += int(adset.get('reach', 0))
            
            # Get conversions and revenue from actions
            actions = adset.get('actions', [])
            for action in actions:
                if 'purchase' in action.get('action_type', '').lower():
                    total_metrics['conversions'] += int(action.get('value', 0))
            
            action_values = adset.get('action_values', [])
            for value in action_values:
                if 'purchase' in value.get('action_type', '').lower():
                    total_metrics['revenue'] += float(value.get('value', 0))
        
        # Calculate aggregated metrics
        if total_metrics['impressions'] > 0:
            total_metrics['ctr'] = (total_metrics['clicks'] / total_metrics['impressions']) * 100
        if total_metrics['clicks'] > 0:
            total_metrics['cpc'] = total_metrics['spend'] / total_metrics['clicks']
        if total_metrics['spend'] > 0:
            total_metrics['roas'] = total_metrics['revenue'] / total_metrics['spend']
        
        # Use adset insights as primary data
        insights_data = [{
            **total_metrics,
            'adsets': adsets_insights,
            'campaign_name': campaign_data.get('name', 'Unknown')
        }]
        
        logger.info(f"Fetched campaign: {campaign_data.get('name', 'Unknown')}")
        logger.info(f"Fetched {len(adsets_insights)} ad sets with insights")
        logger.info(f"Total spend from adsets: ${total_metrics['spend']:.2f}")
        logger.info(f"Total revenue from adsets: ${total_metrics['revenue']:.2f}")
        
        return Command(
            update={
                "campaign_data": campaign_data,
                "insights_data": insights_data,
                "adsets_data": adsets_data,
                "ads_data": ads_data,
                "demographics_data": demographics_data,
                "stage": "analyzing"
            },
            goto="analyze_intelligently"
        )
        
    except Exception as e:
        logger.error(f"Error fetching dynamic data: {e}")
        return Command(
            update={
                "error": str(e),
                "stage": "error"
            },
            goto="handle_error"
        )


# async def analyze_intelligently_node(state: MetaCampaignState) -> Command[Literal["fetch_additional_data", "generate_report"]]:
    """Use AI to intelligently analyze data and determine if more is needed"""
    logger.info("Analyzing data with AI intelligence")
    
    try:
        analyzer = DynamicMetaCampaignAnalyzer(get_settings())
        analysis = await analyzer.analyze_with_intelligence(state)
        
        # Calculate campaign health score
        if state.get('insights_data'):
            metrics = {
                'ctr': state.get('insights_data', [{}])[0].get('ctr', 0),
                'cpc': state.get('insights_data', [{}])[0].get('cpc', 0),
                'roas': state.get('roas_data', {}).get('roas', 0) if state.get('roas_data') else 0,
                'spend': state.get('insights_data', [{}])[0].get('spend', 0),
                'conversions': state.get('insights_data', [{}])[0].get('conversions', 0)
            }
            health_score = await analyze_campaign_health.ainvoke({"campaign_metrics": metrics})
            
            # Detect anomalies if we have historical data
            if len(state.get('insights_data', [])) > 1:
                anomalies = await detect_performance_anomalies.ainvoke({
                    "current_metrics": metrics,
                    "historical_data": state.get('insights_data', [])
                })
                if anomalies:
                    analysis['insights'].append(f"⚠️ Detected {len(anomalies)} performance anomalies")
            
            # Get optimization plan
            optimization_plan = await generate_optimization_plan.ainvoke({
                "campaign_data": state.get('campaign_data', {}),
                "performance_data": metrics
            })
            
            # Get competitive benchmarks
            benchmarks = await get_competitive_benchmarks.ainvoke({
                "industry": "events",
                "region": "US"
            })
            
            # Add intelligence insights
            analysis['insights'].append(f"Campaign Health: {health_score.get('health', 'Unknown')} (Score: {health_score.get('score', 0)}/100)")
            analysis['insights'].extend(health_score.get('factors', []))
            
            # Add benchmark comparisons
            if benchmarks:
                ctr_val = float(metrics.get('ctr', 0)) if metrics.get('ctr') else 0
                cpc_val = float(metrics.get('cpc', 999)) if metrics.get('cpc') else 999
                if ctr_val > benchmarks.get('avg_ctr', 1.5):
                    analysis['insights'].append(f"✅ CTR {ctr_val:.2f}% beats industry avg {benchmarks['avg_ctr']:.2f}%")
                if cpc_val < benchmarks.get('avg_cpc', 1.0):
                    analysis['insights'].append(f"✅ CPC ${cpc_val:.2f} better than industry avg ${benchmarks['avg_cpc']:.2f}")
            
            # Add optimization recommendations
            for opt in optimization_plan[:3]:
                analysis['recommendations'].append(f"{opt['action']}: {opt['reason']}")
        
        # Check if AI wants to fetch additional data
        if analysis.get('needs_more_data') and analysis.get('additional_queries'):
            return Command(
                update={
                    "custom_data": {"additional_queries": analysis['additional_queries']},
                    "insights": analysis.get('insights', []),
                    "recommendations": analysis.get('recommendations', []),
                    "stage": "fetching_additional"
                },
                goto="fetch_additional_data"
            )
        else:
            # Proceed to report generation
            return Command(
                update={
                    "insights": analysis.get('insights', []),
                    "recommendations": analysis.get('recommendations', []),
                    "stage": "reporting"
                },
                goto="generate_report"
            )
        
    except Exception as e:
        logger.error(f"Error in intelligent analysis: {e}")
        return Command(
            update={
                "error": str(e),
                "stage": "reporting"
            },
            goto="generate_report"
        )


# async def fetch_additional_data_node(state: MetaCampaignState) -> Command[Literal["generate_report"]]:
    """Fetch additional data as requested by AI"""
    logger.info("Fetching additional data requested by AI")
    
    try:
        additional_queries = state.get('custom_data', {}).get('additional_queries', [])
        
        if additional_queries:
            results = meta_sdk_batch_query.invoke({"queries": additional_queries})
            
            # Store additional data
            return Command(
                update={
                    "custom_data": {"additional_results": results},
                    "stage": "reporting"
                },
                goto="generate_report"
            )
        else:
            return Command(
                update={"stage": "reporting"},
                goto="generate_report"
            )
        
    except Exception as e:
        logger.error(f"Error fetching additional data: {e}")
        return Command(
            update={"stage": "reporting"},
            goto="generate_report"
        )


# async def quick_answer_node(state: MetaCampaignState) -> Command[Literal["complete"]]:
    """Provide quick, conversational answers - ALWAYS USE ADSET DATA"""
    logger.info("Generating quick answer from adset data")
    
    try:
        campaign_id = state.get('campaign_id')
        entities = state.get('detected_entities', {})
        question = state.get('current_question', '')
        
        # ALWAYS fetch adset level data - no campaign level queries
        time_period = entities.get('time_period') or 'today'
        if time_period == 'lifetime':
            time_period = 'maximum'
            
        query = {
            "operation": "get_adsets_insights",
            "campaign_id": campaign_id,
            "date_preset": time_period,
            "fields": [
                'adset_name', 'impressions', 'clicks', 'spend', 'ctr', 'cpc',
                'reach', 'frequency', 'conversions', 'purchase_roas',
                'actions', 'action_values', 'inline_link_clicks'
            ],
            "level": "adset"
        }
        
        result = meta_sdk_query.invoke({"query": query})
        
        # Aggregate data from all ad sets
        totals = {
            'spend': 0,
            'impressions': 0,
            'clicks': 0,
            'reach': 0,
            'conversions': 0,
            'revenue': 0,
            'adsets': []
        }
        
        for adset in result if isinstance(result, list) else [result]:
            if isinstance(adset, dict):
                adset_name = adset.get('adset_name', 'Unknown')
                spend = float(adset.get('spend', 0))
                impressions = int(adset.get('impressions', 0))
                clicks = int(adset.get('clicks', 0))
                
                if spend > 0:  # Only count adsets with spend
                    totals['spend'] += spend
                    totals['impressions'] += impressions
                    totals['clicks'] += clicks
                    totals['reach'] += int(adset.get('reach', 0))
                    
                    # Get conversions from actions
                    actions = adset.get('actions', [])
                    for action in actions if isinstance(actions, list) else []:
                        if 'purchase' in str(action.get('action_type', '')).lower():
                            totals['conversions'] += int(action.get('value', 0))
                    
                    # Get revenue from action_values
                    action_values = adset.get('action_values', [])
                    for value in action_values if isinstance(action_values, list) else []:
                        if 'purchase' in str(value.get('action_type', '')).lower():
                            totals['revenue'] += float(value.get('value', 0))
                    
                    # Get ROAS directly if available
                    if adset.get('purchase_roas'):
                        roas_data = adset.get('purchase_roas')
                        if isinstance(roas_data, list) and roas_data:
                            roas_value = float(roas_data[0].get('value', 0))
                        else:
                            roas_value = 0
                    else:
                        roas_value = 0
                    
                    totals['adsets'].append({
                        'name': adset_name.replace('Sende Tour - ', ''),  # Shorten name
                        'spend': spend,
                        'impressions': impressions,
                        'clicks': clicks,
                        'ctr': float(adset.get('ctr', 0)),
                        'roas': roas_value
                    })
        
        # Calculate aggregate metrics
        if totals['impressions'] > 0:
            totals['ctr'] = (totals['clicks'] / totals['impressions']) * 100
        if totals['clicks'] > 0:
            totals['cpc'] = totals['spend'] / totals['clicks']
        if totals['spend'] > 0:
            totals['overall_roas'] = totals['revenue'] / totals['spend'] if totals['revenue'] > 0 else 0
        
        # Generate conversational response
        settings = get_settings()
        model = ChatOpenAI(
            model=settings.openai.model,
            temperature=0.7,
            api_key=settings.openai.api_key
        ) if settings.openai.api_key else ChatAnthropic(
            model=settings.anthropic.model,
            temperature=0.7,
            api_key=settings.anthropic.api_key
        )
        
        # Create summary for AI
        summary = f"""
        SENDÉ Tour Campaign Performance (Today):
        - Total Spend: ${totals['spend']:.2f}
        - Total Impressions: {totals['impressions']:,}
        - Total Clicks: {totals['clicks']:,}
        - Overall CTR: {totals.get('ctr', 0):.2f}%
        - Active Cities: {len(totals['adsets'])} ({', '.join([a['name'] for a in totals['adsets']])})
        
        City Breakdown:
        {chr(10).join([f"- {a['name']}: ${a['spend']:.2f} spent, {a['impressions']:,} impressions, {a['ctr']:.2f}% CTR" + (f", {a['roas']:.1f}x ROAS" if a['roas'] > 0 else "") for a in totals['adsets']])}
        """
        
        prompt = f"""
        User asked: {question or 'How is my SENDÉ tour campaign doing?'}
        
        {summary}
        
        Give a comprehensive but concise answer (3-4 sentences). Include total spend, performance across all 5 cities, and key metrics.
        Mention that the campaign is running in Brooklyn, Miami, Houston, Chicago, and LA.
        If ROAS data is available, highlight it as it's a key success metric.
        """
        
        response = await model.ainvoke([SystemMessage(content=prompt)])
        
        return Command(
            update={
                "answer": response.content,
                "stage": "complete"
            },
            goto="complete"
        )
        
    except Exception as e:
        logger.error(f"Error in quick answer: {e}")
        return Command(
            update={
                "answer": f"I encountered an issue getting that data: {str(e)}. Try asking for a 'full report' for comprehensive analysis.",
                "stage": "complete"
            },
            goto="complete"
        )

# async def location_analysis_node(state: MetaCampaignState) -> Command[Literal["complete"]]:
    """Analyze performance for specific locations - USING ADSET DATA"""
    logger.info("Analyzing location performance from adset data")
    
    try:
        campaign_id = state.get('campaign_id')
        entities = state.get('detected_entities', {})
        location = entities.get('location', '')
        
        # Fetch adset data (adsets are named by city)
        time_period = entities.get('time', 'last_7d')
        if time_period == 'lifetime':
            time_period = 'maximum'
            
        query = {
            "operation": "get_adsets_insights",
            "campaign_id": campaign_id,
            "date_preset": time_period,
            "fields": [
                'adset_name', 'impressions', 'clicks', 'spend', 'conversions', 
                'ctr', 'cpc', 'actions', 'action_values'
            ],
            "level": "adset"
        }
        
        result = meta_sdk_query.invoke({"query": query})
        
        # Filter for specific location if found
        location_data = None
        if isinstance(result, list):
            for item in result:
                if location.lower() in str(item).lower():
                    location_data = item
                    break
        
        # Generate location-specific response
        settings = get_settings()
        model = ChatOpenAI(
            model=settings.openai.model,
            temperature=0.7,
            api_key=settings.openai.api_key
        ) if settings.openai.api_key else ChatAnthropic(
            model=settings.anthropic.model,
            temperature=0.7,
            api_key=settings.anthropic.api_key
        )
        
        prompt = f"""
        User asked about {location} performance.
        
        Location data: {json.dumps(location_data if location_data else result, indent=2)[:1500]}
        
        Provide a conversational answer about {location}'s performance. Include key metrics.
        If we don't have specific {location} data, explain what geographic data we do have.
        Keep it to 3-4 sentences.
        """
        
        response = await model.ainvoke([SystemMessage(content=prompt)])
        
        return Command(
            update={
                "answer": response.content,
                "stage": "complete"
            },
            goto="complete"
        )
        
    except Exception as e:
        logger.error(f"Error in location analysis: {e}")
        return Command(
            update={
                "answer": f"I couldn't get location data right now. The campaign is running in multiple locations. For detailed geographic breakdown, try asking for a 'full report'.",
                "stage": "complete"
            },
            goto="complete"
        )

# async def metric_analysis_node(state: MetaCampaignState) -> Command[Literal["complete"]]:
    """Analyze specific metrics in detail - handles both trends and city comparisons"""
    logger.info("Analyzing specific metrics")
    
    try:
        campaign_id = state.get('campaign_id')
        entities = state.get('detected_entities', {})
        metric = entities.get('metric', 'ctr')
        question = state.get('current_question', '')
        
        # Check if asking about best/worst/top performing across cities
        is_comparison = any(word in question.lower() for word in ['best', 'worst', 'top', 'highest', 'lowest', 'which', 'city', 'cities'])
        
        if is_comparison:
            # Get adset level data for city comparison
            logger.info(f"Comparing {metric} across cities")
            
            query = {
                "operation": "get_adsets_insights",
                "campaign_id": campaign_id,
                "date_preset": entities.get('time_period') or 'today',
                "fields": [
                    'adset_name', 'impressions', 'clicks', 'spend', 'ctr', 'cpc', 'cpm',
                    'conversions', 'purchase_roas', 'actions', 'action_values', 'inline_link_clicks'
                ],
                "level": "adset"
            }
            
            result = meta_sdk_query.invoke({"query": query})
            
            if not result or not isinstance(result, list):
                logger.warning("No adset data returned")
                result = []
            
            # Process city data
            cities_data = []
            metric_field = metric.lower()
            
            # Map common metric names to actual field names
            metric_mapping = {
                'ctr': 'ctr',
                'click through rate': 'ctr',
                'clicks': 'clicks',
                'impressions': 'impressions',
                'spend': 'spend',
                'cost': 'spend',
                'cpc': 'cpc',
                'cost per click': 'cpc',
                'cpm': 'cpm',
                'roas': 'purchase_roas',
                'return on ad spend': 'purchase_roas'
            }
            
            actual_metric = metric_mapping.get(metric_field, metric_field)
            
            for adset in result:
                if isinstance(adset, dict):
                    city_name = adset.get('adset_name', 'Unknown').replace('Sende Tour - ', '')
                    
                    # Get metric value
                    metric_value = 0
                    if actual_metric == 'purchase_roas':
                        # Calculate ROAS from action_values
                        action_values = adset.get('action_values', [])
                        revenue = 0
                        for value in action_values:
                            if 'purchase' in value.get('action_type', '').lower():
                                revenue = float(value.get('value', 0))
                                break
                        spend = float(adset.get('spend', 0))
                        metric_value = revenue / spend if spend > 0 else 0
                    else:
                        metric_value = float(adset.get(actual_metric, 0))
                    
                    cities_data.append({
                        'city': city_name,
                        'metric_value': metric_value,
                        'spend': float(adset.get('spend', 0)),
                        'impressions': int(adset.get('impressions', 0)),
                        'clicks': int(adset.get('clicks', 0))
                    })
            
            # Sort cities by metric value
            cities_data.sort(key=lambda x: x['metric_value'], reverse=True)
            
            # Generate comparison response
            settings = get_settings()
            model = ChatOpenAI(
                model=settings.openai.model,
                temperature=0.7,
                api_key=settings.openai.api_key
            ) if settings.openai.api_key else ChatAnthropic(
                model=settings.anthropic.model,
                temperature=0.7,
                api_key=settings.anthropic.api_key
            )
            
            # Create response based on question
            if 'best' in question.lower() or 'highest' in question.lower() or 'top' in question.lower():
                best_city = cities_data[0] if cities_data else None
                if best_city:
                    unit = '%' if actual_metric in ['ctr'] else ('x' if actual_metric == 'purchase_roas' else '')
                    answer = f"{best_city['city']} has the best {metric.upper()} at {best_city['metric_value']:.2f}{unit}. "
                    other_cities = []
                    for c in cities_data[1:4]:
                        other_cities.append(f"{c['city']} ({c['metric_value']:.2f}{unit})")
                    if other_cities:
                        answer += f"The other cities are: {', '.join(other_cities)}."
                else:
                    answer = "I couldn't find enough data to compare cities. Try asking for a full report."
            elif 'worst' in question.lower() or 'lowest' in question.lower():
                worst_city = cities_data[-1] if cities_data else None
                if worst_city:
                    unit = '%' if actual_metric in ['ctr'] else ('x' if actual_metric == 'purchase_roas' else '')
                    answer = f"{worst_city['city']} has the lowest {metric.upper()} at {worst_city['metric_value']:.2f}{unit}. "
                    better_cities = []
                    for c in cities_data[:3]:
                        better_cities.append(f"{c['city']} ({c['metric_value']:.2f}{unit})")
                    if better_cities:
                        answer += f"Better performing cities: {', '.join(better_cities)}."
                else:
                    answer = "I couldn't find enough data to compare cities. Try asking for a full report."
            else:
                # General comparison
                if cities_data:
                    unit = '%' if actual_metric in ['ctr'] else ('x' if actual_metric == 'purchase_roas' else '')
                    answer = f"Here's the {metric.upper()} breakdown by city: "
                    city_list = []
                    for c in cities_data[:5]:
                        city_list.append(f"{c['city']}: {c['metric_value']:.2f}{unit}")
                    answer += ", ".join(city_list)
                else:
                    answer = "I couldn't find enough data to compare cities. Try asking for a full report."
            
            return Command(
                update={
                    "answer": answer,
                    "stage": "complete"
                },
                goto="complete"
            )
            
        else:
            # Original trend analysis code for non-comparison queries
            query = {
                "operation": "get_campaign_insights",
                "campaign_id": campaign_id,
                "date_preset": entities.get('time_period') or entities.get('time') or 'last_7d',
                "fields": [metric, 'impressions', 'spend'],
                "time_increment": "1"
            }
            
            result = meta_sdk_query.invoke({"query": query})
            
            # Calculate trend
            trend = "stable"
            if isinstance(result, list) and len(result) > 1:
                first_val = float(result[0].get(metric, 0))
                last_val = float(result[-1].get(metric, 0))
                if last_val > first_val * 1.1:
                    trend = "improving"
                elif last_val < first_val * 0.9:
                    trend = "declining"
            
            # Generate metric-focused response
            settings = get_settings()
            model = ChatOpenAI(
                model=settings.openai.model,
                temperature=0.7,
                api_key=settings.openai.api_key
            ) if settings.openai.api_key else ChatAnthropic(
                model=settings.anthropic.model,
                temperature=0.7,
                api_key=settings.anthropic.api_key
            )
            
            prompt = f"""
            User asked about {metric.upper()}.
            
            Metric data: {json.dumps(result, indent=2)[:1500]}
            Trend: {trend}
            
            Explain the {metric.replace('_', ' ').upper()} performance conversationally. Include:
            - Current value
            - Trend (improving/declining/stable)
            - Brief context of what this means
            Keep it to 2-3 sentences.
            """
            
            response = await model.ainvoke([SystemMessage(content=prompt)])
            
            return Command(
                update={
                    "answer": response.content,
                    "stage": "complete"
                },
                goto="complete"
            )
        
    except Exception as e:
        logger.error(f"Error in metric analysis: {e}")
        return Command(
            update={
                "answer": f"I had trouble analyzing that metric. Let me know if you'd like a full performance report instead.",
                "stage": "complete"
            },
            goto="complete"
        )

# async def comparison_analysis_node(state: MetaCampaignState) -> Command[Literal["complete"]]:
    """Compare performance across time periods or segments"""
    logger.info("Running comparison analysis")
    
    try:
        campaign_id = state.get('campaign_id')
        
        # Get this week vs last week data
        this_week_query = {
            "operation": "get_campaign_insights",
            "campaign_id": campaign_id,
            "date_preset": "last_7d",
            "fields": ['impressions', 'clicks', 'spend', 'conversions', 'ctr', 'cpc', 'purchase_roas']
        }
        
        last_week_query = {
            "operation": "get_campaign_insights",
            "campaign_id": campaign_id,
            "date_preset": "last_14d",
            "fields": ['impressions', 'clicks', 'spend', 'conversions', 'ctr', 'cpc', 'purchase_roas']
        }
        
        results = meta_sdk_batch_query.invoke({"queries": [this_week_query, last_week_query]})
        
        # Generate comparison response
        settings = get_settings()
        model = ChatOpenAI(
            model=settings.openai.model,
            temperature=0.7,
            api_key=settings.openai.api_key
        ) if settings.openai.api_key else ChatAnthropic(
            model=settings.anthropic.model,
            temperature=0.7,
            api_key=settings.anthropic.api_key
        )
        
        prompt = f"""
        User wants a comparison.
        
        This week: {json.dumps(results[0] if len(results) > 0 else {}, indent=2)[:1000]}
        Last 2 weeks: {json.dumps(results[1] if len(results) > 1 else {}, indent=2)[:1000]}
        
        Provide a brief comparison highlighting:
        - Key changes (improving/declining)
        - Most significant metric changes
        - Quick recommendation if needed
        Keep it conversational, 3-4 sentences max.
        """
        
        response = await model.ainvoke([SystemMessage(content=prompt)])
        
        return Command(
            update={
                "answer": response.content,
                "stage": "complete"
            },
            goto="complete"
        )
        
    except Exception as e:
        logger.error(f"Error in comparison analysis: {e}")
        return Command(
            update={
                "answer": "I couldn't complete the comparison right now. Try asking for specific metrics or a full report for detailed analysis.",
                "stage": "complete"
            },
            goto="complete"
        )

# GHL operations removed - handled by separate GHL agent via supervisor pattern

# async def generate_report_node(state: MetaCampaignState) -> Command[Literal["answer_question", "complete"]]:
    """Generate comprehensive report ONLY when explicitly requested"""
    logger.info("Generating full campaign report")
    
    campaign = state.get('campaign_data', {})
    insights = state.get('insights_data', [])
    adsets = state.get('adsets_data', [])
    ads = state.get('ads_data', [])
    
    # Calculate totals from insights
    total_impressions = sum(int(day.get('impressions', 0)) for day in insights if isinstance(day, dict))
    total_clicks = sum(int(day.get('clicks', 0)) for day in insights if isinstance(day, dict))
    total_spend = sum(float(day.get('spend', 0)) for day in insights if isinstance(day, dict))
    total_reach = max((int(day.get('reach', 0)) for day in insights if isinstance(day, dict)), default=0)
    
    # Calculate ROAS
    total_revenue = 0
    total_conversions = 0
    for day in insights:
        if isinstance(day, dict):
            # Check for purchase actions
            actions = day.get('actions', [])
            for action in actions if isinstance(actions, list) else []:
                if 'purchase' in str(action.get('action_type', '')).lower():
                    total_conversions += int(action.get('value', 0))
            
            # Check for action values (revenue)
            action_values = day.get('action_values', [])
            for value in action_values if isinstance(action_values, list) else []:
                if 'purchase' in str(value.get('action_type', '')).lower():
                    total_revenue += float(value.get('value', 0))
    
    roas = (total_revenue / total_spend) if total_spend > 0 else 0
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
    avg_cpm = (total_spend / total_impressions * 1000) if total_impressions > 0 else 0
    
    report = f"""
META ADS CAMPAIGN REPORT (Dynamic SDK)
========================================
Campaign: {campaign.get('name', 'Unknown')}
Campaign ID: {state.get('campaign_id', 'Unknown')}
Status: {campaign.get('effective_status', 'Unknown')}
Objective: {campaign.get('objective', 'Unknown')}
Date Range: {state.get('date_range', 'last_30d')}
========================================

PERFORMANCE METRICS:
• Impressions: {total_impressions:,}
• Clicks: {total_clicks:,}
• Reach: {total_reach:,}
• Total Spend: ${total_spend:,.2f}
• CTR: {avg_ctr:.2f}%
• CPC: ${avg_cpc:.2f}
• CPM: ${avg_cpm:.2f}

CONVERSION & ROAS:
• Total Conversions: {total_conversions:,}
• Total Revenue: ${total_revenue:,.2f}
• ROAS: {roas:.2f}x
• Cost per Conversion: ${(total_spend/total_conversions if total_conversions > 0 else 0):.2f}

CAMPAIGN STRUCTURE:
• Ad Sets: {len(adsets)}
• Ads: {len(ads)}
• Budget Type: {'Daily' if campaign.get('daily_budget') else 'Lifetime'}
• Bid Strategy: {campaign.get('bid_strategy', 'Unknown')}

AD SETS BREAKDOWN:
{chr(10).join(f"• {adset.get('name', 'Unknown')}: {adset.get('effective_status', 'Unknown')} - {adset.get('optimization_goal', 'Unknown')}" for adset in (adsets[:5] if isinstance(adsets, list) else []))}

KEY INSIGHTS (AI-Generated):
{chr(10).join(f"• {insight}" for insight in state.get('insights', [])[:5])}

RECOMMENDATIONS (AI-Generated):
{chr(10).join(f"• {rec}" for rec in state.get('recommendations', [])[:5])}

========================================
Generated with Dynamic Meta SDK Access
This report can fetch ANY data from Meta Ads API
========================================
"""
    
    if state.get('current_question'):
        return Command(
            update={
                "report_summary": report,
                "stage": "answering"
            },
            goto="answer_question"
        )
    else:
        return Command(
            update={
                "report_summary": report,
                "stage": "complete"
            },
            goto="complete"
        )


# async def answer_question_node(state: MetaCampaignState) -> Command[Literal["complete"]]:
    """Answer specific questions using all available data and AI"""
    if not state.get('current_question'):
        return Command(
            update={"stage": "complete"},
            goto="complete"
        )
    
    logger.info(f"Answering question with AI: {state.get('current_question')}")
    
    settings = get_settings()
    
    # Get AI model
    if settings.openai.api_key:
        model = ChatOpenAI(
            model=settings.openai.model,
            temperature=0.3,
            api_key=settings.openai.api_key
        )
    else:
        model = ChatAnthropic(
            model=settings.anthropic.model,
            temperature=0.3,
            api_key=settings.anthropic.api_key
        )
    
    # Create comprehensive context
    context = f"""You have access to the full Meta Ads SDK and have fetched comprehensive data.

Campaign Report:
{state.get('report_summary', '')}

Raw Campaign Data: {json.dumps(state.get('campaign_data', {}), indent=2)[:2000]}
Raw Insights Data: {json.dumps(state.get('insights_data', []), indent=2)[:2000]}
Ad Sets: {len(state.get('adsets_data', []))} ad sets
Ads: {len(state.get('ads_data', []))} ads

Question: {state.get('current_question', '')}

Provide a detailed, data-driven answer. You have access to ALL Meta Ads data through the SDK, 
so be specific and comprehensive in your response."""

    response = await model.ainvoke([SystemMessage(content=context)])
    
    return Command(
        update={
            "answer": response.content,
            "stage": "complete"
        },
        goto="complete"
    )


# async def handle_error_node(state: MetaCampaignState) -> Command[Literal["complete"]]:
    """Handle errors gracefully"""
    error_msg = state.get('error', 'Unknown error occurred')
    logger.error(f"Error in campaign analysis: {error_msg}")
    
    error_report = f"""
META ADS CAMPAIGN ERROR
========================================
Campaign ID: {state.get('campaign_id', 'Unknown')}
Error: {error_msg}

The Dynamic SDK encountered an issue. Please check:
1. Meta Access Token is valid
2. Campaign ID exists and you have permissions
3. API rate limits haven't been exceeded

With the dynamic SDK, you can fetch ANY data from Meta Ads.
Try adjusting your query or checking permissions.
========================================
"""
    
    return Command(
        update={
            "report_summary": error_report,
            "stage": "complete"
        },
        goto="complete"
    )


async def complete_node(state: MetaCampaignState) -> Command[Literal[END]]:
    """Complete the workflow"""
    logger.info("Dynamic Meta Ads analysis complete")
    
    # Return the answer or report
    if state.get('answer'):
        answer_msg = AIMessage(content=state.get('answer'))
        return Command(
            update={"messages": [answer_msg]},
            goto=END
        )
    elif state.get('report_summary'):
        report_msg = AIMessage(content=state.get('report_summary'))
        return Command(
            update={"messages": [report_msg]},
            goto=END
        )
    
    return Command(goto=END)


def create_dynamic_meta_campaign_graph():
    """Create a simplified Meta Ads campaign analysis graph"""
    
    graph = StateGraph(MetaCampaignState)
    
    # Add only essential nodes for clean flow
    graph.add_node("initialize", initialize_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("complete", complete_node)
    
    # Simple linear flow
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "analyze")
    graph.add_edge("analyze", "complete")
    graph.add_edge("complete", END)
    
    # Compile
    return graph.compile()


# Export the dynamic graph
meta_campaign_graph = create_dynamic_meta_campaign_graph()
