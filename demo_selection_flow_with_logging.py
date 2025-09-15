#!/usr/bin/env python3
"""
Demo: UI Selection Flow with Enhanced Backend Storage and Logging
Shows the complete flow: Select Consigner → Store & Log → Select Consignee → Store & Log → Run ParcelUpdateAgent
"""
import asyncio
import json
from backend.agents.consigner_consignee_agent import ConsignerConsigneeAgent
from backend.agents.agent_manager import AgentManager
from backend.agents.base_agent import APIIntent

async def demo_ui_selection_flow():
    """Demo the complete UI selection flow with enhanced logging"""

    print("🚀 DEMO: UI SELECTION FLOW WITH BACKEND STORAGE & LOGGING")
    print("=" * 80)
    print()

    # Initialize AgentManager and ConsignerConsigneeAgent
    agent_manager = AgentManager()

    # Sample data (as would come from UI after parcel creation)
    parcel_data = {
        "company_id": "62d66794e54f47829a886a1d",
        "parcel_id": "68c7e9c3116d262e3a714d16",
        "parcel_etag": "b1234567890abcdef",  # From parcel creation
        "trip_id": "68c7e9bd2ab2a82fa4f58ae5",
        "user_context": {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "current_company": "62d66794e54f47829a886a1d",
            "username": "917340224449",
            "name": "Test User"
        }
    }

    try:
        print("1. 🏁 INITIALIZING CONSIGNER/CONSIGNEE SELECTION FLOW")
        print("-" * 60)

        # Start the selection flow
        flow_response = await agent_manager.start_consigner_consignee_flow(parcel_data)

        if not flow_response.success:
            print(f"❌ Flow initialization failed: {flow_response.error}")
            return

        print("✅ Flow initialized successfully")
        print(f"📋 Available partners: {len(flow_response.data.get('partners', []))}")
        print()

        # Get available partners
        partners = flow_response.data.get("partners", [])
        if not partners:
            print("❌ No partners available for selection")
            return

        print("2. 👤 UI USER SELECTS CONSIGNER")
        print("-" * 60)
        print("Available partners from /preferred_partners API:")
        for i, partner in enumerate(partners[:3], 1):
            print(f"  {i}. {partner['name']} ({partner['city']})")
        print()

        # Simulate user selecting first consigner
        selected_consigner = partners[0]
        print(f"🎯 UI Selection: User selects #{1} - {selected_consigner['name']}")
        print()

        consigner_selection = {
            "selection_type": "consigner",
            "partner_id": selected_consigner["id"],
            "partner_name": selected_consigner["name"]
        }

        print("3. 💾 STORING CONSIGNER DATA IN BACKEND")
        print("-" * 60)

        consigner_response = await agent_manager.handle_consigner_consignee_selection(consigner_selection)

        if not consigner_response.success:
            print(f"❌ Consigner selection failed: {consigner_response.error}")
            return

        if consigner_response.data.get("action") != "consigner_selected":
            print(f"❌ Unexpected consigner response: {consigner_response.data.get('action')}")
            return

        print("✅ Consigner data stored in backend successfully!")
        print("📝 Check logs above for detailed storage information")
        print()

        print("4. 📦 UI USER SELECTS CONSIGNEE")
        print("-" * 60)
        print("Same /preferred_partners API - showing partners again:")
        for i, partner in enumerate(partners[:3], 1):
            status = "(Same as Consigner)" if partner['id'] == selected_consigner['id'] else ""
            print(f"  {i}. {partner['name']} ({partner['city']}) {status}")
        print()

        # Simulate user selecting consignee (different from consigner if possible)
        selected_consignee = partners[1] if len(partners) > 1 else partners[0]
        selection_num = 2 if len(partners) > 1 else 1
        print(f"🎯 UI Selection: User selects #{selection_num} - {selected_consignee['name']}")
        print()

        consignee_selection = {
            "selection_type": "consignee",
            "partner_id": selected_consignee["id"],
            "partner_name": selected_consignee["name"]
        }

        print("5. 💾 STORING CONSIGNEE DATA IN BACKEND")
        print("-" * 60)

        consignee_response = await agent_manager.handle_consigner_consignee_selection(consignee_selection)

        if not consignee_response.success:
            print(f"❌ Consignee selection failed: {consignee_response.error}")
            return

        print("✅ Consignee data stored in backend successfully!")
        print("📝 Check logs above for detailed storage information")
        print()

        # Check if ParcelUpdateAgent was triggered
        action = consignee_response.data.get("action")
        if action == "selection_complete_and_parcel_updated":
            print("6. 🚀 PARCEL UPDATE AGENT EXECUTED AUTOMATICALLY")
            print("-" * 60)
            print("✅ ParcelUpdateAgent was triggered automatically after both selections")
            print("✅ PATCH API executed with stored _etag")
            print("✅ Parcel updated successfully with consigner/consignee details")
            print()

            # Show final results
            final_data = consignee_response.data.get("final_data", {})
            update_result = consignee_response.data.get("update_result", {})

            print("📊 FINAL BACKEND STORAGE SUMMARY")
            print("-" * 60)
            print(f"Parcel ID: {final_data.get('parcel_id')}")
            print(f"Trip ID: {final_data.get('trip_id')}")
            print(f"Original _etag: {final_data.get('parcel_etag')}")
            print(f"New _etag: {update_result.get('_etag', 'N/A')}")
            print(f"Stored Consigner: {final_data.get('consigner_details', {}).get('name')}")
            print(f"Stored Consignee: {final_data.get('consignee_details', {}).get('name')}")
            print()

            print("🎉 COMPLETE FLOW SUCCESS!")
            print("=" * 80)
            print("✅ 1. Consigner selected on UI → Stored in backend with logs")
            print("✅ 2. Consignee selected on UI → Stored in backend with logs")
            print("✅ 3. ParcelUpdateAgent automatically triggered")
            print("✅ 4. PATCH API executed successfully")
            print("=" * 80)

        elif action == "selection_complete_update_failed":
            print("6. ⚠️ SELECTIONS STORED BUT UPDATE FAILED")
            print("-" * 60)
            print("✅ Both selections stored in backend successfully")
            print(f"❌ ParcelUpdateAgent execution failed: {consignee_response.data.get('update_error')}")
            print("💡 Data is stored and ready for manual API retry")

        else:
            print("6. ℹ️ SELECTIONS STORED - READY FOR MANUAL TRIGGER")
            print("-" * 60)
            print("✅ Both selections stored in backend successfully")
            print("💡 ParcelUpdateAgent can be triggered manually if needed")

    except Exception as e:
        print(f"❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

async def show_backend_storage_structure():
    """Show the backend storage structure"""

    print("\n" + "=" * 80)
    print("📋 BACKEND STORAGE STRUCTURE")
    print("=" * 80)
    print()

    print("ConsignerConsigneeAgent.selection_data:")
    print("-" * 40)
    storage_structure = {
        "consigner": {
            "id": "partner_id_from_preferred_partners_api",
            "name": "Partner Name",
            "city": "City Name",
            "company_info": "Company Information"
        },
        "consignee": {
            "id": "partner_id_from_preferred_partners_api",
            "name": "Partner Name",
            "city": "City Name",
            "company_info": "Company Information"
        },
        "parcel_id": "68c7e9c3116d262e3a714d16",
        "trip_id": "68c7e9bd2ab2a82fa4f58ae5",
        "parcel_etag": "b1234567890abcdef",
        "current_step": "completed",
        "user_context": {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "current_company": "62d66794e54f47829a886a1d"
        }
    }

    print(json.dumps(storage_structure, indent=2))
    print()

    print("🔄 WORKFLOW SUMMARY:")
    print("-" * 40)
    print("1. UI sends consigner selection → Stored in backend → Logs generated")
    print("2. UI sends consignee selection → Stored in backend → Logs generated")
    print("3. Backend automatically triggers → ParcelUpdateAgent.execute()")
    print("4. PATCH /parcels/{parcel_id} → With If-Match: {_etag}")
    print("5. Parcel updated with complete consigner/consignee data")

if __name__ == "__main__":
    print("🧪 Running UI selection flow demo with enhanced logging...")

    # Run the demo
    asyncio.run(demo_ui_selection_flow())

    # Show storage structure
    asyncio.run(show_backend_storage_structure())