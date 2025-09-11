#!/usr/bin/env python3
"""
Test the exact Gemini workflow that caused the ObjectId validation error
"""
import asyncio
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from agents.agent_manager import agent_manager
from agents.base_agent import APIIntent

async def test_gemini_workflow_objectid_error():
    """Test the exact Gemini workflow that should cause ObjectId validation error"""
    print("Testing Gemini workflow that caused ObjectId validation error...")
    
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
    
    # Step 2: Test the EXACT enhanced_trip_and_parcel_creation workflow
    print("\n=== Step 2: Testing Enhanced Gemini Workflow ===")
    
    try:
        # Use the enhanced Gemini service workflow (the one that was causing errors)
        from gemini_service import gemini_service
        
        test_message = "Create trip and parcel 25kg aata from Jaipur to Kolkata"
        response = await gemini_service.enhanced_trip_and_parcel_creation(
            test_message,
            user_context
        )
        
        if response.get("success"):
            print("SUCCESS: Gemini trip and parcel creation successful!")
            print(f"Trip ID: {response.get('trip_id')}")
            print(f"Parcel ID: {response.get('parcel_id')}")
            message = response.get('message', '').replace('✅', 'SUCCESS')
            print(f"Message: {message}")
        else:
            print(f"ERROR: Gemini workflow failed: {response.get('error')}")
            if "suggestions" in response:
                print("City suggestions available:")
                for key, cities in response["suggestions"].items():
                    print(f"  {key}: {[c['name'] for c in cities[:3]]}")
                        
    except Exception as e:
        print(f"ERROR: Exception during Gemini workflow: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gemini_workflow_objectid_error())