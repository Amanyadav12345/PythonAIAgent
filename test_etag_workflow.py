#!/usr/bin/env python3
"""
Test _etag workflow for parcel PATCH operations
Demonstrates how _etag is passed from parcel creation through ConsignerConsigneeAgent to ParcelUpdateAgent
"""
import asyncio
import json
from backend.agents.consigner_consignee_agent import ConsignerConsigneeAgent
from backend.agents.parcel_update_agent import ParcelUpdateAgent
from backend.agents.base_agent import APIIntent

async def test_etag_workflow():
    """Test the complete _etag workflow"""

    # Sample parcel data with _etag (as received from parcel creation)
    parcel_creation_response = {
        "_id": "68c7e9c3116d262e3a714d16",
        "_etag": "b1234567890abcdef",  # This would come from POST response
        "material_type": "615ee88a221119aee3eac64c",
        "quantity": 25,
        "quantity_unit": "TONNES",
        "description": "Steel 25 ton",
        "cost": 200031,
        "part_load": False,
        "verification": "Verified",
        "created_by": "6257f1d75b42235a2ae4ab34",
        "created_by_company": "62d66794e54f47829a886a1d",
        "trip_id": "68c7e9bd2ab2a82fa4f58ae5"
    }

    print("=== ETAG WORKFLOW TEST ===")
    print(f"1. Parcel created with _etag: {parcel_creation_response['_etag']}")
    print(f"   Parcel ID: {parcel_creation_response['_id']}")
    print()

    # Initialize ConsignerConsigneeAgent
    consigner_agent = ConsignerConsigneeAgent()

    print("2. Initializing ConsignerConsigneeAgent with parcel data including _etag...")

    # Initialize selection process with _etag
    init_data = {
        "company_id": "62d66794e54f47829a886a1d",
        "parcel_id": parcel_creation_response["_id"],
        "parcel_etag": parcel_creation_response["_etag"],  # Pass _etag from creation
        "trip_id": parcel_creation_response["trip_id"],
        "user_context": {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "current_company": "62d66794e54f47829a886a1d"
        }
    }

    try:
        # Initialize selection process
        init_response = await consigner_agent.execute(APIIntent.CREATE, init_data)

        if init_response.success:
            print(f"   ✅ Selection process initialized")
            print(f"   Stored _etag: {consigner_agent.selection_data['parcel_etag']}")
            print()

            # Simulate consigner selection
            print("3. Selecting consigner...")

            # Get partners from the response to simulate selection
            partners = init_response.data.get("partners", [])
            if partners:
                selected_consigner = partners[0]  # Select first partner

                consigner_selection_data = {
                    "selection_type": "consigner",
                    "partner_id": selected_consigner["id"],
                    "partner_name": selected_consigner["name"]
                }

                consigner_response = await consigner_agent.execute(APIIntent.UPDATE, consigner_selection_data)

                if consigner_response.success:
                    print(f"   ✅ Consigner selected: {selected_consigner['name']}")
                    print()

                    # Simulate consignee selection
                    print("4. Selecting consignee...")

                    # Select second partner as consignee (or same if only one)
                    selected_consignee = partners[1] if len(partners) > 1 else partners[0]

                    consignee_selection_data = {
                        "selection_type": "consignee",
                        "partner_id": selected_consignee["id"],
                        "partner_name": selected_consignee["name"]
                    }

                    consignee_response = await consigner_agent.execute(APIIntent.UPDATE, consignee_selection_data)

                    if consignee_response.success:
                        print(f"   ✅ Consignee selected: {selected_consignee['name']}")
                        print()

                        # Get final data for parcel update
                        final_data = consignee_response.data.get("final_data", {})
                        print(f"5. Final data prepared with _etag: {final_data.get('parcel_etag')}")
                        print()

                        # Initialize ParcelUpdateAgent and perform update
                        print("6. Updating parcel with selected consigner/consignee...")

                        parcel_agent = ParcelUpdateAgent()

                        update_data = {
                            "parcel_id": final_data["parcel_id"],
                            "final_data": final_data
                        }

                        # This would normally be called through agent chain
                        update_response = await parcel_agent.execute(APIIntent.CREATE, update_data)

                        if update_response.success:
                            print("   ✅ Parcel updated successfully!")
                            print(f"   New _etag: {update_response.data.get('update_result', {}).get('_etag', 'Not available')}")
                            print()
                            print("=== WORKFLOW COMPLETED SUCCESSFULLY ===")

                            # Show the complete PATCH payload structure
                            print("\n7. PATCH Request Structure:")
                            print("   URL: https://35.244.19.78:8042/parcels/{parcel_id}")
                            print("   Method: PATCH")
                            print("   Headers:")
                            print(f"     If-Match: {final_data.get('parcel_etag')}")
                            print("     Content-Type: application/json")
                            print("   Payload: (Complete parcel data with updated sender/receiver)")

                        else:
                            print(f"   ❌ Parcel update failed: {update_response.error}")
                    else:
                        print(f"   ❌ Consignee selection failed: {consignee_response.error}")
                else:
                    print(f"   ❌ Consigner selection failed: {consigner_response.error}")
            else:
                print("   ❌ No partners available for selection")
        else:
            print(f"   ❌ Selection process initialization failed: {init_response.error}")

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

async def demonstrate_etag_usage():
    """Demonstrate how to properly use _etag in the workflow"""

    print("\n=== ETAG USAGE GUIDE ===")
    print()
    print("1. PARCEL CREATION:")
    print("   POST https://35.244.19.78:8042/parcels")
    print("   Response includes: {'_id': 'parcel_id', '_etag': 'etag_value', ...}")
    print()
    print("2. STORE _ETAG:")
    print("   ConsignerConsigneeAgent.selection_data['parcel_etag'] = response['_etag']")
    print()
    print("3. PASS _ETAG TO UPDATE:")
    print("   final_data = {'parcel_etag': stored_etag, 'parcel_id': parcel_id, ...}")
    print("   ParcelUpdateAgent receives final_data with _etag")
    print()
    print("4. PATCH REQUEST:")
    print("   PATCH https://35.244.19.78:8042/parcels/{parcel_id}")
    print("   Headers: {'If-Match': etag_value}")
    print("   Body: {complete_parcel_payload}")
    print()
    print("5. UPDATE RESPONSE:")
    print("   Response includes new _etag for subsequent updates")
    print()
    print("KEY POINTS:")
    print("- _etag prevents race conditions")
    print("- Must be included in If-Match header for PATCH")
    print("- New _etag returned after successful update")
    print("- _etag flows: Creation → Selection → Update")

if __name__ == "__main__":
    print("Testing _etag workflow...")
    asyncio.run(test_etag_workflow())
    asyncio.run(demonstrate_etag_usage())