"""
Dynamic Meta/Facebook Ads SDK Integration
Provides intelligent, flexible access to all Meta APIs
The AI agent can dynamically call any endpoint and fetch any data
"""
import os
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from ..config.security_config import get_allowed_campaigns, can_access_campaign, filter_campaigns_by_access

# Facebook Business SDK imports
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adsinsights import AdsInsights
from facebook_business.adobjects.user import User
from facebook_business.adobjects.business import Business
from facebook_business.adobjects.page import Page
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.adspixel import AdsPixel
from facebook_business.exceptions import FacebookRequestError

load_dotenv()
logger = logging.getLogger(__name__)


class DynamicMetaSDK:
    """
    Dynamic Meta/Facebook SDK wrapper that provides intelligent access to all APIs
    The AI agent can use this to fetch any data it needs without constraints
    """
    
    # Thread pool for blocking operations
    _executor = ThreadPoolExecutor(max_workers=3)
    
    def __init__(self):
        """Initialize the Facebook Business SDK with credentials"""
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.app_id = os.getenv("META_APP_ID")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.ad_account_id = os.getenv("META_AD_ACCOUNT_ID")
        self.api_version = os.getenv("META_API_VERSION", "v21.0")
        
        # Security context
        self.current_user_phone = None
        self.allowed_campaigns = []
        
        # Normalize Ad Account ID to always include 'act_' prefix when used
        def _format_account_id(raw_id: Optional[str]) -> Optional[str]:
            if not raw_id:
                return None
            raw = str(raw_id)
            return raw if raw.startswith("act_") else f"act_{raw}"
        self._account_id_formatted = _format_account_id(self.ad_account_id)
        
        if self.access_token:
            FacebookAdsApi.init(
                app_id=self.app_id,
                app_secret=self.app_secret,
                access_token=self.access_token,
                api_version=self.api_version
            )
            logger.info("Facebook Business SDK initialized successfully")
        else:
            logger.error("No META_ACCESS_TOKEN found - SDK not initialized")
        
        # Initialize AI for intelligent query understanding
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        ) if os.getenv("OPENAI_API_KEY") else None
    
    def set_user_context(self, phone_number: str):
        """Set the current user context for security filtering"""
        self.current_user_phone = phone_number
        self.allowed_campaigns = get_allowed_campaigns(phone_number)
        logger.info(f"User context set: {phone_number}, allowed campaigns: {self.allowed_campaigns}")
    
    def check_campaign_access(self, campaign_id: str) -> bool:
        """Check if current user can access this campaign"""
        if not self.current_user_phone:
            return True  # No security context set, allow for backward compatibility
        
        if "*" in self.allowed_campaigns:
            return True  # User has access to all campaigns
        
        return campaign_id in self.allowed_campaigns
    
    def get_api_object(self, object_type: str, object_id: str) -> Any:
        """
        Dynamically get any Facebook API object
        
        Args:
            object_type: Type of object (Campaign, AdSet, Ad, AdAccount, etc.)
            object_id: ID of the object
        
        Returns:
            The requested Facebook API object
        """
        object_mapping = {
            "campaign": Campaign,
            "adset": AdSet,
            "ad": Ad,
            "adaccount": AdAccount,
            "adcreative": AdCreative,
            "user": User,
            "business": Business,
            "page": Page,
            "customaudience": CustomAudience,
            "pixel": AdsPixel
        }
        
        obj_class = object_mapping.get(object_type.lower())
        if not obj_class:
            raise ValueError(f"Unknown object type: {object_type}")
        
        return obj_class(object_id)
    
    def fetch_data(self, 
                   object_type: str,
                   object_id: str,
                   fields: Optional[List[str]] = None,
                   params: Optional[Dict[str, Any]] = None,
                   edge: Optional[str] = None) -> Union[Dict, List]:
        """
        Fetch any data from any Meta API object with any fields and parameters
        
        Args:
            object_type: Type of object (Campaign, AdSet, Ad, etc.)
            object_id: ID of the object
            fields: List of fields to fetch (if None, fetches default fields)
            params: Additional parameters for the API call
            edge: Edge to fetch (e.g., 'insights', 'ads', 'adsets')
        
        Returns:
            The fetched data as dict or list
        """
        try:
            obj = self.get_api_object(object_type, object_id)
            
            if edge:
                # Supported edges mapping to typed SDK methods
                edge = edge.lower()
                method_name_map = {
                    "insights": "get_insights",
                    "ads": "get_ads",
                    "adsets": "get_ad_sets",
                    "campaigns": "get_campaigns",
                    "adcreatives": "get_adcreatives",
                }
                method_name = method_name_map.get(edge)
                if not method_name:
                    return {"error": f"Unsupported edge '{edge}' for object {object_type}"}
                edge_method = getattr(obj, method_name, None)
                if not callable(edge_method):
                    return {"error": f"Edge method '{method_name}' not available for {object_type}"}
                result = edge_method(fields=fields, params=params or {})
                return [item.export_all_data() for item in result]
            else:
                # Fetch object data directly
                obj.remote_read(fields=fields)
                return obj.export_all_data()
                
        except FacebookRequestError as e:
            logger.error(f"Facebook API error: {e}")
            return {"error": str(e), "error_code": e.api_error_code()}
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return {"error": str(e)}
    
    async def understand_request(self, request: str) -> Dict[str, Any]:
        """
        Use AI to understand natural language requests
        """
        if not self.llm:
            # Fallback to basic parsing if no LLM
            return {"operation": "custom_query", "description": request}
        
        prompt = f"""
        Analyze this Meta Ads request and determine the API operations needed.
        
        Request: "{request}"
        
        IMPORTANT: In Meta Ads, cities/locations are represented as AdSet names, NOT as breakdowns.
        If the user asks for city-level data, use get_adsets_insights operation.
        
        Available operations:
        - get_campaign_insights: Get performance metrics for campaigns (overall metrics)
        - get_all_campaigns: List all campaigns
        - get_adsets_insights: Get adset-level metrics (USE THIS FOR CITY-LEVEL DATA)
        - get_audience_insights: Get demographic breakdowns (age, gender)
        - custom_query: Custom API query
        
        Return a JSON with:
        {{
            "operation": "operation_name",
            "campaign_id": "id if mentioned",
            "date_preset": "last_30d|last_7d|today|yesterday",
            "fields": ["relevant", "fields"],
            "breakdowns": ["age", "gender"] ONLY for demographics, NOT for cities,
            "level": "campaign|adset|ad"
        }}
        
        If user asks for city/location data: use operation "get_adsets_insights" WITHOUT any "city" breakdown
        """
        
        response = await self.llm.ainvoke(prompt)
        try:
            import json
            return json.loads(response.content)
        except:
            return {"operation": "get_campaign_insights", "date_preset": "last_30d"}
    
    def execute_query(self, query: Dict[str, Any]) -> Any:
        """
        Execute a complex query with multiple operations
        
        Args:
            query: Dictionary describing the query to execute
                  Example: {
                      "operation": "get_campaign_insights",
                      "campaign_id": "123",
                      "date_preset": "last_30d",
                      "breakdowns": ["age", "gender"],
                      "fields": ["impressions", "clicks", "spend"]
                  }
        
        Returns:
            Query results
        """
        operation = query.get("operation", "fetch")
        
        if operation == "get_campaign_insights":
            # Handle case where campaign_id might be in object_id
            campaign_id = query.get("campaign_id") or query.get("object_id")
            
            # CRITICAL FIX: Handle both flat and nested params structure
            date_preset = query.get("date_preset")
            if not date_preset and "params" in query and isinstance(query["params"], dict):
                date_preset = query["params"].get("date_preset")
            if not date_preset:
                date_preset = "maximum"  # Default to maximum for all-time data
            
            breakdowns = query.get("breakdowns")
            if not breakdowns and "params" in query and isinstance(query["params"], dict):
                breakdowns = query["params"].get("breakdowns")
            
            time_increment = query.get("time_increment")
            if not time_increment and "params" in query and isinstance(query["params"], dict):
                time_increment = query["params"].get("time_increment")
            
            if not campaign_id:
                # If no specific campaign, get all campaigns insights
                return self.get_all_campaigns_insights(
                    date_preset,
                    query.get("fields"),
                    breakdowns
                )
            return self.get_campaign_insights_dynamic(
                campaign_id,
                date_preset,
                query.get("fields"),
                breakdowns,
                time_increment
            )
        
        elif operation == "get_all_campaigns":
            return self.get_all_campaigns(
                query.get("fields"),
                query.get("filtering"),
                query.get("limit", 100)
            )
        
        elif operation == "get_audience_insights":
            return self.get_audience_insights(
                query.get("object_id"),
                query.get("object_type", "campaign")
            )
        
        elif operation == "get_adsets_insights":
            # Fetch insights for all adsets in a campaign
            # Handle case where campaign_id might be in object_id
            campaign_id = query.get("campaign_id") or query.get("object_id")
            if not campaign_id:
                return {"error": "No campaign_id provided for adsets insights"}
            
            # CRITICAL FIX: Handle both flat and nested date_preset
            # The AI might generate {"params": {"date_preset": "today"}} or {"date_preset": "today"}
            date_preset = query.get("date_preset")
            if not date_preset and "params" in query and isinstance(query["params"], dict):
                date_preset = query["params"].get("date_preset")
            if not date_preset:
                date_preset = "maximum"  # Default to maximum instead of today
                
            logger.info(f"get_adsets_insights called with date_preset: {date_preset}")
            
            # Similarly handle level from params if present
            level = query.get("level")
            if not level and "params" in query and isinstance(query["params"], dict):
                level = query["params"].get("level")
            if not level:
                level = "adset"
                
            return self.get_adsets_insights(
                campaign_id,
                date_preset,
                query.get("fields"),
                level
            )
        
        elif operation == "custom_query":
            return self.fetch_data(
                query.get("object_type"),
                query.get("object_id"),
                query.get("fields"),
                query.get("params"),
                query.get("edge")
            )
        
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    def get_campaign_insights_dynamic(self,
                                      campaign_id: str,
                                      date_preset: str = "maximum",
                                      fields: Optional[List[str]] = None,
                                      breakdowns: Optional[List[str]] = None,
                                      time_increment: Optional[str] = None) -> List[Dict]:
        """
        Get campaign insights with dynamic field selection
        """
        try:
            if not campaign_id:
                return {"error": "No campaign ID provided"}
            
            if not self.access_token:
                return {"error": "No Meta access token configured"}
            
            # Check campaign access permissions
            if not self.check_campaign_access(campaign_id):
                logger.warning(f"Access denied: User {self.current_user_phone} tried to access campaign {campaign_id}")
                return {"error": "Access denied", "message": "You don't have permission to access this campaign"}
            
            campaign = Campaign(campaign_id)
            
            # Default fields if none specified
            if not fields:
                fields = [
                    'campaign_name', 'impressions', 'clicks', 'ctr', 'cpc', 'cpm',
                    'spend', 'reach', 'frequency', 'conversions', 'purchase_roas',
                    'actions', 'action_values', 'cost_per_action_type'
                ]
            
            params = {
                'date_preset': date_preset,
                'level': 'campaign',
                'time_increment': time_increment or '1'  # Daily by default
            }
            
            if breakdowns:
                params['breakdowns'] = breakdowns  # Pass as list, not joined string
            
            insights = campaign.get_insights(fields=fields, params=params)
            return [insight.export_all_data() for insight in insights]
        except Exception as e:
            logger.error(f"Error getting campaign insights: {e}")
            return {"error": str(e), "message": "Failed to fetch campaign insights"}
    
    def get_all_campaigns(self, 
                         fields: Optional[List[str]] = None,
                         filtering: Optional[List[Dict]] = None,
                         limit: int = 100) -> List[Dict]:
        """
        Get all campaigns from the ad account with optional filtering
        """
        try:
            if not self._account_id_formatted:
                return {"error": "No ad account ID configured"}
            
            if not self.access_token:
                return {"error": "No Meta access token configured"}
            
            account = AdAccount(self._account_id_formatted)
            
            if not fields:
                fields = [
                    'name', 'objective', 'status', 'effective_status',
                    'daily_budget', 'lifetime_budget', 'spend_cap',
                    'created_time', 'start_time', 'stop_time'
                ]
            
            params = {'limit': limit}
            if filtering:
                params['filtering'] = filtering
            
            campaigns = account.get_campaigns(fields=fields, params=params)
            all_campaigns = [campaign.export_all_data() for campaign in campaigns]
            
            # Filter by allowed campaigns if security context is set
            if self.current_user_phone:
                if "*" not in self.allowed_campaigns:
                    # Filter to only allowed campaigns
                    all_campaigns = [c for c in all_campaigns if c.get('id') in self.allowed_campaigns]
            
            return all_campaigns
        except Exception as e:
            logger.error(f"Error getting campaigns: {e}")
            return {"error": str(e), "message": "Failed to fetch campaigns from Meta API"}
    
    def get_adsets_insights(self, 
                           campaign_id: str,
                           date_preset: str = "maximum",
                           fields: Optional[List[str]] = None,
                           level: str = "adset") -> List[Dict]:
        """
        Get insights for all adsets in a campaign
        """
        try:
            if not campaign_id:
                logger.error("No campaign_id provided for adsets insights")
                return []
            
            if not self.access_token:
                logger.error("No Meta access token configured")
                return []
            
            logger.info(f"Getting adsets insights for campaign {campaign_id}, date_preset: {date_preset}, fields: {fields}")
            
            # Check campaign access permissions
            if not self.check_campaign_access(campaign_id):
                logger.warning(f"Access denied: User {self.current_user_phone} tried to access campaign {campaign_id}")
                return []
            
            campaign = Campaign(campaign_id)
            
            # Get all adsets for this campaign
            adsets = campaign.get_ad_sets(fields=['id', 'name', 'status'])
            logger.info(f"Found {len(list(adsets))} adsets for campaign {campaign_id}")
            
            # Default fields if none specified
            if not fields:
                fields = [
                    'adset_name', 'impressions', 'clicks', 'ctr', 'cpc', 'cpm',
                    'spend', 'reach', 'frequency', 'conversions', 'purchase_roas',
                    'actions', 'action_values', 'inline_link_clicks'
                ]
            
            # Collect insights from all adsets
            all_insights = []
            adsets_list = list(campaign.get_ad_sets(fields=['id', 'name', 'status']))  # Re-fetch since we consumed iterator
            logger.info(f"Processing {len(adsets_list)} adsets")
            
            for adset in adsets_list:
                try:
                    adset_id = adset.get('id')
                    adset_name = adset.get('name', 'Unknown')
                    
                    if not adset_id:
                        logger.warning(f"Skipping adset with no ID: {adset}")
                        continue
                    
                    logger.debug(f"Getting insights for adset {adset_id}: {adset_name}")
                    
                    # Create AdSet object properly
                    adset_obj = AdSet(adset_id)
                    
                    params = {
                        'date_preset': date_preset,
                        'level': level
                    }
                    
                    insights = adset_obj.get_insights(fields=fields, params=params)
                    insights_list = list(insights)
                    logger.debug(f"Got {len(insights_list)} insights for adset {adset_name}")
                    
                    for insight in insights_list:
                        insight_data = insight.export_all_data()
                        # Add adset name (city name) if not present
                        if 'adset_name' not in insight_data:
                            insight_data['adset_name'] = adset_name
                        # Add city field for clarity
                        insight_data['city'] = adset_name
                        all_insights.append(insight_data)
                        
                except Exception as e:
                    logger.warning(f"Error getting insights for adset {adset.get('id', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Returning {len(all_insights)} total insights from adsets")
            return all_insights
            
        except Exception as e:
            logger.error(f"Error getting adsets insights: {str(e)}", exc_info=True)
            return []
    
    def get_all_campaigns_insights(self, 
                                   date_preset: str = "last_30d",
                                   fields: Optional[List[str]] = None,
                                   breakdowns: Optional[List[str]] = None) -> List[Dict]:
        """
        Get insights for all campaigns
        """
        try:
            if not self._account_id_formatted:
                return {"error": "No ad account ID configured"}
            
            if not self.access_token:
                return {"error": "No Meta access token configured"}
            
            # First get all campaigns
            campaigns = self.get_all_campaigns(limit=10)  # Limit to 10 for performance
            
            if isinstance(campaigns, dict) and "error" in campaigns:
                return campaigns
            
            # Default fields if none specified
            if not fields:
                fields = [
                    'campaign_name', 'impressions', 'clicks', 'ctr', 'cpc', 'cpm',
                    'spend', 'reach', 'frequency', 'conversions', 'purchase_roas',
                    'actions', 'action_values'
                ]
            
            all_insights = []
            for campaign in campaigns[:5]:  # Get insights for top 5 campaigns
                try:
                    campaign_id = campaign.get('id')
                    if campaign_id:
                        campaign_obj = Campaign(campaign_id)
                        params = {
                            'date_preset': date_preset,
                            'level': 'campaign'
                        }
                        if breakdowns:
                            params['breakdowns'] = breakdowns
                        
                        insights = campaign_obj.get_insights(fields=fields, params=params)
                        for insight in insights:
                            insight_data = insight.export_all_data()
                            insight_data['campaign_id'] = campaign_id
                            insight_data['campaign_name'] = campaign.get('name', 'Unknown')
                            all_insights.append(insight_data)
                except Exception as e:
                    logger.warning(f"Error getting insights for campaign {campaign_id}: {e}")
                    continue
            
            return all_insights
            
        except Exception as e:
            logger.error(f"Error getting all campaigns insights: {e}")
            return {"error": str(e), "message": "Failed to fetch campaigns insights"}
    
    def get_audience_insights(self, object_id: str, object_type: str = "campaign") -> Dict:
        """
        Get detailed audience insights for any object
        """
        obj = self.get_api_object(object_type, object_id)
        
        # Get insights with demographic breakdowns
        # Note: Meta API allows limited breakdown combinations
        params = {
            'date_preset': 'last_30d',
            'breakdowns': ['age', 'gender'],  # Use list format
            'level': object_type
        }
        
        fields = ['impressions', 'reach', 'clicks', 'spend', 'actions', 'action_values']
        
        insights = obj.get_insights(fields=fields, params=params)
        
        # Process and structure the insights
        demographics = {
            "age_groups": {},
            "genders": {},
            "countries": {},
            "regions": {},
            "devices": {}
        }
        
        for insight in insights:
            data = insight.export_all_data()
            
            if 'age' in data:
                demographics['age_groups'][data['age']] = {
                    'impressions': data.get('impressions', 0),
                    'clicks': data.get('clicks', 0),
                    'spend': data.get('spend', 0)
                }
            
            if 'gender' in data:
                demographics['genders'][data['gender']] = {
                    'impressions': data.get('impressions', 0),
                    'clicks': data.get('clicks', 0),
                    'spend': data.get('spend', 0)
                }
            
            if 'country' in data:
                demographics['countries'][data['country']] = {
                    'impressions': data.get('impressions', 0),
                    'clicks': data.get('clicks', 0),
                    'spend': data.get('spend', 0)
                }
        
        return demographics


