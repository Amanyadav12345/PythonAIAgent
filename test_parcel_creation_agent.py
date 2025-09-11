#!/usr/bin/env python3
"""
Test ParcelCreationAgent directly to verify it works like GeminiService
"""
import asyncio
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from agents.agent_manager import agent_manager, WorkflowIntent
from agents.base_agent import APIIntent

async def test_parcel_creation_agent_directly():
    """Test ParcelCreationAgent using the improved GeminiService-like approach"""
    print("Testing ParcelCreationAgent with GeminiService approach...")
    
    # Step 1: Authentication and setup
    print("\n=== Step 1: Authentication ===")
    username = "917340224449"
    password = "12345"
    
    success, user_info, error = await agent_manager.authenticate_user_and_setup(username, password)
    
    if not success:
        print(f"ERROR: Authentication failed: {error}")
        return
    
    print("SUCCESS: Authentication successful!")
    print(f"User ID: {user_info.get('user_id')}")
    print(f"Current Company: {user_info.get('current_company')}")
    
    # Create complete user context
    user_context = {
        "user_id": user_info.get("user_id"),
        "username": user_info.get("username"),
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "current_company": user_info.get("current_company"),
        "user_record": user_info.get("user_record")
    }
    
    # Step 2: Create trip first (required for parcel creation)
    print("\n=== Step 2: Creating Trip ===")
    
    trip_response = await agent_manager.execute_workflow(
        WorkflowIntent.CREATE_TRIP_ADVANCED,
        {
            "message": "Create trip from Jaipur to Kolkata for aata transport",
            "user_id": user_info.get("user_id"),
            **user_context
        }
    )
    
    if not trip_response.success:
        print(f"ERROR: Trip creation failed: {trip_response.error}")
        return
    
    # Extract trip ID
    trip_id = None
    if trip_response.data:
        trip_result = trip_response.data.get("trip_result", {})
        trip_id = trip_result.get("trip_id")
        if not trip_id:
            trip_id = trip_response.data.get("trip_id")
    
    if not trip_id:
        print(f"ERROR: No trip ID returned: {trip_response.data}")
        return
    
    print(f"SUCCESS: Trip created with ID: {trip_id}")
    
    # Step 3: Test ParcelCreationAgent directly
    print("\n=== Step 3: Testing ParcelCreationAgent Directly ===")
    
    try:
        parcel_creator = agent_manager.agents.get("parcel_creator")
        if not parcel_creator:
            print("ERROR: ParcelCreationAgent not available")
            return
        
        # Test the improved parcel creation method
        test_message = "Create parcel 25kg aata from Jaipur to Kolkata"
        
        parcel_response = await parcel_creator.handle_parcel_creation_request(
            user_message=test_message,
            user_context=user_context,
            trip_id=trip_id
        )
        
        if parcel_response.success:
            print("SUCCESS: ParcelCreationAgent created parcel successfully!")
            print(f"Parcel ID: {parcel_response.data.get('parcel_id')}")
            print(f"Trip ID: {parcel_response.data.get('trip_id')}")
            print(f"Message: {parcel_response.data.get('message', '').replace('📦', 'PARCEL')}")
            
            # Show identification details
            identification = parcel_response.data.get('identification_result', {})
            print(f"\nIdentification Results:")
            print(f"  From City: {identification.get('from_city', {}).get('name')} (ID: {identification.get('from_city', {}).get('id')})")
            print(f"  To City: {identification.get('to_city', {}).get('name')} (ID: {identification.get('to_city', {}).get('id')})")
            print(f"  Material: {identification.get('material', {}).get('name')} (ID: {identification.get('material', {}).get('id')})")
            print(f"  Quantity: {identification.get('quantity', {}).get('value')} {identification.get('quantity', {}).get('unit')}")
            print(f"  Notes: {identification.get('parsing_notes', 'N/A')}")
        else:
            print(f"ERROR: ParcelCreationAgent failed: {parcel_response.error}")
            # Show suggestions if available
            if hasattr(parcel_response, 'data') and parcel_response.data:
                suggestions = parcel_response.data.get('suggestions', {})
                if suggestions:
                    print("City suggestions available:")
                    for key, cities in suggestions.items():
                        print(f"  {key}: {[c['name'] for c in cities[:3]]}")
                        
    except Exception as e:
        print(f"ERROR: Exception during parcel creation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_parcel_creation_agent_directly())