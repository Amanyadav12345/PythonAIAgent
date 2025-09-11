#!/usr/bin/env python3
"""
Test the actual chat endpoint flow that might cause ObjectId validation error
"""
import asyncio
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_chat_endpoint_simulation():
    """Test simulating the chat endpoint flow"""
    print("Testing chat endpoint simulation for ObjectId validation...")
    
    # Step 1: Simulate what main.py chat endpoint does
    print("\n=== Step 1: Simulating Main.py Chat Flow ===")
    
    try:
        # Import the agent service and chat models 
        from agent_service import agent_service, ChatRequest
        
        # Create a test user (simulating FastAPI user dependency)
        class TestUser:
            username = "917340224449"
        
        current_user = TestUser()
        
        # Step 2: Get authenticated user info like main.py does
        from agents.agent_manager import agent_manager
        auth_agent = agent_manager.get_agent("auth")
        user_info = None
        if auth_agent and auth_agent.is_user_authenticated(current_user.username):
            user_info = auth_agent.get_user_info(current_user.username)
        else:
            print("User not authenticated - authenticating now...")
            success, user_info, error = await agent_manager.authenticate_user_and_setup("917340224449", "12345")
            if not success:
                print(f"ERROR: Authentication failed: {error}")
                return
        
        print(f"User info from auth: {user_info}")
        
        # Step 3: Create chat request like main.py does
        chat_request = ChatRequest(
            message="Create trip and parcel 25kg aata from Jaipur to Kolkata",
            user_id=current_user.username  # This might be the issue!
        )
        
        # Add user context like main.py does (UPDATED LOGIC)
        if user_info:
            # user_info already contains the auth data including user_record
            user_record = user_info.get("user_record")
            user_id = user_info.get("user_id")  # This is the real ObjectId from auth
            
            if user_record and user_id:
                # Use data from user_record when available
                chat_request.user_id = user_id  # Use real ObjectId
                chat_request.user_context = {
                    "user_id": user_id,
                    "username": current_user.username,
                    "name": user_record.get("name"),
                    "email": user_record.get("email"),
                    "current_company": user_record.get("current_company"),
                    "user_record": user_record
                }
            else:
                # Use direct auth data as fallback (this handles the case where user_record is None)
                chat_request.user_id = user_id or current_user.username
                chat_request.user_context = {
                    "user_id": user_id or current_user.username,
                    "username": current_user.username,
                    "name": user_info.get("name"),
                    "email": user_info.get("email"), 
                    "current_company": user_info.get("current_company"),
                    "user_record": user_record
                }
        else:
            # Fallback to username if no authenticated user data
            chat_request.user_id = current_user.username
            chat_request.user_context = {
                "user_id": current_user.username,
                "username": current_user.username
            }
        
        print(f"Chat request user_id: {chat_request.user_id}")
        print(f"Chat request user_context: {chat_request.user_context}")
        
        # Step 4: Process message through agent service
        print("\n=== Step 2: Processing Through Agent Service ===")
        
        response = await agent_service.process_message(chat_request)
        
        print(f"Chat response type: {type(response)}")
        print(f"Chat response success: {getattr(response, 'success', 'No success field')}")
        
        # Handle unicode characters by encoding to ASCII
        response_text = getattr(response, 'response', 'No response field')
        if isinstance(response_text, str):
            response_text = response_text.encode('ascii', 'ignore').decode('ascii')
        print(f"Chat response text: {response_text}")
        
        # Check for errors
        error_msg = getattr(response, 'error', None)
        if error_msg:
            if isinstance(error_msg, str):
                error_msg = error_msg.encode('ascii', 'ignore').decode('ascii')
            print(f"Chat response error: {error_msg}")
        
        # Show detailed response for debugging
        if hasattr(response, '__dict__'):
            print("Response attributes:")
            for key, value in response.__dict__.items():
                if isinstance(value, str):
                    value = value.encode('ascii', 'ignore').decode('ascii')
                print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"ERROR: Exception during chat endpoint simulation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chat_endpoint_simulation())