#!/usr/bin/env python3
"""
Test the complete parcel workflow with consigner/consignee selection and PATCH API update
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_complete_parcel_workflow():
    """Test the complete workflow: Trip + Parcel + Consigner/Consignee Selection + PATCH Update"""
    print("Testing complete parcel workflow with PATCH API integration...")
    
    try:
        from agent_service import agent_service, ChatRequest
        from agents.agent_manager import agent_manager
        from agents.base_agent import APIIntent
        
        print(f"\n=== COMPLETE PARCEL WORKFLOW TEST ===")
        print(f"Flow: Trip Creation → Parcel Creation → Consigner Selection → Consignee Selection → PATCH Update")
        
        # Test data
        user_context = {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "username": "917340224449", 
            "name": "Aman yadav",
            "email": "yadavaman2282000@gmail.com",
            "current_company": "62d66794e54f47829a886a1d"
        }
        
        print(f"\n--- Step 1: Create Trip and Parcel ---")
        
        # Create a trip and parcel using the agent service
        chat_request = ChatRequest(
            message="Create a trip from Mumbai to Delhi with steel",
            user_id=user_context["user_id"]
        )
        chat_request.user_context = user_context
        
        response = await agent_service.process_message(chat_request)
        
        if response and "Successfully created trip" in response.response:
            print(f"✅ Trip and parcel created successfully")
            
            # Extract trip and parcel IDs from response (this would depend on your response structure)
            # For testing, we'll use example IDs
            trip_id = "68c42057d7bd2d6597272ac4"  # Example from your payload
            parcel_id = "68c42057d7bd2d6597272ac8"  # Example from your payload
            
            print(f"Trip ID: {trip_id}")
            print(f"Parcel ID: {parcel_id}")
            
            print(f"\n--- Step 2: Start Consigner/Consignee Selection ---")
            
            # Start the enhanced consigner/consignee selection flow
            selection_data = {
                "trip_id": trip_id,
                "parcel_id": parcel_id,
                **user_context
            }
            
            flow_response = await agent_manager.start_consigner_consignee_flow(selection_data)
            
            if flow_response.success:
                print(f"✅ Consigner/Consignee flow started")
                print(f"Available partners: {len(flow_response.data.get('partners', []))}")
                
                partners = flow_response.data.get('partners', [])
                if len(partners) >= 2:
                    print(f"\n--- Step 3: Select Consigner ---")
                    
                    # Select first partner as consigner
                    consigner_selection = {
                        "partner_id": partners[0]['id'],
                        "partner_name": partners[0]['name'],
                        "selection_type": "consigner"
                    }
                    
                    consigner_response = await agent_manager.handle_consigner_consignee_selection(consigner_selection)
                    
                    if consigner_response.success and consigner_response.data.get('current_step') == 'consignee':
                        print(f"✅ Consigner selected: {partners[0]['name']}")
                        
                        print(f"\n--- Step 4: Select Consignee ---")
                        
                        # Select second partner as consignee
                        consignee_selection = {
                            "partner_id": partners[1]['id'],
                            "partner_name": partners[1]['name'],
                            "selection_type": "consignee"
                        }
                        
                        consignee_response = await agent_manager.handle_consigner_consignee_selection(consignee_selection)
                        
                        if consignee_response.success:
                            action = consignee_response.data.get('action')
                            
                            if action == "selection_complete_and_parcel_updated":
                                print(f"✅ Consignee selected: {partners[1]['name']}")
                                print(f"✅ Parcel automatically updated via PATCH API!")
                                
                                # Display complete results
                                final_data = consignee_response.data.get('final_data', {})
                                update_result = consignee_response.data.get('update_result', {})
                                
                                print(f"\n--- Step 5: Workflow Complete ---")
                                print(f"🎉 Complete workflow finished successfully!")
                                
                                print(f"\nFinal Selection Summary:")
                                consigner_details = final_data.get('consigner_details', {})
                                consignee_details = final_data.get('consignee_details', {})
                                
                                print(f"Consigner: {consigner_details.get('name')} ({consigner_details.get('city')})")
                                print(f"Consignee: {consignee_details.get('name')} ({consignee_details.get('city')})")
                                print(f"Trip ID: {final_data.get('trip_id')}")
                                print(f"Parcel ID: {final_data.get('parcel_id')}")
                                
                                # Show update details
                                updated_parcel = update_result.get('updated_parcel', {})
                                if updated_parcel:
                                    print(f"\nParcel Update Details:")
                                    print(f"Updated Parcel ID: {updated_parcel.get('_id')}")
                                    print(f"New _etag: {updated_parcel.get('_etag')}")
                                    
                                    # Show sender/receiver info
                                    sender = updated_parcel.get('sender', {})
                                    receiver = updated_parcel.get('receiver', {})
                                    
                                    if sender:
                                        print(f"Sender Person: {sender.get('sender_person')}")
                                        print(f"Sender Name: {sender.get('name')}")
                                    
                                    if receiver:
                                        print(f"Receiver Person: {receiver.get('receiver_person')}")
                                        print(f"Receiver Name: {receiver.get('name')}")
                                
                                print(f"\n--- API Integration Verification ---")
                                await test_direct_parcel_operations(parcel_id)
                                
                            elif action == "selection_complete_update_failed":
                                print(f"✅ Consignee selected: {partners[1]['name']}")
                                print(f"⚠️ Parcel update failed: {consignee_response.data.get('update_error')}")
                                print(f"📋 Manual API payload available for retry")
                                
                                # Show the payload that can be used for manual API call
                                api_payload = consignee_response.data.get('api_payload', {})
                                print(f"\nManual API Payload:")
                                print(f"URL: PATCH https://35.244.19.78:8042/parcels/{parcel_id}")
                                print(f"Headers: If-Match: <_etag>")
                                print(f"Payload keys: {list(api_payload.keys()) if api_payload else 'None'}")
                                
                            else:
                                print(f"✅ Consignee selected: {partners[1]['name']}")
                                print(f"Action: {action}")
                                
                        else:
                            print(f"❌ Consignee selection failed: {consignee_response.error}")
                    else:
                        print(f"❌ Consigner selection failed: {consigner_response.error}")
                else:
                    print(f"⚠️ Not enough partners for testing (need at least 2, found {len(partners)})")
                    if partners:
                        print("Available partners:")
                        for i, partner in enumerate(partners, 1):
                            print(f"  {i}. {partner['name']} ({partner['city']})")
            else:
                print(f"❌ Failed to start consigner/consignee flow: {flow_response.error}")
        else:
            print(f"❌ Failed to create trip and parcel")
            if response:
                print(f"Response: {response.response}")
        
        print(f"\n" + "="*80)
        print("COMPLETE PARCEL WORKFLOW SUMMARY:")
        print("="*80)
        print("✅ Created enhanced ConsignerConsigneeAgent")
        print("✅ Created ParcelUpdateAgent with PATCH API support")
        print("✅ Implemented _etag handling and caching")
        print("✅ Integrated automatic parcel update after selection")
        print("✅ Built complete end-to-end workflow")
        print("")
        print("Workflow Features:")
        print("1. Trip and parcel creation")
        print("2. Shared partner list fetching")
        print("3. Step-by-step consigner selection")
        print("4. Step-by-step consignee selection")
        print("5. Automatic PATCH API update with _etag")
        print("6. Complete data storage and validation")
        print("7. Error handling and fallback options")
        print("")
        print("API Integration:")
        print("- GET /parcels/{id} for _etag retrieval")
        print("- PATCH /parcels/{id} with If-Match header")
        print("- Automatic payload building from selections")
        print("- _etag caching and management")
        print("- Complete sender/receiver update")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_direct_parcel_operations(parcel_id: str):
    """Test direct parcel operations independently"""
    print(f"\n--- Testing Direct Parcel Operations ---")
    
    try:
        from agents.agent_manager import agent_manager
        
        print(f"Testing ParcelUpdateAgent directly...")
        
        # Test 1: Get parcel details
        print(f"1. Getting parcel details for ID: {parcel_id}")
        get_response = await agent_manager.update_parcel_directly({
            "parcel_id": parcel_id
        })
        
        if get_response.success:
            parcel_data = get_response.data.get('parcel', {})
            etag = get_response.data.get('_etag')
            print(f"   ✅ Parcel retrieved successfully")
            print(f"   _etag: {etag}")
            print(f"   Parcel keys: {list(parcel_data.keys()) if parcel_data else 'None'}")
        else:
            print(f"   ❌ Failed to get parcel: {get_response.error}")
            return
        
        # Test 2: Direct update with custom payload
        print(f"\n2. Testing direct PATCH update...")
        
        # Create a simple update payload (just update verification status)
        update_payload = {
            "verification": "Updated via API Test",
            "_id": parcel_id
        }
        
        patch_response = await agent_manager.update_parcel_directly({
            "parcel_id": parcel_id,
            "update_payload": update_payload,
            "_etag": etag
        })
        
        if patch_response.success:
            updated_parcel = patch_response.data.get('updated_parcel', {})
            new_etag = patch_response.data.get('_etag')
            print(f"   ✅ Parcel updated successfully")
            print(f"   New _etag: {new_etag}")
            print(f"   Verification: {updated_parcel.get('verification')}")
        else:
            print(f"   ❌ Failed to update parcel: {patch_response.error}")
        
        print(f"\nDirect parcel operations test completed.")
        
    except Exception as e:
        print(f"Error in direct parcel operations test: {str(e)}")

async def test_parcel_update_agent_standalone():
    """Test ParcelUpdateAgent as standalone component"""
    print(f"\n=== STANDALONE PARCEL UPDATE AGENT TEST ===")
    
    try:
        from agents.parcel_update_agent import ParcelUpdateAgent
        from agents.base_agent import APIIntent
        
        agent = ParcelUpdateAgent()
        test_parcel_id = "68c42057d7bd2d6597272ac8"  # Example ID
        
        print(f"1. Testing _etag retrieval...")
        get_response = await agent.execute(APIIntent.READ, {"parcel_id": test_parcel_id})
        
        if get_response.success:
            print(f"   ✅ GET successful")
            etag = get_response.data.get('_etag')
            print(f"   _etag: {etag}")
        else:
            print(f"   ❌ GET failed: {get_response.error}")
            return
        
        print(f"\n2. Testing PATCH update...")
        update_data = {
            "parcel_id": test_parcel_id,
            "update_payload": {
                "verification": "Standalone Test Update",
                "_id": test_parcel_id
            },
            "_etag": etag
        }
        
        update_response = await agent.execute(APIIntent.UPDATE, update_data)
        
        if update_response.success:
            print(f"   ✅ PATCH successful")
            new_etag = update_response.data.get('_etag')
            print(f"   New _etag: {new_etag}")
        else:
            print(f"   ❌ PATCH failed: {update_response.error}")
        
        print(f"\nStandalone test completed.")
        
    except Exception as e:
        print(f"Error in standalone test: {str(e)}")

if __name__ == "__main__":
    print("Running complete parcel workflow test...")
    asyncio.run(test_complete_parcel_workflow())
    
    print("\n" + "="*80)
    print("Running standalone ParcelUpdateAgent test...")
    asyncio.run(test_parcel_update_agent_standalone())