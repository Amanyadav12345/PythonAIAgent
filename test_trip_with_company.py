#!/usr/bin/env python3
"""
Test trip creation with proper current_company in user_context
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_trip_with_company():
    """Test trip creation with current_company in user_context"""
    print("Testing trip creation with proper current_company...")
    
    try:
        from agent_service import agent_service, ChatRequest
        
        # Create a ChatRequest with proper user_context including current_company
        chat_request = ChatRequest(
            message="Create a trip from Mumbai to Delhi",
            user_id="6257f1d75b42235a2ae4ab34"
        )
        
        # This is the key - make sure user_context includes current_company
        chat_request.user_context = {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "username": "917340224449", 
            "name": "Aman yadav",
            "email": "yadavaman2282000@gmail.com",
            "current_company": "62d66794e54f47829a886a1d",  # This is crucial!
            "user_record": {
                "_id": "6257f1d75b42235a2ae4ab34",
                "name": "Aman yadav"
            }
        }
        
        print(f"Request: {chat_request.message}")
        print(f"User context: {chat_request.user_context}")
        print(f"Current company: {chat_request.user_context.get('current_company')}")
        
        response = await agent_service.process_message(chat_request)
        
        print(f"\nResponse: {response.response}")
        print(f"Success: {'success' in response.response.lower() or 'created' in response.response.lower()}")
        print(f"Tools used: {response.tools_used}")
        
        if "error" in response.response.lower():
            print("❌ ERROR: Trip creation failed")
        else:
            print("✅ SUCCESS: Trip creation worked")
            
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_trip_with_company())