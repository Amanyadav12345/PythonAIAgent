#!/usr/bin/env python3
"""
Test material search functionality with the updated MaterialAgent
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_material_search():
    """Test material search with various inputs"""
    print("Testing MaterialAgent search functionality...")
    
    try:
        from agents.agent_manager import agent_manager
        from agents.base_agent import APIIntent
        
        # Test cases - different material searches
        test_cases = [
            "iron",           # Should find "Iron Bars"
            "Iron Bars",      # Should find exact match
            "bamboo",         # Should find "Bamboo" 
            "biscuits",       # Should find "Biscuits"
            "steel",          # Should find suggestions or no match
            "boxes",          # Should find "Box" as suggestion
        ]
        
        for i, search_term in enumerate(test_cases, 1):
            print(f"\n=== Test {i}: Searching for '{search_term}' ===")
            
            try:
                response = await agent_manager.execute_single_intent(
                    "material", APIIntent.SEARCH, {"material_name": search_term}
                )
                
                if response.success:
                    data = response.data
                    match_type = data.get("match_type", "unknown")
                    materials = data.get("materials", [])
                    
                    print(f"SUCCESS: Search successful - Match type: {match_type}")
                    
                    if match_type == "exact":
                        material = materials[0]
                        print(f"   Exact match found: {material['name']} (ID: {material['id']})")
                        print(f"   State: {material.get('state')}, Hazard: {material.get('hazard')}")
                        
                    elif match_type == "partial" and materials:
                        print(f"   Found {len(materials)} suggestions:")
                        for j, material in enumerate(materials[:3], 1):  # Show top 3
                            similarity = material.get('similarity', 0)
                            print(f"   {j}. {material['name']} (ID: {material['id']}) - Similarity: {similarity:.2f}")
                            
                    elif match_type == "none":
                        print(f"   No materials found for '{search_term}'")
                        
                else:
                    print(f"ERROR: Search failed: {response.error}")
                    
            except Exception as e:
                print(f"ERROR: Exception during search: {str(e)}")
        
        print("\n=== Material List Test ===")
        try:
            # Test listing all materials
            response = await agent_manager.execute_single_intent(
                "material", APIIntent.LIST, {}
            )
            
            if response.success and response.data:
                # Check if we got materials data
                if isinstance(response.data, dict) and "_items" in response.data:
                    total_materials = len(response.data["_items"])
                    print(f"SUCCESS: Successfully retrieved {total_materials} materials from API")
                    
                    # Show first few materials
                    for i, material in enumerate(response.data["_items"][:5], 1):
                        print(f"   {i}. {material.get('name', 'Unknown')} (ID: {material.get('_id', 'Unknown')})")
                else:
                    print("ERROR: Unexpected response format for material list")
            else:
                print(f"ERROR: Failed to list materials: {response.error if response else 'Unknown error'}")
                
        except Exception as e:
            print(f"ERROR: Exception during material list: {str(e)}")
            
    except Exception as e:
        print(f"ERROR: CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_material_search())