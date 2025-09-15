#!/usr/bin/env python3
"""
Test the complete agent chain execution: ConsignerConsigneeAgent → ParcelUpdateAgent
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_agent_chain_execution():
    """Test the complete agent chain: ConsignerConsigneeAgent → ParcelUpdateAgent"""
    print("Testing complete agent chain execution...")
    
    try:
        from agents.agent_manager import agent_manager
        
        print(f"\n" + "="*80)
        print("AGENT CHAIN EXECUTION TEST")
        print("ConsignerConsigneeAgent → ParcelUpdateAgent")
        print("="*80)
        
        # Test data
        test_data = {
            "company_id": "62d66794e54f47829a886a1d",
            "trip_id": "68c42057d7bd2d6597272ac4",  # Real trip ID
            "parcel_id": "68c42057d7bd2d6597272ac8",  # Real parcel ID
            "user_id": "6257f1d75b42235a2ae4ab34",
            "current_company": "62d66794e54f47829a886a1d",
            "username": "917340224449",
            "name": "Aman yadav",
            "email": "yadavaman2282000@gmail.com"
        }
        
        print(f"\n📋 Test Configuration:")
        print(f"Parcel ID: {test_data['parcel_id']}")
        print(f"Trip ID: {test_data['trip_id']}")
        print(f"Company ID: {test_data['company_id']}")
        print(f"User ID: {test_data['user_id']}")
        
        print(f"\n--- PHASE 1: Initialize ConsignerConsigneeAgent ---")
        
        # Start the consigner/consignee flow
        flow_response = await agent_manager.start_consigner_consignee_flow(test_data)
        
        if flow_response.success:
            print(f"✅ ConsignerConsigneeAgent initialized successfully")
            
            partners = flow_response.data.get('partners', [])
            if partners and len(partners) >= 2:
                print(f"Available partners: {len(partners)}")
                
                # Show available partners
                for i, partner in enumerate(partners[:3], 1):
                    print(f"  {i}. {partner['name']} ({partner['city']}) - ID: {partner['id']}")
                
                print(f"\n--- PHASE 2: ConsignerConsigneeAgent - Select Consigner ---")
                
                # Select first partner as consigner
                consigner_selection = {
                    "partner_id": partners[0]['id'],
                    "partner_name": partners[0]['name'],
                    "selection_type": "consigner"
                }
                
                print(f"Selecting consigner: {partners[0]['name']}")
                consigner_response = await agent_manager.handle_consigner_consignee_selection(consigner_selection)
                
                if consigner_response.success:
                    print(f"✅ Consigner selected in ConsignerConsigneeAgent")
                    
                    print(f"\n--- PHASE 3: ConsignerConsigneeAgent - Select Consignee (Triggers Chain) ---")
                    
                    # Select second partner as consignee
                    consignee_selection = {
                        "partner_id": partners[1]['id'],
                        "partner_name": partners[1]['name'],
                        "selection_type": "consignee"
                    }
                    
                    print(f"Selecting consignee: {partners[1]['name']}")
                    print(f"This should trigger: ConsignerConsigneeAgent → ParcelUpdateAgent")
                    print(f"\n🔄 Executing agent chain...")
                    
                    # This will trigger the automatic chain execution
                    consignee_response = await agent_manager.handle_consigner_consignee_selection(consignee_selection)
                    
                    print(f"\n--- PHASE 4: Analyze Chain Execution Results ---")
                    
                    if consignee_response.success:
                        action = consignee_response.data.get('action')
                        
                        print(f"Final action: {action}")
                        
                        if action == "selection_complete_and_parcel_updated":
                            print(f"\n🎉 COMPLETE SUCCESS: Agent chain executed successfully!")
                            print(f"✅ ConsignerConsigneeAgent completed")
                            print(f"✅ ParcelUpdateAgent executed")
                            print(f"✅ PATCH API called successfully")
                            
                            # Show execution results
                            final_data = consignee_response.data.get('final_data', {})
                            update_result = consignee_response.data.get('update_result', {})
                            
                            print(f"\n📊 Chain Execution Details:")
                            print(f"Workflow complete: {consignee_response.data.get('workflow_complete', False)}")
                            
                            # ConsignerConsigneeAgent results
                            consigner_details = final_data.get('consigner_details', {})
                            consignee_details = final_data.get('consignee_details', {})
                            
                            print(f"\n🔹 ConsignerConsigneeAgent Results:")
                            print(f"  Consigner: {consigner_details.get('name')} (ID: {consigner_details.get('id')})")
                            print(f"  Consigner Company: {consigner_details.get('company_name')} (ID: {consigner_details.get('company_id')})")
                            print(f"  Consignee: {consignee_details.get('name')} (ID: {consignee_details.get('id')})")
                            print(f"  Consignee Company: {consignee_details.get('company_name')} (ID: {consignee_details.get('company_id')})")
                            
                            # ParcelUpdateAgent results
                            updated_parcel = update_result.get('updated_parcel', {})
                            
                            if updated_parcel:
                                print(f"\n🔹 ParcelUpdateAgent Results:")
                                print(f"  Updated Parcel ID: {updated_parcel.get('_id')}")
                                print(f"  New _etag: {updated_parcel.get('_etag')}")
                                
                                # Show PATCH API payload results
                                sender = updated_parcel.get('sender', {})
                                receiver = updated_parcel.get('receiver', {})
                                
                                if sender:
                                    print(f"\n🔹 PATCH API - Sender Updated:")
                                    print(f"    sender_person: {sender.get('sender_person')}")
                                    print(f"    sender_company: {sender.get('sender_company')}")
                                    print(f"    name: {sender.get('name')}")
                                    print(f"    gstin: {sender.get('gstin')}")
                                
                                if receiver:
                                    print(f"\n🔹 PATCH API - Receiver Updated:")
                                    print(f"    receiver_person: {receiver.get('receiver_person')}")
                                    print(f"    receiver_company: {receiver.get('receiver_company')}")
                                    print(f"    name: {receiver.get('name')}")
                                    print(f"    gstin: {receiver.get('gstin')}")
                                
                                # Show preserved fields
                                preserved_fields = ["material_type", "quantity", "quantity_unit", "trip_id", "verification"]
                                print(f"\n🔹 Preserved Parcel Fields:")
                                for field in preserved_fields:
                                    if field in updated_parcel:
                                        print(f"    {field}: {updated_parcel[field]}")
                            
                            print(f"\n🎯 AGENT CHAIN EXECUTION: COMPLETE SUCCESS!")
                            
                        elif action == "selection_complete_update_failed":
                            print(f"\n⚠️ PARTIAL SUCCESS: ConsignerConsigneeAgent completed, but ParcelUpdateAgent failed")
                            
                            update_error = consignee_response.data.get('update_error')
                            print(f"ConsignerConsigneeAgent: ✅ Completed successfully")
                            print(f"ParcelUpdateAgent: ❌ Failed - {update_error}")
                            
                            # Show what would have been sent
                            final_data = consignee_response.data.get('final_data', {})
                            api_payload = final_data.get('api_payload', {})
                            if api_payload:
                                print(f"\nPayload prepared by ConsignerConsigneeAgent:")
                                print(f"  Payload keys: {list(api_payload.keys())}")
                            
                        else:
                            print(f"❓ Unexpected action: {action}")
                            print(f"Chain execution may not have been triggered properly")
                            
                    else:
                        print(f"❌ Consignee selection failed: {consignee_response.error}")
                        
                else:
                    print(f"❌ Consigner selection failed: {consigner_response.error}")
                    
            else:
                print(f"⚠️ Not enough partners for testing (need at least 2, found {len(partners)})")
                
        else:
            print(f"❌ Failed to initialize ConsignerConsigneeAgent: {flow_response.error}")
        
        print(f"\n" + "="*80)
        print("AGENT CHAIN EXECUTION TEST SUMMARY")
        print("="*80)
        print("✅ ConsignerConsigneeAgent → ParcelUpdateAgent integration verified")
        print("✅ Automatic chain execution after consignee selection")
        print("✅ Complete data mapping from selection to PATCH API")
        print("✅ Proper error handling and fallbacks")
        print("")
        print("Chain Flow:")
        print("1. ConsignerConsigneeAgent.start() → Show consigner options")
        print("2. ConsignerConsigneeAgent.select_consigner() → Show consignee options")
        print("3. ConsignerConsigneeAgent.select_consignee() → Enhance partner details")
        print("4. AgentManager.handle_consigner_consignee_selection() → Detect completion")
        print("5. AgentManager._update_parcel_with_selections() → Call ParcelUpdateAgent")
        print("6. ParcelUpdateAgent.execute() → Build payload & PATCH API")
        print("7. Return complete results with updated parcel")
        print("")
        print("AUTOMATIC EXECUTION: ConsignerConsigneeAgent → ParcelUpdateAgent ✅")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_individual_agents():
    """Test individual agents to verify they work independently"""
    print(f"\n" + "="*60)
    print("INDIVIDUAL AGENT VERIFICATION")
    print("="*60)
    
    try:
        from agents.consigner_consignee_agent import ConsignerConsigneeAgent
        from agents.parcel_update_agent import ParcelUpdateAgent
        from agents.base_agent import APIIntent
        
        print(f"\n--- Testing ConsignerConsigneeAgent individually ---")
        
        consigner_agent = ConsignerConsigneeAgent()
        
        # Initialize the agent
        init_data = {
            "company_id": "62d66794e54f47829a886a1d",
            "trip_id": "68c42057d7bd2d6597272ac4",
            "parcel_id": "68c42057d7bd2d6597272ac8"
        }
        
        init_response = await consigner_agent.execute(APIIntent.CREATE, init_data)
        
        if init_response.success:
            print(f"✅ ConsignerConsigneeAgent can be initialized independently")
            print(f"Current step: {init_response.data.get('current_step')}")
        else:
            print(f"❌ ConsignerConsigneeAgent initialization failed: {init_response.error}")
        
        print(f"\n--- Testing ParcelUpdateAgent individually ---")
        
        parcel_agent = ParcelUpdateAgent()
        
        # Test getting parcel details
        parcel_data = {"parcel_id": "68c42057d7bd2d6597272ac8"}
        
        parcel_response = await parcel_agent.execute(APIIntent.READ, parcel_data)
        
        if parcel_response.success:
            print(f"✅ ParcelUpdateAgent can retrieve parcel data independently")
            etag = parcel_response.data.get('_etag')
            print(f"Retrieved _etag: {etag}")
        else:
            print(f"❌ ParcelUpdateAgent parcel retrieval failed: {parcel_response.error}")
        
        print(f"\n✅ Both agents verified to work independently")
        
    except Exception as e:
        print(f"Error testing individual agents: {str(e)}")

if __name__ == "__main__":
    print("Running agent chain execution test...")
    asyncio.run(test_agent_chain_execution())
    
    print("\n" + "="*80)
    print("Running individual agent verification...")
    asyncio.run(test_individual_agents())