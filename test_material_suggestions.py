#!/usr/bin/env python3
"""
Test material search with suggestions - showing how it works for parcel creation
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_material_suggestions():
    """Test material search suggestions workflow"""
    print("Testing material suggestions workflow for parcel creation...")
    
    try:
        from agents.agent_manager import agent_manager
        from agents.base_agent import APIIntent
        
        # Simulate user typing different material names
        test_scenarios = [
            {
                "user_input": "iron bar",  # Should suggest " Iron Bars"
                "expected": "suggestions"
            },
            {
                "user_input": "Iron Bars",  # Should find exact match
                "expected": "exact"
            },
            {
                "user_input": "cement",     # Should find exact or suggest
                "expected": "any"
            },
            {
                "user_input": "wood",       # Should find suggestions like "Wooden Boxes", etc.
                "expected": "suggestions"  
            },
            {
                "user_input": "xyz123",     # Should find nothing
                "expected": "none"
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            user_input = scenario["user_input"]
            expected = scenario["expected"]
            
            print(f"\n=== Scenario {i}: User types '{user_input}' ===")
            
            try:
                response = await agent_manager.execute_single_intent(
                    "material", APIIntent.SEARCH, {"material_name": user_input}
                )
                
                if response.success and response.data:
                    data = response.data
                    match_type = data.get("match_type")
                    materials = data.get("materials", [])
                    message = data.get("message", "")
                    
                    if match_type == "exact":
                        material = materials[0]
                        print(f"✅ EXACT MATCH: {material['name']}")
                        print(f"   Material ID: {material['id']}")
                        print(f"   State: {material.get('state')}, Hazard: {material.get('hazard')}")
                        print(f"   → Use this ID ({material['id']}) in parcel creation")
                        
                    elif match_type == "partial":
                        print(f"🤔 SUGGESTIONS NEEDED: {message}")
                        print(f"   Found {len(materials)} suggestions:")
                        for j, material in enumerate(materials, 1):
                            similarity = material.get('similarity', 0)
                            print(f"   {j}. {material['name']} (ID: {material['id']}) - {similarity:.0%} match")
                        print(f"   → Ask user: 'Did you mean one of these materials?'")
                        
                        # Simulate user choosing the first suggestion
                        if materials:
                            chosen = materials[0]
                            print(f"   💡 If user chooses '{chosen['name']}':")
                            print(f"      → Use ID {chosen['id']} in parcel creation")
                        
                    elif match_type == "none":
                        print(f"❌ NO MATCHES: {message}")
                        print(f"   → Ask user to check spelling or choose from available materials")
                        
                else:
                    # API call failed
                    data = response.data if response.data else {}
                    match_type = data.get("match_type")
                    materials = data.get("materials", [])
                    message = data.get("message", response.error)
                    
                    if match_type == "none":
                        print(f"❌ NO MATCHES: {message}")
                        print(f"   → Ask user to check spelling or try different material name")
                    else:
                        print(f"❌ SEARCH FAILED: {message}")
                        
            except Exception as e:
                print(f"❌ Exception: {str(e)}")
        
        print(f"\n" + "="*60)
        print("INTEGRATION WITH PARCEL CREATION:")
        print("="*60)
        print("1. User types material name")
        print("2. MaterialAgent searches and returns:")
        print("   - EXACT MATCH → Use material ID directly") 
        print("   - SUGGESTIONS → Show options, user picks one")
        print("   - NO MATCH → Ask user to try again")
        print("3. Pass chosen material ID to ParcelCreationAgent")
        print("4. Create parcel with proper material_type field")
        
    except Exception as e:
        print(f"ERROR: CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_material_suggestions())