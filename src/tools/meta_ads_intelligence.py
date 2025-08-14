"""
Meta Ads Intelligence Layer
Advanced capabilities for smarter campaign analysis and optimization
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class MetaAdsIntelligence:
    """Advanced intelligence capabilities for Meta Ads"""
    
    def __init__(self):
        self.memory_file = "campaign_memory.json"
        self.alerts_file = "campaign_alerts.json"
        self.benchmarks_file = "industry_benchmarks.json"
        
    def calculate_health_score(self, metrics: Dict) -> Dict:
        """
        Calculate a comprehensive campaign health score (0-100)
        Based on multiple performance indicators
        """
        score = 0
        factors = []
        
        # CTR health (0-25 points)
        ctr = metrics.get('ctr', 0)
        if ctr > 2:
            ctr_score = 25
            factors.append("✅ Excellent CTR")
        elif ctr > 1:
            ctr_score = 20
            factors.append("👍 Good CTR")
        elif ctr > 0.5:
            ctr_score = 10
            factors.append("⚠️ Low CTR")
        else:
            ctr_score = 0
            factors.append("❌ Very low CTR")
        score += ctr_score
        
        # CPC efficiency (0-25 points)
        cpc = metrics.get('cpc', 999)
        if cpc < 0.5:
            cpc_score = 25
            factors.append("✅ Excellent CPC")
        elif cpc < 1:
            cpc_score = 20
            factors.append("👍 Good CPC")
        elif cpc < 2:
            cpc_score = 10
            factors.append("⚠️ High CPC")
        else:
            cpc_score = 0
            factors.append("❌ Very high CPC")
        score += cpc_score
        
        # ROAS performance (0-25 points)
        roas = metrics.get('roas', 0)
        if roas > 4:
            roas_score = 25
            factors.append("✅ Excellent ROAS")
        elif roas > 2:
            roas_score = 20
            factors.append("👍 Good ROAS")
        elif roas > 1:
            roas_score = 10
            factors.append("⚠️ Low ROAS")
        else:
            roas_score = 5
            factors.append("❌ Negative ROAS")
        score += roas_score
        
        # Spend efficiency (0-25 points)
        spend_efficiency = metrics.get('conversions', 0) / max(metrics.get('spend', 1), 1)
        if spend_efficiency > 0.1:
            spend_score = 25
            factors.append("✅ Efficient spending")
        elif spend_efficiency > 0.05:
            spend_score = 15
            factors.append("👍 Moderate efficiency")
        else:
            spend_score = 5
            factors.append("⚠️ Low spend efficiency")
        score += spend_score
        
        # Determine overall health
        if score >= 80:
            health = "🟢 Excellent"
        elif score >= 60:
            health = "🟡 Good"
        elif score >= 40:
            health = "🟠 Needs Attention"
        else:
            health = "🔴 Critical"
        
        return {
            "score": score,
            "health": health,
            "factors": factors,
            "breakdown": {
                "ctr_score": ctr_score,
                "cpc_score": cpc_score,
                "roas_score": roas_score,
                "spend_score": spend_score
            }
        }
    
    def detect_anomalies(self, current_metrics: Dict, historical_data: List[Dict]) -> List[Dict]:
        """
        Detect anomalies in campaign performance using statistical analysis
        """
        anomalies = []
        
        if not historical_data or len(historical_data) < 7:
            return anomalies
        
        # Convert to pandas for easier analysis
        df = pd.DataFrame(historical_data)
        
        # Check each metric for anomalies
        metrics_to_check = ['ctr', 'cpc', 'spend', 'impressions', 'clicks']
        
        for metric in metrics_to_check:
            if metric in df.columns and metric in current_metrics:
                # Calculate statistics
                mean = df[metric].mean()
                std = df[metric].std()
                current_value = current_metrics[metric]
                
                # Detect if current value is outside 2 standard deviations
                if abs(current_value - mean) > 2 * std:
                    severity = "high" if abs(current_value - mean) > 3 * std else "medium"
                    
                    change_pct = ((current_value - mean) / mean) * 100
                    
                    anomalies.append({
                        "metric": metric,
                        "current_value": current_value,
                        "expected_range": f"{mean - 2*std:.2f} - {mean + 2*std:.2f}",
                        "severity": severity,
                        "change_percent": change_pct,
                        "direction": "increase" if current_value > mean else "decrease",
                        "message": f"Unusual {metric}: {current_value:.2f} ({change_pct:+.1f}% from normal)"
                    })
        
        return anomalies
    
    def predict_performance(self, historical_data: List[Dict], days_ahead: int = 7) -> Dict:
        """
        Predict future campaign performance using trend analysis
        """
        if not historical_data or len(historical_data) < 7:
            return {"error": "Insufficient data for prediction"}
        
        df = pd.DataFrame(historical_data)
        predictions = {}
        
        # Simple linear regression for each metric
        metrics = ['spend', 'impressions', 'clicks', 'conversions']
        
        for metric in metrics:
            if metric in df.columns:
                # Create time series
                y = df[metric].values
                x = np.arange(len(y))
                
                # Fit linear trend
                z = np.polyfit(x, y, 1)
                p = np.poly1d(z)
                
                # Predict future values
                future_x = np.arange(len(y), len(y) + days_ahead)
                future_y = p(future_x)
                
                predictions[metric] = {
                    "current": float(y[-1]) if len(y) > 0 else 0,
                    "predicted_7d": float(future_y[-1]) if len(future_y) > 0 else 0,
                    "trend": "increasing" if z[0] > 0 else "decreasing",
                    "daily_change": float(z[0])
                }
        
        # Calculate predicted ROAS
        if 'conversions' in predictions and 'spend' in predictions:
            predicted_roas = predictions['conversions']['predicted_7d'] / max(predictions['spend']['predicted_7d'], 1)
            predictions['roas'] = {
                "predicted_7d": predicted_roas,
                "trend": "improving" if predicted_roas > 1 else "declining"
            }
        
        return predictions
    
    def generate_optimization_actions(self, campaign_data: Dict, performance_data: Dict) -> List[Dict]:
        """
        Generate specific optimization actions the agent can execute
        """
        actions = []
        
        # Check CTR
        ctr = performance_data.get('average_ctr', 0)
        if ctr < 1:
            actions.append({
                "priority": "high",
                "type": "creative_optimization",
                "action": "refresh_creatives",
                "reason": f"CTR is {ctr:.2f}%, below 1% threshold",
                "expected_impact": "Increase CTR by 20-50%",
                "implementation": {
                    "steps": [
                        "Test new ad copy variations",
                        "Update creative assets",
                        "A/B test different CTAs"
                    ]
                }
            })
        
        # Check CPC
        cpc = performance_data.get('average_cpc', 0)
        if cpc > 1.5:
            actions.append({
                "priority": "high",
                "type": "bidding_optimization",
                "action": "adjust_bidding_strategy",
                "reason": f"CPC is ${cpc:.2f}, above $1.50 threshold",
                "expected_impact": "Reduce CPC by 20-30%",
                "implementation": {
                    "steps": [
                        "Switch to automatic bidding",
                        "Adjust bid caps",
                        "Refine audience targeting"
                    ]
                }
            })
        
        # Check spend pacing
        spend = performance_data.get('total_spend', 0)
        budget = campaign_data.get('daily_budget', 0) * 30  # Monthly budget
        if budget > 0:
            pace_pct = (spend / budget) * 100
            if pace_pct < 50:
                actions.append({
                    "priority": "medium",
                    "type": "budget_optimization",
                    "action": "increase_delivery",
                    "reason": f"Only {pace_pct:.1f}% of budget spent",
                    "expected_impact": "Increase reach and conversions",
                    "implementation": {
                        "steps": [
                            "Expand audience targeting",
                            "Increase bid amounts",
                            "Add more placements"
                        ]
                    }
                })
        
        # Check for underperforming locations
        if 'adsets_data' in campaign_data:
            for adset in campaign_data.get('adsets_data', []):
                if adset.get('effective_status') == 'ACTIVE':
                    # This would need actual performance data per adset
                    actions.append({
                        "priority": "low",
                        "type": "geographic_optimization",
                        "action": "review_location_performance",
                        "reason": f"Review performance for {adset.get('name', 'Unknown')}",
                        "expected_impact": "Optimize budget allocation across locations",
                        "implementation": {
                            "steps": [
                                "Compare location performance",
                                "Reallocate budget to top performers",
                                "Pause underperforming locations"
                            ]
                        }
                    })
                    break  # Just one example
        
        return actions
    
    def compare_campaigns(self, campaigns: List[Dict]) -> Dict:
        """
        Compare multiple campaigns to find patterns and best practices
        """
        if len(campaigns) < 2:
            return {"error": "Need at least 2 campaigns to compare"}
        
        comparison = {
            "best_performer": None,
            "worst_performer": None,
            "insights": [],
            "metrics_comparison": {}
        }
        
        # Calculate scores for each campaign
        scores = []
        for campaign in campaigns:
            health = self.calculate_health_score(campaign)
            scores.append({
                "campaign_id": campaign.get('campaign_id'),
                "campaign_name": campaign.get('campaign_name'),
                "score": health['score'],
                "health": health['health']
            })
        
        # Sort by score
        scores.sort(key=lambda x: x['score'], reverse=True)
        comparison['best_performer'] = scores[0]
        comparison['worst_performer'] = scores[-1]
        
        # Generate insights
        score_diff = scores[0]['score'] - scores[-1]['score']
        comparison['insights'].append(
            f"Performance gap of {score_diff} points between best and worst campaigns"
        )
        
        # Compare key metrics
        metrics = ['ctr', 'cpc', 'roas', 'spend']
        for metric in metrics:
            values = [c.get(metric, 0) for c in campaigns]
            comparison['metrics_comparison'][metric] = {
                "best": max(values) if metric != 'cpc' else min(values),
                "worst": min(values) if metric != 'cpc' else max(values),
                "average": sum(values) / len(values),
                "variance": np.var(values)
            }
        
        return comparison


@tool
async def analyze_campaign_health(campaign_metrics: Dict) -> Dict:
    """
    Calculate comprehensive campaign health score with detailed breakdown
    
    Args:
        campaign_metrics: Dictionary containing campaign performance metrics
    
    Returns:
        Health score, status, and contributing factors
    """
    intelligence = MetaAdsIntelligence()
    return intelligence.calculate_health_score(campaign_metrics)


@tool
async def detect_performance_anomalies(current_metrics: Dict, historical_data: List[Dict]) -> List[Dict]:
    """
    Detect anomalies in campaign performance compared to historical patterns
    
    Args:
        current_metrics: Current campaign metrics
        historical_data: List of historical daily metrics
    
    Returns:
        List of detected anomalies with severity and recommendations
    """
    intelligence = MetaAdsIntelligence()
    return intelligence.detect_anomalies(current_metrics, historical_data)


@tool
async def predict_campaign_performance(historical_data: List[Dict], days_ahead: int = 7) -> Dict:
    """
    Predict future campaign performance based on historical trends
    
    Args:
        historical_data: Historical campaign metrics
        days_ahead: Number of days to predict ahead
    
    Returns:
        Predicted metrics and trends
    """
    intelligence = MetaAdsIntelligence()
    return intelligence.predict_performance(historical_data, days_ahead)


@tool
async def generate_optimization_plan(campaign_data: Dict, performance_data: Dict) -> List[Dict]:
    """
    Generate specific optimization actions the agent can execute
    
    Args:
        campaign_data: Campaign configuration and structure
        performance_data: Current performance metrics
    
    Returns:
        List of prioritized optimization actions
    """
    intelligence = MetaAdsIntelligence()
    return intelligence.generate_optimization_actions(campaign_data, performance_data)


@tool
async def compare_campaign_performance(campaigns: List[Dict]) -> Dict:
    """
    Compare multiple campaigns to identify best practices and patterns
    
    Args:
        campaigns: List of campaign data to compare
    
    Returns:
        Comparison analysis with best/worst performers and insights
    """
    intelligence = MetaAdsIntelligence()
    return intelligence.compare_campaigns(campaigns)


@tool
async def export_campaign_report(campaign_data: Dict, format: str = "markdown") -> str:
    """
    Export campaign report in various formats
    
    Args:
        campaign_data: Complete campaign data and analysis
        format: Export format (markdown, json, csv, html)
    
    Returns:
        Formatted report string
    """
    if format == "markdown":
        report = f"""# Meta Ads Campaign Report
        
