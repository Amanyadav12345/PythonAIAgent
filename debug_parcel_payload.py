#!/usr/bin/env python3
"""
Debug parcel payload to see what user context is actually being passed
"""
import asyncio
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from agents.agent_manager import agent_manager, WorkflowIntent
from agents.base_agent import APIIntent

async def debug_parcel_payload():
    """Debug what user context is actually passed to parcel creation"""
    print("Debugging parcel payload user context...")
    
    # Step 1: Authentication and setup
    print("\n=== Step 1: Authentication ===")
    username = "917340224449"
    password = "12345"
    
    success, user_info, error = await agent_manager.authenticate_user_and_setup(username, password)
    
    if not success:
        print(f"ERROR: Authentication failed: {error}")
        return
    
    print("SUCCESS: Authentication successful!")
    print(f"Raw user_info from auth: {user_info}")
    
    # Create complete user context
    user_context = {
        "user_id": user_info.get("user_id"),
        "username": user_info.get("username"),
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "current_company": user_info.get("current_company"),
        "user_record": user_info.get("user_record")
    }
    
    print(f"\nUser context created: {user_context}")
    print(f"User ID type: {type(user_context['user_id'])}")
    print(f"Current Company type: {type(user_context['current_company'])}")
    
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
    
    # Step 3: Debug parcel creation workflow data
    print("\n=== Step 3: Testing Workflow Data ===")
    
    # Check what data is passed to CREATE_PARCEL_FOR_TRIP workflow
    parcel_creation_data = {
        "message": "Create parcel 25kg aata from Jaipur to Kolkata",
        "user_id": user_info.get("user_id"),
        "trip_id": trip_id,
        "from_city_id": "61421aa1de5cb316d9ba55c0",  # Jaipur
        "to_city_id": "61421a9fde5cb316d9ba5547",   # Kolkata
        "material_type": "aata",
        "quantity": 25,
        "quantity_unit": "KILOGRAMS",
        "cost": 200000,
        **user_context
    }
    
    print(f"Parcel creation data being sent to workflow: {parcel_creation_data}")
    print(f"Data includes user_id: {parcel_creation_data.get('user_id')}")
    print(f"Data includes current_company: {parcel_creation_data.get('current_company')}")
    
    # Step 4: Execute workflow and capture detailed response
    print("\n=== Step 4: Executing Parcel Creation Workflow ===")
    
    try:
        parcel_response = await agent_manager.execute_workflow(
            WorkflowIntent.CREATE_PARCEL_FOR_TRIP,
            parcel_creation_data
        )
        
        print(f"Parcel workflow response success: {parcel_response.success}")
        print(f"Parcel workflow response error: {parcel_response.error}")
        if hasattr(parcel_response, 'data') and parcel_response.data:
            print(f"Parcel ID: {parcel_response.data.get('parcel_id')}")
            print(f"Trip ID: {parcel_response.data.get('trip_id')}")
            message = parcel_response.data.get('message', '').replace('📦', 'PARCEL')
            print(f"Message: {message}")
            print(f"Response data keys: {list(parcel_response.data.keys())}")
        
    except Exception as e:
        print(f"ERROR: Exception during parcel workflow: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_parcel_payload())