# Initialize the SDK
meta_sdk = DynamicMetaSDK()


@tool
def meta_sdk_query(query: Dict[str, Any]) -> Any:
    """
    Execute any Meta/Facebook Ads API query dynamically
    
    This is a powerful tool that gives the AI agent full access to the Meta Ads SDK.
    The agent can fetch any data from any object with any fields and parameters.
    
    Args:
        query: A dictionary describing what to fetch. Examples:
        
        1. Get campaign insights:
        {
            "operation": "get_campaign_insights",
            "campaign_id": "120232002620350525",
            "date_preset": "last_30d",
            "fields": ["impressions", "clicks", "spend", "purchase_roas"],
            "breakdowns": ["age", "gender"],
            "time_increment": "1"
        }
        
        2. Get all campaigns:
        {
            "operation": "get_all_campaigns",
            "fields": ["name", "status", "objective", "spend_cap"],
            "filtering": [{"field": "effective_status", "operator": "IN", "value": ["ACTIVE"]}]
        }
        
        3. Custom query for any object:
        {
            "operation": "custom_query",
            "object_type": "adset",
            "object_id": "120232007448100525",
            "fields": ["name", "targeting", "optimization_goal", "bid_strategy"],
            "edge": "ads"  # Optional: fetch ads under this adset
        }
        
        4. Get audience insights:
        {
            "operation": "get_audience_insights",
            "object_id": "120232002620350525",
            "object_type": "campaign"
        }
        
        5. Get adsets insights:
        {
            "operation": "get_adsets_insights",
            "campaign_id": "120232002620350525",
            "date_preset": "today",
            "fields": ["adset_name", "impressions", "clicks", "spend"],
            "level": "adset"
        }
    
    Returns:
        The requested data from Meta Ads API
    """
    logger.info(f"meta_sdk_query called with: {json.dumps(query, indent=2)}")
    
    try:
        # Check if we're in an async context (LangGraph Studio)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context - run in thread pool to avoid blocking
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(meta_sdk.execute_query, query)
                result = future.result(timeout=30)  # Increased timeout to 30 seconds
        else:
            # Normal sync execution
            result = meta_sdk.execute_query(query)
        
        # Enhanced logging to understand the result
        logger.info(f"meta_sdk_query result type: {type(result)}, length: {len(result) if isinstance(result, list) else 'N/A'}")
        if isinstance(result, list) and len(result) > 0:
            logger.info(f"First result item keys: {result[0].keys() if isinstance(result[0], dict) else 'N/A'}")
        elif isinstance(result, dict):
            logger.info(f"Result keys: {result.keys()}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in meta_sdk_query: {str(e)}", exc_info=True)
        return {"error": str(e), "message": "Failed to fetch data from Meta API", "error_type": type(e).__name__}


