#!/usr/bin/env python3
"""Debug LangSmith trace 1f079948-0620-62b7-8194-71b5123682ff"""

import os
import json
from datetime import datetime
from langsmith import Client
from dotenv import load_dotenv

load_dotenv()

# Initialize LangSmith client
client = Client()

def analyze_trace(trace_id):
    """Analyze a specific trace"""
    print(f"🔍 Debugging Trace: {trace_id}")
    print("="*80)
    
    try:
        # Fetch the run
        run = client.read_run(trace_id)
        
        # Basic info
        print(f"📅 Timestamp: {run.start_time}")
        duration = (run.end_time - run.start_time).total_seconds() if run.end_time else None
        print(f"⏱️ Duration: {duration:.2f}s" if duration else "⏱️ Duration: N/A")
        print(f"📊 Status: {run.status}")
        print(f"🏷️ Name: {run.name}")
        
        # Extract input
        print("\n📥 USER QUERY:")
        print("-"*40)
        if run.inputs:
            messages = run.inputs.get('messages', [])
            if messages:
                for msg in messages:
                    if msg.get('role') == 'user':
                        user_query = msg.get('content', 'No content')
                        print(f"Query: '{user_query}'")
                        
                        # Check for typos
                        typos = []
                        if 'citie' in user_query.lower():
                            typos.append('citie → city')
                        if 'bst' in user_query.lower():
                            typos.append('bst → best')
                        if 'performng' in user_query.lower():
                            typos.append('performng → performing')
                        
                        if typos:
                            print(f"⚠️ Detected typos: {', '.join(typos)}")
            
            # Check other inputs
            phone_number = run.inputs.get('phone_number', 'N/A')
            contact_id = run.inputs.get('contact_id', 'N/A')
            print(f"Phone: {phone_number}")
            print(f"Contact: {contact_id}")
        
        # Extract outputs
        print("\n📤 RESPONSE:")
        print("-"*40)
        if run.outputs:
            # Check intent
            intent = run.outputs.get('intent', 'unknown')
            print(f"Intent: {intent}")
            
            # Check if query was corrected
            current_request = run.outputs.get('current_request')
            if current_request and messages:
                original = messages[0].get('content', '')
                if current_request != original:
                    print(f"✅ Query corrected: '{original}' → '{current_request}'")
                else:
                    print(f"❌ No correction applied")
            
            # Check final response
            final_response = run.outputs.get('final_response', '')
            if final_response:
                print(f"\nFinal Response Preview:")
                # Check for city data
                cities = ["brooklyn", "miami", "houston", "chicago", "los angeles"]
                has_city_data = any(city in final_response.lower() for city in cities)
                
                if has_city_data:
                    print("✅ Response contains city performance data")
                    # Show relevant snippets
                    lines = final_response.split('\n')
                    for line in lines[:5]:
                        if any(city in line.lower() for city in cities):
                            print(f"  → {line[:100]}")
                else:
                    print("❌ No city data found in response")
                    print(f"Response: {final_response[:200]}...")
            
            # Check meta response
            meta_response = run.outputs.get('meta_response', {})
            if meta_response:
                if meta_response.get('success'):
                    print("\n✅ Meta agent responded")
                    data = meta_response.get('data', '')
                    if data:
                        data_str = str(data).lower()
                        if 'brooklyn' in data_str or 'miami' in data_str:
                            print("✅ Meta response contains city data")
                        else:
                            print("❌ Meta response missing city data")
        
        # Check for errors
        if run.error:
            print(f"\n❌ ERROR: {run.error}")
        
        # Analyze child runs
        print("\n🔄 EXECUTION FLOW:")
        print("-"*40)
        
        # Try to get project name from environment or use default
        project_name = os.getenv('LANGCHAIN_PROJECT', 'meta-ryan')
        
        try:
            child_runs = list(client.list_runs(
                project_name=project_name,
                filter=f'eq(parent_run_id, "{trace_id}")',
                limit=20
            ))
        except:
            # Fallback: try without filter
            child_runs = []
            print("⚠️ Could not fetch child runs")
        
        if child_runs:
            for i, child in enumerate(child_runs, 1):
                duration = (child.end_time - child.start_time).total_seconds() if child.end_time else 0
                status_icon = "✅" if child.status == "success" else "❌"
                print(f"{i}. {status_icon} {child.name} ({duration:.2f}s)")
                
                # Check for specific issues
                if child.name == "supervisor_graph":
                    if child.outputs:
                        child_intent = child.outputs.get('intent', 'unknown')
                        if child_intent == "unknown":
                            print(f"   ⚠️ Supervisor failed to detect intent")
                        else:
                            print(f"   → Intent: {child_intent}")
                
                if child.name == "process_request":
                    if child.outputs:
                        corrected = child.outputs.get('current_request')
                        if corrected:
                            print(f"   → Corrected to: '{corrected}'")
                
                if child.name == "meta_agent":
                    if child.outputs:
                        meta_data = child.outputs.get('meta_response', {})
                        if meta_data.get('success'):
                            print(f"   → Meta agent succeeded")
                        else:
                            print(f"   ⚠️ Meta agent failed")
                
                if child.error:
                    print(f"   ❌ Error: {child.error}")
        
        # Summary
        print("\n📊 ANALYSIS SUMMARY:")
        print("-"*40)
        
        # Determine issue
        issues = []
        if run.outputs:
            intent = run.outputs.get('intent', 'unknown')
            if intent == 'unknown':
                issues.append("Intent not detected properly")
            
            current_request = run.outputs.get('current_request')
            if messages and current_request:
                original = messages[0].get('content', '')
                if 'citie' in original.lower() and current_request == original:
                    issues.append("Typo not corrected")
            
            final_response = run.outputs.get('final_response', '')
            if final_response and not any(city in final_response.lower() for city in ["brooklyn", "miami", "houston"]):
                if 'city' in str(messages).lower() or 'citie' in str(messages).lower():
                    issues.append("City data not returned despite city query")
        
        if issues:
            print("🔴 Issues Found:")
            for issue in issues:
                print(f"  • {issue}")
        else:
            print("✅ No major issues detected")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        print("-"*40)
        if 'Typo not corrected' in issues:
            print("• Typo correction logic may not be active in deployment")
            print("• Check if supervisor_agent.py changes are deployed")
            print("• Verify IntentAnalyzer class is properly initialized")
        
        if 'City data not returned' in issues:
            print("• Meta agent may not be recognizing city queries")
            print("• Check if meta_campaign_agent.py changes are deployed")
            print("• Verify adset_name field is being requested for city queries")
        
        if 'Intent not detected' in issues:
            print("• Supervisor may be failing to analyze the query")
            print("• Check if the prompt template is working correctly")
            print("• Verify LLM is accessible and responding")
        
        return run
        
    except Exception as e:
        print(f"❌ Error fetching trace: {e}")
        return None

if __name__ == "__main__":
    trace_id = "1f079e2a-6432-6bb6-84da-cbfbd84afcc8"
    run = analyze_trace(trace_id)
    
    if run:
        print("\n" + "="*80)
        print("✅ Trace analysis complete")
        
        # Save full trace for reference
        with open("trace_debug_latest.json", "w") as f:
            trace_data = {
                "trace_id": trace_id,
                "timestamp": str(run.start_time),
                "status": run.status,
                "inputs": run.inputs,
                "outputs": run.outputs,
                "error": run.error
            }
            json.dump(trace_data, f, indent=2, default=str)
            print(f"📄 Full trace saved to trace_debug_latest.json")