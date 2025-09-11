"""
Authentication Example - Demonstrates the authentication workflow
Shows how to authenticate users and use the credentials for API operations
"""
import asyncio
import json
from dotenv import load_dotenv

from agent_manager import agent_manager, WorkflowIntent
from base_agent import APIIntent

load_dotenv()

async def example_authentication_workflow():
    """Example: Complete authentication workflow"""
    print("\n🔐 AUTHENTICATION WORKFLOW EXAMPLE")
    print("=" * 50)
    
    # Test credentials (replace with actual credentials)
    test_credentials = {
        "username": "917340224449",  # From the example API call
        "password": "12345"          # From the example API call
    }
    
    print(f"Testing authentication with username: {test_credentials['username']}")
    
    # Step 1: Authenticate user and setup all agents
    print("\n1. Authenticating user...")
    success, user_info, error = await agent_manager.authenticate_user_and_setup(
        test_credentials["username"], 
        test_credentials["password"]
    )
    
    if success:
        print("✅ Authentication successful!")
        print(f"   User ID: {user_info.get('user_id')}")
        print(f"   Name: {user_info.get('name')}")
        print(f"   Email: {user_info.get('email')}")
        print(f"   User Type: {user_info.get('user_type')}")
        print(f"   Current Company: {user_info.get('current_company')}")
        print(f"   Roles: {', '.join(user_info.get('role_names', []))}")
        print(f"   Token: {user_info.get('token')}")
        
        # Step 2: Test API operations with authenticated credentials
        print("\n2. Testing API operations with authenticated credentials...")
        await test_authenticated_operations()
        
    else:
        print(f"❌ Authentication failed: {error}")

async def example_direct_auth_agent():
    """Example: Direct authentication agent usage"""
    print("\n🔧 DIRECT AUTH AGENT EXAMPLE")
    print("=" * 50)
    
    # Test authentication directly with auth agent
    auth_response = await agent_manager.execute_single_intent(
        "auth", APIIntent.VALIDATE, {
            "username": "917340224449",
            "password": "12345"
        }
    )
    
    print(f"Direct auth result: {auth_response.success}")
    
    if auth_response.success and auth_response.data:
        auth_data = auth_response.data
        print("\nAuthentication Details:")
        print(f"   Authenticated: {auth_data.get('authenticated')}")
        print(f"   Token: {auth_data.get('token')}")
        print(f"   Auth Header: {auth_data.get('auth_header')}")
        print(f"   User ID: {auth_data.get('user_id')}")
        print(f"   Username: {auth_data.get('username')}")
        print(f"   Name: {auth_data.get('name')}")
        print(f"   Status: {auth_data.get('status_text')}")
        
        # Show user record details
        user_record = auth_data.get('user_record', {})
        if user_record:
            print("\nUser Record Details:")
            print(f"   Phone: {user_record.get('phone', {}).get('number')}")
            print(f"   Email: {user_record.get('email')}")
            print(f"   Company: {user_record.get('current_company')}")
            print(f"   Individual Type: {user_record.get('individual_user_type')}")
            print(f"   User Type: {user_record.get('user_type')}")
            print(f"   Roles: {len(user_record.get('roles', []))} role(s)")
    else:
        print(f"❌ Direct authentication failed: {auth_response.error}")

async def test_authenticated_operations():
    """Test various API operations after authentication"""
    print("\n📋 TESTING AUTHENTICATED OPERATIONS")
    print("-" * 40)
    
    # Test 1: Search cities (should work with authenticated credentials)
    print("🏙️  Testing city search...")
    city_response = await agent_manager.execute_single_intent(
        "city", APIIntent.SEARCH, {"city_name": "Jaipur"}
    )
    print(f"   City search result: {city_response.success}")
    if not city_response.success:
        print(f"   Error: {city_response.error}")
    
    # Test 2: Search materials (should work with authenticated credentials)
    print("\n🧱 Testing material search...")
    material_response = await agent_manager.execute_single_intent(
        "material", APIIntent.SEARCH, {"material_name": "paint"}
    )
    print(f"   Material search result: {material_response.success}")
    if not material_response.success:
        print(f"   Error: {material_response.error}")
    
    # Test 3: Create trip (should work with authenticated credentials)
    print("\n🚛 Testing trip creation...")
    trip_response = await agent_manager.execute_single_intent(
        "trip", APIIntent.CREATE, {}
    )
    print(f"   Trip creation result: {trip_response.success}")
    if trip_response.success and trip_response.data:
        trip_id = trip_response.data.get("extracted_trip_id")
        print(f"   Created trip ID: {trip_id}")
    else:
        print(f"   Error: {trip_response.error}")

