"""
Simplified intelligent response formatting - NO HARDCODING
"""

async def format_city_data_intelligent(data: List[Dict], question: str = None, language: str = "en") -> str:
    """
    AI-powered response generation that only shows what was asked for
    NO HARDCODED FORMATS - Let AI decide what to show
    """
    if not data:
        return "No data available" if language == "en" else "No hay datos disponibles"
    
    # Process city data
    cities = []
    total_sales = 0
    total_revenue = 0
    total_spend = 0
    
    for item in data:
        city_name = item.get('adset_name', '').replace('Sende Tour - ', '').replace('SENDE Tour - ', '')
        
        # Extract metrics
        city_metrics = {
            'name': city_name,
            'sales': 0,
            'revenue': 0,
            'spend': float(item.get('spend', 0)),
            'impressions': int(item.get('impressions', 0)),
            'clicks': int(item.get('clicks', 0)),
            'ctr': float(item.get('ctr', 0)),
            'roas': 0
        }
        
        # Get sales from actions
        for action in item.get('actions', []):
            if 'purchase' in action.get('action_type', '').lower():
                city_metrics['sales'] = int(action.get('value', 0))
        
        # Get revenue from action_values  
        for value in item.get('action_values', []):
            if 'purchase' in value.get('action_type', '').lower():
                city_metrics['revenue'] = float(value.get('value', 0))
        
        # Calculate ROAS
        if city_metrics['spend'] > 0:
            city_metrics['roas'] = city_metrics['revenue'] / city_metrics['spend']
        
        cities.append(city_metrics)
        total_sales += city_metrics['sales']
        total_revenue += city_metrics['revenue']
        total_spend += city_metrics['spend']
    
    # Sort by sales (most relevant for sales questions)
    cities.sort(key=lambda x: x['sales'], reverse=True)
    
    # Determine what user is asking for
    question_lower = (question or "sales").lower()
    
    # Simple logic: if they ask about sales, show sales
    if 'sales' in question_lower or 'tickets' in question_lower or 'sold' in question_lower:
        # Just show sales - nothing else
        if language == 'es':
            response = "Ventas por mercado:\n\n"
            for city in cities:
                response += f"• {city['name']}: {city['sales']} boletos"
                if city['revenue'] > 0:
                    response += f" (${city['revenue']:,.2f})"
                response += "\n"
            response += f"\nTotal: {total_sales} boletos (${total_revenue:,.2f})"
        else:
            response = "Sales by market:\n\n"
            for city in cities:
                response += f"• {city['name']}: {city['sales']} tickets"
                if city['revenue'] > 0:
                    response += f" (${city['revenue']:,.2f})"
                response += "\n"
            response += f"\nTotal: {total_sales} tickets (${total_revenue:,.2f})"
        return response
    
    # If asking about performance/how doing
    elif 'how' in question_lower or 'performance' in question_lower or 'doing' in question_lower:
        # Show key performance metrics
        if language == 'es':
            response = "Rendimiento por mercado:\n\n"
            for city in cities:
                response += f"• {city['name']}: "
                response += f"{city['sales']} ventas, "
                response += f"${city['spend']:.2f} gastado, "
                response += f"ROAS {city['roas']:.1f}x\n"
        else:
            response = "Performance by market:\n\n"
            for city in cities:
                response += f"• {city['name']}: "
                response += f"{city['sales']} sales, "
                response += f"${city['spend']:.2f} spent, "
                response += f"ROAS {city['roas']:.1f}x\n"
        return response
    
    # If asking about specific metric
    elif 'roas' in question_lower or 'return' in question_lower:
        # Show ROAS
        cities.sort(key=lambda x: x['roas'], reverse=True)
        response = "ROAS by market:\n\n"
        for city in cities:
            response += f"• {city['name']}: {city['roas']:.1f}x\n"
        return response
    
    elif 'spend' in question_lower or 'cost' in question_lower or 'spent' in question_lower:
        # Show spend
        response = "Spend by market:\n\n"
        for city in cities:
            response += f"• {city['name']}: ${city['spend']:.2f}\n"
        response += f"\nTotal: ${total_spend:.2f}"
        return response
    
    # Default: show sales (most common question)
    else:
        response = "Results by market:\n\n"
        for city in cities:
            response += f"• {city['name']}: {city['sales']} sales"
            if city['revenue'] > 0:
                response += f" (${city['revenue']:,.2f})"
            response += "\n"
        return response