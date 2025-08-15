#!/usr/bin/env python3
"""Simple test for typo correction in supervisor agent"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.supervisor_agent import SupervisorAgent
from unittest.mock import MagicMock

def test_typo_correction():
    """Test that the supervisor correctly handles typos"""
    
    print("🧪 Testing Typo Correction in Supervisor Agent")
    print("="*60)
    
    # Create supervisor instance
    supervisor = SupervisorAgent()
    
    # Test queries with typos
    test_cases = [
        ("Which is the best citie", "meta", "Which is the best city"),
        ("wat is the bst performing city", "meta", "what is the best performing city"),
        ("show me brookln sales", "meta", "show me brooklyn sales"),
        ("hw many sales", "meta", "how many sales"),
        ("best performng location", "meta", "best performing location"),
    ]
    
    for original, expected_intent, expected_correction in test_cases:
        print(f"\n📝 Testing: '{original}'")
        print("-"*40)
        
        # Create mock state
        state = {
            "messages": [{"role": "user", "content": original}],
            "phone_number": "+13054870475",
            "contact_id": "test_123",
            "current_request": original,
            "intent": None,
            "language": "en"
        }
        
        try:
            # Process the state
            result = supervisor.process_request(state)
            
            # Check intent
            intent = result.get("intent", "unknown")
            print(f"✓ Intent detected: {intent}")
            
            if intent == expected_intent:
                print(f"✅ Correct intent: {expected_intent}")
            else:
                print(f"❌ Wrong intent: got {intent}, expected {expected_intent}")
            
            # Check correction
            corrected = result.get("current_request", original)
            if corrected != original:
                print(f"✅ Query corrected: '{original}' → '{corrected}'")
                if corrected.lower() == expected_correction.lower():
                    print(f"✅ Correction matches expected: '{expected_correction}'")
            else:
                print(f"⚠️ No correction applied")
            
            # Check confidence
            confidence = result.get("confidence", 0)
            print(f"Confidence: {confidence:.2f}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "="*60)
    print("✅ Test Complete")

if __name__ == "__main__":
    test_typo_correction()