@tool
async def intelligent_meta_query(request: str) -> Any:
    """
    Intelligent natural language interface to Meta Ads
    
    Just describe what you want in plain English:
    - "Show me how my campaigns are performing"
    - "What's the CTR for Miami?"
    - "Get demographic breakdown"
    - "How much did I spend today?"
    - "Show me ROAS for last week"
    
    The AI understands your request and fetches the right data.
    
    Args:
        request: Natural language request
    
    Returns:
        The requested Meta Ads data
    """
    logger.info(f"Intelligent query: {request}")
    
    try:
        # Understand the request
        query = await meta_sdk.understand_request(request)
        logger.info(f"Understood as: {query}")
        
        # Execute the query
        result = meta_sdk.execute_query(query)
        return result
    except Exception as e:
        logger.error(f"Error in intelligent query: {e}")
        return {"error": str(e)}


@tool
def meta_sdk_discover(object_type: str = "campaign", object_id: Optional[str] = None) -> Dict:
    """
    Discover available fields and edges for a Meta API object
    
    This helps the AI agent understand what data is available to fetch.
    
    Args:
        object_type: Type of object (campaign, adset, ad, adaccount, etc.)
        object_id: Optional ID to get specific object metadata
    
    Returns:
        Dictionary with available fields, edges, and capabilities
    """
    # Common fields for different object types
    field_mapping = {
        "campaign": {
            "fields": [
                "name", "objective", "status", "effective_status", "daily_budget",
                "lifetime_budget", "spend_cap", "created_time", "start_time", "stop_time",
                "bid_strategy", "budget_optimization", "source_campaign_id"
            ],
            "edges": ["insights", "ads", "adsets", "ads_pixels", "copies"],
            "insights_fields": [
                # Basic metrics
                "impressions", "clicks", "ctr", "cpc", "cpm", "cpp", "spend", "reach",
                "frequency", "unique_clicks", "unique_ctr", "cost_per_unique_click",
                
                # Conversion metrics
                "conversions", "conversion_rate", "cost_per_conversion", 
                "purchase_roas", "website_purchase_roas", "mobile_app_purchase_roas",
                
                # Action metrics
                "actions", "action_values", "cost_per_action_type", "unique_actions",
                "website_ctr", "website_clicks", "deeplink_clicks", "app_store_clicks",
                
                # Video metrics
                "video_views", "video_p25_watched_actions", "video_p50_watched_actions",
                "video_p75_watched_actions", "video_p95_watched_actions", "video_p100_watched_actions",
                "video_avg_time_watched_actions", "video_play_actions", "video_thruplay_watched_actions",
                "cost_per_thruplay", "video_15s_watched_actions", "video_30_sec_watched_actions",
                
                # Engagement metrics
                "engagement", "post_engagement", "page_engagement", "post_reactions",
                "post_comments", "post_shares", "post_saves", "photo_views", "link_clicks",
                "landing_page_views", "instant_experience_clicks_to_open", "instant_experience_clicks_to_start",
                
                # Lead metrics
                "leads", "cost_per_lead", "lead_form_opens", "lead_form_views",
                
                # E-commerce metrics
                "adds_to_cart", "adds_to_wishlist", "checkouts_initiated", "payment_info_added",
                "purchases", "omni_purchases", "website_purchases", "in_app_purchases",
                "offline_purchases", "catalog_segment_actions", "catalog_segment_value",
                "catalog_segment_value_mobile_purchase_roas", "catalog_segment_value_omni_purchase_roas",
                "catalog_segment_value_website_purchase_roas",
                
                # App metrics
                "app_installs", "app_use", "app_activations", "app_registrations",
                "app_sessions", "app_adds_to_cart", "app_adds_to_wishlist", "app_checkouts_initiated",
                "app_content_views", "app_custom_events", "app_purchases", "app_ratings",
                "app_achievement_unlocked", "app_tutorial_completed",
                
                # Store metrics
                "store_location_page_views", "store_directions", "store_locator_searches",
                
                # Quality and relevance metrics
                "quality_ranking", "engagement_rate_ranking", "conversion_rate_ranking",
                "inline_link_clicks", "inline_link_click_ctr", "inline_post_engagement",
                "unique_inline_link_clicks", "unique_inline_link_click_ctr",
                
                # Attribution metrics
                "estimated_ad_recallers", "estimated_ad_recall_rate", "cost_per_estimated_ad_recaller",
                "reach_frequency", "full_view_impressions", "full_view_reach",
                
                # Advanced metrics
                "social_spend", "dda_countby_convs", "dda_results", "canvas_avg_view_percent",
                "canvas_avg_view_time", "outbound_clicks", "outbound_clicks_ctr",
                "unique_outbound_clicks", "unique_outbound_clicks_ctr"
            ],
            "breakdowns": [
                "age", "gender", "country", "region", "dma", "device_platform",
                "publisher_platform", "platform_position", "impression_device"
            ]
        },
        "adset": {
            "fields": [
                "name", "status", "effective_status", "daily_budget", "lifetime_budget",
                "bid_strategy", "optimization_goal", "billing_event", "targeting",
                "promoted_object", "attribution_spec"
            ],
            "edges": ["insights", "ads", "activities", "delivery_estimate"],
            "insights_fields": ["impressions", "clicks", "spend", "conversions"]
        },
        "ad": {
            "fields": [
                "name", "status", "effective_status", "creative", "bid_type",
                "bid_amount", "targeting", "tracking_specs", "conversion_specs"
            ],
            "edges": ["insights", "creatives", "previews", "leads"],
            "insights_fields": ["impressions", "clicks", "spend", "actions"]
        },
        "adaccount": {
            "fields": [
                "name", "account_status", "currency", "timezone_name", "spend_cap",
                "amount_spent", "balance", "business", "capabilities"
            ],
            "edges": [
                "campaigns", "adsets", "ads", "insights", "users", "custom_audiences",
                "pixels", "applications", "businesses"
            ]
        }
    }
    
    info = field_mapping.get(object_type.lower(), {})
    
    if object_id and meta_sdk.access_token:
        try:
            # Try to get actual object metadata
            obj = meta_sdk.get_api_object(object_type, object_id)
            obj.remote_read(fields=['id', 'name'])
            info['object_exists'] = True
            info['object_name'] = obj.get('name', 'Unknown')
        except:
            info['object_exists'] = False
    
    return {
        "object_type": object_type,
        "available_fields": info.get("fields", []),
        "available_edges": info.get("edges", []),
        "insights_fields": info.get("insights_fields", []),
        "breakdowns": info.get("breakdowns", []),
        "description": f"Use meta_sdk_query to fetch any of these fields or edges for {object_type}"
    }


