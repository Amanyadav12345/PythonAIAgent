#!/usr/bin/env python3
"""
Test the exact error you're experiencing with trip creation
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_current_trip_error():
    """Test the current trip creation error"""
    print("Testing the current trip creation to reproduce the error...")
    
    try:
        from agent_service import agent_service, ChatRequest
        
        # Create a ChatRequest exactly as your frontend would send it
        chat_request = ChatRequest(
            message="Create a trip from Delhi to Mumbai",
            user_id="6257f1d75b42235a2ae4ab34"
        )
        
        # Simulate frontend request without current_company
        chat_request.user_context = {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "username": "917340224449", 
            "name": "Aman yadav",
            "email": "yadavaman2282000@gmail.com",
            # Note: current_company is NOT included to test the static fallback
        }
        
        print(f"Request: {chat_request.message}")
        print(f"User context: {chat_request.user_context}")
        
        response = await agent_service.process_message(chat_request)
        
        print(f"\nResponse: {response.response}")
        print(f"Tools used: {response.tools_used}")
        
        if "Failed to create trip33" in response.response:
            print("ERROR: Trip creation failed")
            print(f"Error response: {response.response}")
            return False
        elif "Successfully created trip" in response.response:
            print("SUCCESS: Trip creation worked")
            return True
        else:
            print("UNKNOWN: Unclear response")
            print(f"Response: {response.response}")
            return False
            
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_current_trip_error())
    if success:
        print("\nTrip creation is working correctly!")
    else:
        print("\nTrip creation is failing - need to investigate further")