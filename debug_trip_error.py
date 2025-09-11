#!/usr/bin/env python3
"""
Debug script to identify trip creation errors
"""
import asyncio
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def debug_trip_creation():
    """Debug trip creation to identify the error"""
    print("Debugging trip creation errors...")
    
    try:
        from agent_service import agent_service, ChatRequest
        
        print("\n=== Test 1: Basic Trip Creation ===")
        try:
            chat_request = ChatRequest(
                message="Create a trip from Jaipur to Kolkata",
                user_id="6257f1d75b42235a2ae4ab34"
            )
            
            # Proper user context with all required fields
            chat_request.user_context = {
                "user_id": "6257f1d75b42235a2ae4ab34",
                "username": "917340224449",
                "name": "Aman yadav",
                "email": "yadavaman2282000@gmail.com",
                "current_company": "62d66794e54f47829a886a1d",
                "user_record": {
                    "_id": "6257f1d75b42235a2ae4ab34",
                    "name": "Aman yadav"
                }
            }
            
            print(f"Sending request: {chat_request.message}")
            print(f"User context: {chat_request.user_context}")
            
            response = await agent_service.process_message(chat_request)
            
            print(f"\nResponse received:")
            print(f"Response: {response.response}")
            print(f"Sources: {response.sources}")
            print(f"Tools used: {response.tools_used}")
            
            # Check for specific error patterns
            if "error" in response.response.lower():
                print(f"\nERROR DETECTED in response!")
            elif "successfully" in response.response.lower():
                print(f"\nSUCCESS: Trip creation appears to have worked")
            else:
                print(f"\nUNCERTAIN: Unclear response")
                
        except Exception as e:
            print(f"EXCEPTION during trip creation: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n=== Test 2: Direct TripCreationAgent Test ===")
        try:
            from agents.trip_creation_agent import TripCreationAgent
            
            trip_agent = TripCreationAgent()
            
            user_context = {
                "user_id": "6257f1d75b42235a2ae4ab34",
                "current_company": "62d66794e54f47829a886a1d",
                "username": "917340224449",
                "name": "Aman yadav",
                "email": "yadavaman2282000@gmail.com"
            }
            
            print(f"Testing TripCreationAgent directly...")
            
            response = await trip_agent.handle_trip_creation_request(
                user_message="Create a trip from Jaipur to Kolkata",
                user_context=user_context
            )
            
            print(f"Direct agent response - Success: {response.success}")
            if response.success:
                print(f"Trip data: {response.data}")
            else:
                print(f"Error: {response.error}")
                
        except Exception as e:
            print(f"EXCEPTION in direct TripCreationAgent test: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n=== Test 3: API Connection Test ===")
        try:
            import httpx
            import base64
            
            # Test API connectivity
            auth_username = os.getenv("PARCEL_API_USERNAME", "917340224449")
            auth_password = os.getenv("PARCEL_API_PASSWORD", "12345")
            
            credentials = f"{auth_username}:{auth_password}"
            credentials_b64 = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {credentials_b64}",
                "Content-Type": "application/json"
            }
            
            # Test trip API endpoint
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                test_url = "https://35.244.19.78:8042/trips"
                print(f"Testing API connection to: {test_url}")
                
                # Try a simple GET request first
                try:
                    response = await client.get(test_url, headers=headers)
                    print(f"GET response status: {response.status_code}")
                    print(f"GET response headers: {dict(response.headers)}")
                    if response.status_code in [200, 401, 403]:
                        print("API endpoint is reachable")
                    else:
                        print(f"Unexpected status code: {response.status_code}")
                        print(f"Response: {response.text[:500]}")
                except Exception as e:
                    print(f"API connection failed: {str(e)}")
                
        except Exception as e:
            print(f"EXCEPTION in API connection test: {str(e)}")
        
        print("\nDebug completed. Check the output above for errors.")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_trip_creation())