@tool
def meta_sdk_batch_query(queries: List[Dict[str, Any]]) -> List[Any]:
    """
    Execute multiple Meta API queries in batch for efficiency
    
    Args:
        queries: List of query dictionaries (same format as meta_sdk_query)
    
    Returns:
        List of results for each query
    """
    results = []
    for query in queries:
        result = meta_sdk.execute_query(query)
        results.append(result)
    return results


@tool
def meta_sdk_search(search_type: str, search_term: str, limit: int = 10) -> List[Dict]:
    """
    Search for Meta Ads objects by name or other criteria
    
    Args:
        search_type: What to search for (campaigns, adsets, ads, audiences)
        search_term: Search term to look for
        limit: Maximum number of results
    
    Returns:
        List of matching objects
    """
    if not meta_sdk._account_id_formatted:
        return [{"error": "No ad account configured"}]
    
    account = AdAccount(meta_sdk._account_id_formatted)
    
    if search_type == "campaigns":
        campaigns = account.get_campaigns(
            fields=['name', 'status', 'objective'],
            params={'limit': 500}  # Get more to search through
        )
        results = []
        for campaign in campaigns:
            data = campaign.export_all_data()
            if search_term.lower() in data.get('name', '').lower():
                results.append(data)
                if len(results) >= limit:
                    break
        return results
    
    elif search_type == "adsets":
        adsets = account.get_ad_sets(
            fields=['name', 'status', 'campaign_id'],
            params={'limit': 500}
        )
        results = []
        for adset in adsets:
            data = adset.export_all_data()
            if search_term.lower() in data.get('name', '').lower():
                results.append(data)
                if len(results) >= limit:
                    break
        return results
    
    else:
        return [{"error": f"Search type {search_type} not supported"}]


# Export the main tool for the agent to use
__all__ = ['meta_sdk_query', 'meta_sdk_discover', 'meta_sdk_batch_query', 'meta_sdk_search']
