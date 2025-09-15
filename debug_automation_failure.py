#!/usr/bin/env python3
"""
Debug automation failure after parcel creation
Helps identify where the consigner/consignee selection automation fails
"""
import asyncio
from backend.agents.agent_manager import AgentManager, WorkflowIntent

async def debug_automation_failure():
    """Debug the automation failure after parcel creation"""

    print("🔍 DEBUGGING AUTOMATION FAILURE")
    print("=" * 60)
    print()

    # Initialize AgentManager
    agent_manager = AgentManager()

    # User data that was working in your logs
    user_data = {
        "user_id": "6257f1d75b42235a2ae4ab34",
        "username": "917340224449",
        "name": "User",
        "email": "",
        "current_company": "62d66794e54f47829a886a1d"
    }

    print("1. 🧪 TESTING DIRECT CONSIGNER/CONSIGNEE FLOW")
    print("-" * 50)

    # Test data similar to what would be passed from parcel creation
    flow_data = {
        "company_id": "62d66794e54f47829a886a1d",
        "trip_id": "68c7f0e0b4858ef89d470a71",
        "parcel_id": "68c7f0e6b4858ef89d470a75",
        "parcel_etag": "test_etag_123",
        "user_context": {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "current_company": "62d66794e54f47829a886a1d",
            "username": "917340224449",
            "name": "User",
            "email": ""
        }
    }

    print(f"Testing with company_id: {flow_data['company_id']}")
    print(f"Trip ID: {flow_data['trip_id']}")
    print(f"Parcel ID: {flow_data['parcel_id']}")
    print()

    try:
        print("2. 🔄 CALLING start_consigner_consignee_flow DIRECTLY")
        print("-" * 50)

        # This is what fails in the automation
        response = await agent_manager.start_consigner_consignee_flow(flow_data)

        print(f"Direct call result - Success: {response.success}")

        if response.success:
            print("✅ Direct call SUCCEEDED!")
            print(f"Data keys: {list(response.data.keys())}")
            partners = response.data.get("partners", [])
            print(f"Partners found: {len(partners)}")

            if partners:
                print("Available partners:")
                for i, partner in enumerate(partners[:3], 1):
                    print(f"  {i}. {partner.get('name')} ({partner.get('city')})")
            else:
                print("No partners in response")

        else:
            print("❌ Direct call FAILED!")
            print(f"Error: {response.error}")

    except Exception as e:
        print(f"❌ EXCEPTION during direct call: {str(e)}")
        import traceback
        traceback.print_exc()

    print()
    print("3. 🔄 TESTING ConsignerConsigneeAgent DIRECTLY")
    print("-" * 50)

    try:
        from backend.agents.base_agent import APIIntent
        consigner_agent = agent_manager.get_agent("consigner_consignee")

        if consigner_agent:
            print("Found ConsignerConsigneeAgent")

            # Test the initialization directly
            init_data = {
                "company_id": "62d66794e54f47829a886a1d",
                "trip_id": "68c7f0e0b4858ef89d470a71",
                "parcel_id": "68c7f0e6b4858ef89d470a75",
                "parcel_etag": "test_etag_123",
                "user_context": flow_data["user_context"]
            }

            agent_response = await consigner_agent.execute(APIIntent.CREATE, init_data)

            print(f"ConsignerConsigneeAgent.execute result - Success: {agent_response.success}")

            if agent_response.success:
                print("✅ ConsignerConsigneeAgent SUCCEEDED!")
                data = agent_response.data
                partners = data.get("partners", [])
                print(f"Partners: {len(partners)}")
                print(f"Message: {data.get('message', 'No message')[:100]}...")
            else:
                print("❌ ConsignerConsigneeAgent FAILED!")
                print(f"Error: {agent_response.error}")
        else:
            print("❌ ConsignerConsigneeAgent not found in agent_manager")

    except Exception as e:
        print(f"❌ EXCEPTION testing ConsignerConsigneeAgent: {str(e)}")
        import traceback
        traceback.print_exc()

    print()
    print("4. 🔄 TESTING PREFERRED PARTNERS API DIRECTLY")
    print("-" * 50)

    try:
        # Test just the preferred partners API call
        consigner_agent = agent_manager.get_agent("consigner_consignee")
        if consigner_agent:
            partners_response = await consigner_agent._get_preferred_partners({
                "company_id": "62d66794e54f47829a886a1d",
                "page": 0,
                "page_size": 5
            })

            print(f"_get_preferred_partners result - Success: {partners_response.success}")

            if partners_response.success:
                partners = partners_response.data.get("partners", [])
                print(f"✅ API call SUCCEEDED! Found {len(partners)} partners")

                for i, partner in enumerate(partners[:3], 1):
                    print(f"  {i}. {partner.get('name', 'No name')} ({partner.get('city', 'No city')})")
            else:
                print("❌ API call FAILED!")
                print(f"Error: {partners_response.error}")

    except Exception as e:
        print(f"❌ EXCEPTION testing API directly: {str(e)}")
        import traceback
        traceback.print_exc()

    print()
    print("🎯 SUMMARY")
    print("-" * 50)
    print("The enhanced logging will now show you exactly where the failure occurs.")
    print("Run your parcel creation flow again and check the logs for:")
    print("• ConsignerConsigneeAgent: _initialize_selection_process calling _get_preferred_partners")
    print("• ConsignerConsigneeAgent: API response success: [true/false]")
    print("• ConsignerConsigneeAgent: Found X raw items from API")
    print("• ConsignerConsigneeAgent: Processed X valid partners for display")

if __name__ == "__main__":
    asyncio.run(debug_automation_failure())