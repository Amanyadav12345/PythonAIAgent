#!/usr/bin/env python3
"""
Test trip creation WITHOUT current_company in user_context to verify static fallback works
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_trip_without_company():
    """Test trip creation without current_company in user_context (should use static fallback)"""
    print("Testing trip creation WITHOUT current_company (using static fallback)...")
    
    try:
        from agent_service import agent_service, ChatRequest
        
        # Create a ChatRequest WITHOUT current_company in user_context
        chat_request = ChatRequest(
            message="Create a trip from Chennai to Bangalore",
            user_id="6257f1d75b42235a2ae4ab34"
        )
        
        # This is the key - user_context does NOT include current_company
        chat_request.user_context = {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "username": "917340224449", 
            "name": "Aman yadav",
            "email": "yadavaman2282000@gmail.com",
            # NOTE: current_company is NOT included - should fallback to static value
            "user_record": {
                "_id": "6257f1d75b42235a2ae4ab34",
                "name": "Aman yadav"
            }
        }
        
        print(f"Request: {chat_request.message}")
        print(f"User context: {chat_request.user_context}")
        print(f"Current company in context: {chat_request.user_context.get('current_company', 'NOT PROVIDED')}")
        
        response = await agent_service.process_message(chat_request)
        
        print(f"\nResponse: {response.response}")
        print(f"Success: {'success' in response.response.lower() or 'created' in response.response.lower()}")
        print(f"Tools used: {response.tools_used}")
        
        if "error" in response.response.lower():
            print("❌ ERROR: Trip creation failed")
            return False
        elif "failed" in response.response.lower():
            print("❌ ERROR: Trip creation failed")  
            return False
        else:
            print("SUCCESS: Trip creation worked with static current_company fallback")
            return True
            
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_trip_without_company())
    if success:
        print("\n✅ Static current_company fallback is working correctly!")
    else:
        print("\n❌ Static current_company fallback failed!")