async def example_auth_workflow_integration():
    """Example: How authentication integrates with other workflows"""
    print("\n🔄 AUTH INTEGRATION WITH OTHER WORKFLOWS")
    print("=" * 50)
    
    # Step 1: Authenticate
    print("1. Authenticating user...")
    auth_success, user_info, auth_error = await agent_manager.authenticate_user_and_setup(
        "917340224449", "12345"
    )
    
    if not auth_success:
        print(f"❌ Authentication failed: {auth_error}")
        return
    
    print("✅ Authentication successful!")
    
    # Step 2: Use authenticated session for parcel creation workflow
    print("\n2. Creating parcel with authenticated session...")
    parcel_data = {
        "from_city": "Jaipur",
        "to_city": "Kolkata",
        "material": "paint",
        "weight": 25,
        "description": "Authenticated parcel creation test",
        "sender_name": user_info.get("name", "Default Sender"),
        "receiver_name": "Test Receiver"
    }
    
    parcel_response = await agent_manager.execute_workflow(
        WorkflowIntent.CREATE_PARCEL, parcel_data
    )
    
    print(f"   Parcel creation result: {parcel_response.success}")
    
    if parcel_response.success:
        print("✅ Parcel created successfully with authenticated session!")
    else:
        print(f"❌ Parcel creation failed: {parcel_response.error}")

async def example_auth_cache_management():
    """Example: Authentication cache management"""
    print("\n💾 AUTHENTICATION CACHE MANAGEMENT")
    print("=" * 50)
    
    auth_agent = agent_manager.get_agent("auth")
    if not auth_agent:
        print("❌ Auth agent not available")
        return
    
    # Authenticate and check cache
    print("1. Authenticating and caching user...")
    auth_response = await agent_manager.execute_single_intent(
        "auth", APIIntent.VALIDATE, {
            "username": "917340224449",
            "password": "12345"
        }
    )
    
    if auth_response.success:
        username = "917340224449"
        print(f"✅ User {username} authenticated and cached")
        
        # Check if user is in cache
        print(f"\n2. Checking cache status...")
        is_cached = auth_agent.is_user_authenticated(username)
        print(f"   User in cache: {is_cached}")
        
        # Get cached user info
        if is_cached:
            cached_info = auth_agent.get_user_info(username)
            print(f"   Cached token: {cached_info.get('token')[:20]}...")
            print(f"   Cached auth header: {cached_info.get('auth_header')[:30]}...")
        
        # Test reading cached user
        print(f"\n3. Reading cached user data...")
        read_response = await agent_manager.execute_single_intent(
            "auth", APIIntent.READ, {"user_id": auth_response.data.get("user_id")}
        )
        print(f"   Read cached user result: {read_response.success}")
        
        # Logout user (clear cache)
        print(f"\n4. Logging out user (clearing cache)...")
        logout_success = auth_agent.logout_user(username)
        print(f"   Logout result: {logout_success}")
        
        # Verify cache is cleared
        is_still_cached = auth_agent.is_user_authenticated(username)
        print(f"   User still in cache: {is_still_cached}")

async def main():
    """Run all authentication examples"""
    print("🔐 AUTHENTICATION SYSTEM EXAMPLES")
    print("=" * 50)
    
    # Note about environment setup
    print("📝 ENVIRONMENT SETUP:")
    print("   Make sure to set AUTH_API_URL=https://35.244.19.78:8042 in your .env file")
    print("   Replace test credentials with actual ones\n")
    
    # Run examples
    await example_authentication_workflow()
    await example_direct_auth_agent()
    await example_auth_workflow_integration() 
    await example_auth_cache_management()
    
    print("\n✅ All authentication examples completed!")

if __name__ == "__main__":
    asyncio.run(main())