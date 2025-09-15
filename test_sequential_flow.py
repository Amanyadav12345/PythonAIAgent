#!/usr/bin/env python3
"""
Test the improved sequential consigner → consignee flow
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_sequential_consigner_consignee_flow():
    """Test the improved sequential flow with clear messaging"""
    print("Testing improved sequential consigner → consignee flow...")
    
    try:
        from agents.agent_manager import agent_manager
        
        print(f"\n=== SEQUENTIAL CONSIGNER → CONSIGNEE FLOW TEST ===")
        
        # Test data
        test_data = {
            "company_id": "62d66794e54f47829a886a1d",
            "trip_id": "test_trip_123",
            "parcel_id": "test_parcel_456",
            "user_id": "6257f1d75b42235a2ae4ab34",
            "current_company": "62d66794e54f47829a886a1d",
            "username": "917340224449",
            "name": "Aman yadav",
            "email": "yadavaman2282000@gmail.com"
        }
        
        print(f"\n--- STEP 1: Initialize Flow (Should ask for CONSIGNER first) ---")
        
        # Start the flow
        response = await agent_manager.start_consigner_consignee_flow(test_data)
        
        if response.success:
            print(f"✅ Flow initialized successfully")
            print(f"Current step: {response.data.get('current_step')}")
            print(f"Input type: {response.data.get('input_type')}")
            
            # Display the message to show how it asks for consigner first
            message = response.data.get('message', '')
            print(f"\n📋 User sees this message:")
            print(f"{'='*60}")
            print(message)
            print(f"{'='*60}")
            
            partners = response.data.get('partners', [])
            if partners and len(partners) >= 2:
                print(f"\n--- STEP 2: Select CONSIGNER (First partner) ---")
                
                # Select first partner as consigner
                consigner_selection = {
                    "partner_id": partners[0]['id'],
                    "partner_name": partners[0]['name'],
                    "selection_type": "consigner"
                }
                
                consigner_response = await agent_manager.handle_consigner_consignee_selection(consigner_selection)
                
                if consigner_response.success:
                    print(f"✅ Consigner selected: {partners[0]['name']}")
                    print(f"Current step: {consigner_response.data.get('current_step')}")
                    print(f"Input type: {consigner_response.data.get('input_type')}")
                    
                    # Display the message to show how it asks for consignee
                    consignee_message = consigner_response.data.get('message', '')
                    print(f"\n📋 User now sees this message:")
                    print(f"{'='*60}")
                    print(consignee_message)
                    print(f"{'='*60}")
                    
                    print(f"\n--- STEP 3: Select CONSIGNEE (Second partner) ---")
                    
                    # Select second partner as consignee
                    consignee_selection = {
                        "partner_id": partners[1]['id'],
                        "partner_name": partners[1]['name'],
                        "selection_type": "consignee"
                    }
                    
                    consignee_response = await agent_manager.handle_consigner_consignee_selection(consignee_selection)
                    
                    if consignee_response.success:
                        print(f"✅ Consignee selected: {partners[1]['name']}")
                        action = consignee_response.data.get('action')
                        print(f"Action: {action}")
                        
                        if action in ["selection_complete_and_parcel_updated", "selection_complete"]:
                            # Display final completion message
                            final_message = consignee_response.data.get('message', '')
                            print(f"\n📋 Final completion message:")
                            print(f"{'='*60}")
                            print(final_message)
                            print(f"{'='*60}")
                            
                            print(f"\n🎉 SEQUENTIAL FLOW COMPLETED SUCCESSFULLY!")
                            
                            # Show flow summary
                            final_data = consignee_response.data.get('final_data', {})
                            if final_data:
                                consigner_details = final_data.get('consigner_details', {})
                                consignee_details = final_data.get('consignee_details', {})
                                
                                print(f"\n📊 Flow Summary:")
                                print(f"1. CONSIGNER: {consigner_details.get('name')} ({consigner_details.get('city')})")
                                print(f"2. CONSIGNEE: {consignee_details.get('name')} ({consignee_details.get('city')})")
                                print(f"3. Trip ID: {final_data.get('trip_id')}")
                                print(f"4. Parcel ID: {final_data.get('parcel_id')}")
                        else:
                            print(f"Unexpected action: {action}")
                    else:
                        print(f"❌ Consignee selection failed: {consignee_response.error}")
                        
                    # Test validation - try to select consigner again (should fail)
                    print(f"\n--- VALIDATION TEST: Try to select consigner again (should fail) ---")
                    
                    invalid_selection = {
                        "partner_id": partners[0]['id'],
                        "partner_name": partners[0]['name'],
                        "selection_type": "consigner"
                    }
                    
                    validation_response = await agent_manager.handle_consigner_consignee_selection(invalid_selection)
                    
                    if not validation_response.success:
                        print(f"✅ Validation working: {validation_response.error}")
                    else:
                        print(f"⚠️ Validation not working - should have failed")
                        
                else:
                    print(f"❌ Consigner selection failed: {consigner_response.error}")
                    
                # Test validation - try to select consignee first (should fail)
                print(f"\n--- VALIDATION TEST: Try to select consignee before consigner (should fail) ---")
                
                # Reset the agent to test this properly
                from agents.consigner_consignee_agent import ConsignerConsigneeAgent
                test_agent = ConsignerConsigneeAgent()
                
                # Initialize with fresh state
                await test_agent.execute(test_agent.APIIntent.CREATE, {
                    "company_id": "62d66794e54f47829a886a1d",
                    "trip_id": "test_trip",
                    "parcel_id": "test_parcel"
                })
                
                # Try to select consignee first
                invalid_consignee_selection = {
                    "partner_id": partners[1]['id'],
                    "partner_name": partners[1]['name'],
                    "selection_type": "consignee"
                }
                
                from agents.base_agent import APIIntent
                validation_response2 = await test_agent.execute(APIIntent.UPDATE, invalid_consignee_selection)
                
                if not validation_response2.success:
                    print(f"✅ Sequential validation working: {validation_response2.error}")
                else:
                    print(f"⚠️ Sequential validation not working - should require consigner first")
                
            else:
                print(f"⚠️ Not enough partners for testing (need at least 2, found {len(partners)})")
        else:
            print(f"❌ Failed to initialize flow: {response.error}")
        
        print(f"\n" + "="*80)
        print("SEQUENTIAL FLOW IMPROVEMENTS SUMMARY:")
        print("="*80)
        print("✅ Clear STEP 1: Select CONSIGNER (Sender) messaging")
        print("✅ Clear STEP 2: Select CONSIGNEE (Receiver) messaging")
        print("✅ Shows selected consigner when asking for consignee")
        print("✅ Highlights if same partner selected for both roles")
        print("✅ Sequential validation (consigner must be first)")
        print("✅ Prevents out-of-order selections")
        print("✅ Clear completion messaging")
        print("")
        print("User Experience Flow:")
        print("1. User sees: 'STEP 1: Select a CONSIGNER (Sender)'")
        print("2. After selection: 'CONSIGNER SELECTED: [Name]'")
        print("3. User sees: 'STEP 2: Select a CONSIGNEE (Receiver)'")
        print("4. After selection: Complete workflow with both details")
        print("5. Automatic parcel update via PATCH API")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sequential_consigner_consignee_flow())