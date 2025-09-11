#!/usr/bin/env python3
"""
Test the complete authentication and parcel creation flow
"""
import asyncio
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from agents.agent_manager import agent_manager
from agents.base_agent import APIIntent

async def test_authentication_and_parcel_creation():
    """Test complete flow from authentication to parcel creation"""
    print("Testing authentication and parcel creation flow...")
    
    # Step 1: Test authentication 
    print("\n=== Step 1: Authentication ===")
    username = "917340224449"
    password = "12345"
    
    success, user_info, error = await agent_manager.authenticate_user_and_setup(username, password)
    
    if success:
        print("SUCCESS: Authentication successful!")
        print(f"User ID: {user_info.get('user_id')}")
        print(f"Username: {user_info.get('username')}")
        print(f"Name: {user_info.get('name')}")
        print(f"Email: {user_info.get('email')}")
        print(f"Current Company: {user_info.get('current_company')}")
        
        # Step 2: Create user context for parcel creation
        user_context = {
            "user_id": user_info.get("user_id"),
            "username": user_info.get("username"),
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "current_company": user_info.get("current_company"),
            "user_record": user_info.get("user_record")
        }
        
        print(f"\nUser context created:")
        print(f"- user_id (ObjectId): {user_context['user_id']}")
        print(f"- current_company (ObjectId): {user_context['current_company']}")
        print(f"- name: {user_context['name']}")
        
        # Step 3: Test parcel creation workflow with proper user context
        print("\n=== Step 2: Testing Parcel Creation with Authentication ===")
        
        try:
            # Use the enhanced Gemini service workflow
            from gemini_service import gemini_service
            
            test_message = "Create trip and parcel 25kg aata from Jaipur to Kolkata"
            response = await gemini_service.enhanced_trip_and_parcel_creation(
                test_message,
                user_context
            )
            
            if response.get("success"):
                print("SUCCESS: Trip and parcel creation successful!")
                print(f"Message: {response.get('message', '')}")
                
                # Extract details
                if "trip_id" in response:
                    print(f"Trip ID: {response['trip_id']}")
                if "parcel_id" in response:
                    print(f"Parcel ID: {response['parcel_id']}")
                    
            else:
                print(f"ERROR: Trip and parcel creation failed: {response.get('error')}")
                if "suggestions" in response:
                    print("City suggestions available:")
                    for key, cities in response["suggestions"].items():
                        print(f"  {key}: {[c['name'] for c in cities[:3]]}")
                        
        except Exception as e:
            print(f"ERROR: Exception during parcel creation: {str(e)}")
            import traceback
            traceback.print_exc()
        
    else:
        print(f"ERROR: Authentication failed: {error}")

if __name__ == "__main__":
    asyncio.run(test_authentication_and_parcel_creation())