## Campaign: {campaign_data.get('campaign_name', 'Unknown')}
**Date**: {datetime.now().strftime('%Y-%m-%d')}
**Status**: {campaign_data.get('status', 'Unknown')}

### Performance Summary
- **Spend**: ${campaign_data.get('total_spend', 0):,.2f}
- **Impressions**: {campaign_data.get('total_impressions', 0):,}
- **Clicks**: {campaign_data.get('total_clicks', 0):,}
- **CTR**: {campaign_data.get('average_ctr', 0):.2f}%
- **CPC**: ${campaign_data.get('average_cpc', 0):.2f}
- **ROAS**: {campaign_data.get('roas', 0):.2f}x

### Key Insights
{chr(10).join(f"- {insight}" for insight in campaign_data.get('insights', []))}

### Recommendations
{chr(10).join(f"1. {rec}" for rec in campaign_data.get('recommendations', []))}
"""
        return report
    
    elif format == "json":
        return json.dumps(campaign_data, indent=2)
    
    elif format == "csv":
        # Convert to CSV format
        df = pd.DataFrame([campaign_data])
        return df.to_csv(index=False)
    
    else:
        return "Unsupported format"


@tool
async def create_alert_rules(campaign_id: str, rules: List[Dict]) -> Dict:
    """
    Create automated alert rules for campaign monitoring
    
    Args:
        campaign_id: Campaign to monitor
        rules: List of alert rules with conditions and thresholds
        
    Example rules:
    [
        {"metric": "ctr", "condition": "below", "threshold": 1.0, "severity": "high"},
        {"metric": "spend", "condition": "above", "threshold": 1000, "severity": "medium"}
    ]
    
    Returns:
        Confirmation of created alert rules
    """
    alerts_file = f"alerts_{campaign_id}.json"
    
    # Save alert rules
    with open(alerts_file, 'w') as f:
        json.dump({
            "campaign_id": campaign_id,
            "rules": rules,
            "created_at": datetime.now().isoformat(),
            "active": True
        }, f, indent=2)
    
    return {
        "status": "success",
        "message": f"Created {len(rules)} alert rules for campaign {campaign_id}",
        "rules": rules
    }


@tool
async def get_competitive_benchmarks(industry: str = "events", region: str = "US") -> Dict:
    """
    Get industry benchmarks for comparison
    
    Args:
        industry: Industry category (events, ecommerce, entertainment, etc.)
        region: Geographic region
    
    Returns:
        Industry benchmark metrics
    """
    # These would ideally come from a benchmark database or API
    benchmarks = {
        "events": {
            "US": {
                "avg_ctr": 1.91,
                "avg_cpc": 1.32,
                "avg_cpm": 25.23,
                "avg_conversion_rate": 9.21,
                "avg_roas": 2.5
            }
        },
        "entertainment": {
            "US": {
                "avg_ctr": 1.45,
                "avg_cpc": 0.98,
                "avg_cpm": 14.23,
                "avg_conversion_rate": 7.5,
                "avg_roas": 3.2
            }
        }
    }
    
    return benchmarks.get(industry, {}).get(region, {
        "message": "No benchmarks available for this industry/region",
        "avg_ctr": 1.5,
        "avg_cpc": 1.0,
        "avg_cpm": 20.0,
        "avg_conversion_rate": 5.0,
        "avg_roas": 2.0
    })


# Export all tools
__all__ = [
    'analyze_campaign_health',
    'detect_performance_anomalies',
    'predict_campaign_performance',
    'generate_optimization_plan',
    'compare_campaign_performance',
    'export_campaign_report',
    'create_alert_rules',
    'get_competitive_benchmarks'
]