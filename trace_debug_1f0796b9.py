#!/usr/bin/env python3
"""
Deep trace analysis for 1f0796b9-5706-61e7-8b8c-52c843c07969
"""

import os
from dotenv import load_dotenv
load_dotenv()

from langsmith import Client

def analyze_trace():
    client = Client()
    trace_id = "1f0796b9-5706-61e7-8b8c-52c843c07969"
    
    print("="*100)
    print(f"TRACE ANALYSIS: {trace_id}")
    print("="*100)
    
    # Get the run
    run = client.read_run(trace_id)
    
    print(f"\nRun Name: {run.name}")
    print(f"Status: {run.status}")
    print(f"Run Type: {run.run_type}")
    print(f"Start Time: {run.start_time}")
    print(f"End Time: {run.end_time}")
    
    # Check inputs
    print("\n" + "="*50)
    print("INPUTS:")
    print("="*50)
    if run.inputs:
        import json
        print(json.dumps(run.inputs, indent=2, default=str))
    
    # Check outputs
    print("\n" + "="*50)
    print("OUTPUTS:")
    print("="*50)
    if run.outputs:
        import json
        print(json.dumps(run.outputs, indent=2, default=str))
    
    # Get child runs
    print("\n" + "="*50)
    print("CHILD RUNS:")
    print("="*50)
    
    # Get project name from the run
    project_name = None
    if hasattr(run, 'project_name'):
        project_name = run.project_name
    else:
        # Try to get from session
        try:
            project = client.read_project(project_id=run.session_id)
            project_name = project.name
        except:
            project_name = "campaign-report-agent"  # Fallback to default
    
    child_runs = list(client.list_runs(
        project_name=project_name,
        filter=f'eq(parent_run_id, "{trace_id}")',
        limit=100
    ))
    
    for i, child in enumerate(child_runs):
        print(f"\n{i+1}. {child.name}")
        print(f"   Type: {child.run_type}")
        print(f"   Status: {child.status}")
        
        # Look for specific nodes
        if "meta" in child.name.lower() or "analyze" in child.name.lower():
            print(f"   📊 META/ANALYZE NODE FOUND")
            if child.inputs:
                print(f"   Inputs: {json.dumps(child.inputs, indent=6, default=str)[:500]}")
            if child.outputs:
                print(f"   Outputs: {json.dumps(child.outputs, indent=6, default=str)[:500]}")
        
        if "query" in child.name.lower() or "sdk" in child.name.lower():
            print(f"   🔍 QUERY/SDK NODE FOUND")
            if child.inputs:
                inputs_str = json.dumps(child.inputs, indent=6, default=str)
                # Look for date_preset
                if "date_preset" in inputs_str or "today" in inputs_str:
                    print(f"   ⚠️ Contains date_preset or 'today'")
                    print(f"   Full inputs: {inputs_str[:1000]}")
            if child.outputs:
                outputs_str = json.dumps(child.outputs, indent=6, default=str)
                # Check for data
                if "impressions" in outputs_str or "spend" in outputs_str:
                    print(f"   ✅ Contains data (impressions/spend)")
                    # Extract numbers
                    import re
                    impressions = re.findall(r'"impressions"\s*:\s*"?(\d+)"?', outputs_str)
                    spend = re.findall(r'"spend"\s*:\s*"?([\d.]+)"?', outputs_str)
                    if impressions:
                        print(f"   Impressions found: {impressions[:5]}")
                    if spend:
                        print(f"   Spend found: {spend[:5]}")
        
        # Check tool calls
        if child.run_type == "tool":
            print(f"   🔧 TOOL CALL")
            if child.inputs:
                print(f"   Tool inputs: {json.dumps(child.inputs, indent=6, default=str)[:500]}")
            if child.outputs:
                outputs_str = json.dumps(child.outputs, indent=6, default=str)
                if len(outputs_str) > 500:
                    print(f"   Tool outputs (truncated): {outputs_str[:500]}...")
                else:
                    print(f"   Tool outputs: {outputs_str}")
    
    # Look for specific patterns
    print("\n" + "="*50)
    print("PATTERN ANALYSIS:")
    print("="*50)
    
    # Check all runs for date_preset handling
    date_preset_found = False
    today_found = False
    data_returned = False
    
    for child in child_runs:
        if child.inputs:
            inputs_str = str(child.inputs)
            if "date_preset" in inputs_str:
                date_preset_found = True
                if "today" in inputs_str:
                    today_found = True
                    print(f"\n📍 'today' found in {child.name}")
                    print(f"   Full context: {inputs_str[:300]}")
        
        if child.outputs:
            outputs_str = str(child.outputs)
            if "impressions" in outputs_str and '"impressions": "0"' not in outputs_str:
                data_returned = True
                print(f"\n📊 Data returned in {child.name}")
                print(f"   Sample: {outputs_str[:300]}")
    
    print("\n" + "="*50)
    print("DIAGNOSIS:")
    print("="*50)
    print(f"Date preset found: {date_preset_found}")
    print(f"'Today' query found: {today_found}")
    print(f"Data returned: {data_returned}")
    
    if today_found and not data_returned:
        print("\n⚠️ ISSUE: 'today' was requested but no data returned")
    elif not today_found:
        print("\n⚠️ ISSUE: 'today' was not properly passed through the system")
    elif data_returned:
        print("\n✅ Data was returned, check if it's being processed correctly")

if __name__ == "__main__":
    analyze_trace()