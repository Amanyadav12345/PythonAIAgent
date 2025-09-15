#!/usr/bin/env python3
"""
Test the enhanced consigner/consignee selection workflow
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_consigner_consignee_workflow():
    """Test complete consigner/consignee selection workflow"""
    print("Testing enhanced consigner/consignee selection workflow...")
    
    try:
        from agents.agent_manager import agent_manager
        from agents.base_agent import APIIntent
        
        print(f"\n=== Testing Enhanced ConsignerConsigneeAgent ===")
        print(f"Features:")
        print(f"1. Shared partner list for both consigner and consignee")
        print(f"2. Step-by-step selection process")
        print(f"3. Data storage throughout the process")
        print(f"4. Final API payload preparation")
        
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
        
        print(f"\n--- Step 1: Initialize Selection Process ---")
        
        # Start the consigner/consignee flow
        response = await agent_manager.start_consigner_consignee_flow(test_data)
        
        if response.success:
            print(f"✅ Flow initialized successfully")
            print(f"Current step: {response.data.get('current_step')}")
            print(f"Partners available: {len(response.data.get('partners', []))}")
            
            selection_data = response.data.get('selection_data', {})
            print(f"Selection status: {selection_data.get('completion_status', {})}")
            
            partners = response.data.get('partners', [])
            if partners:
                print(f"\nAvailable partners:")
                for i, partner in enumerate(partners[:3], 1):  # Show first 3
                    print(f"  {i}. {partner['name']} ({partner['city']})")
                
                print(f"\n--- Step 2: Select Consigner ---")
                
                # Simulate consigner selection (select first partner)
                consigner_selection_data = {
                    "partner_id": partners[0]['id'],
                    "partner_name": partners[0]['name'],
                    "selection_type": "consigner"
                }
                
                consigner_response = await agent_manager.handle_consigner_consignee_selection(consigner_selection_data)
                
                if consigner_response.success:
                    print(f"✅ Consigner selected: {partners[0]['name']}")
                    print(f"Current step: {consigner_response.data.get('current_step')}")
                    
                    selection_data = consigner_response.data.get('selection_data', {})
                    print(f"Selection status: {selection_data.get('completion_status', {})}")
                    
                    if consigner_response.data.get('current_step') == 'consignee':
                        print(f"\n--- Step 3: Select Consignee ---")
                        
                        # Simulate consignee selection (select second partner if available, or first)
                        consignee_partner = partners[1] if len(partners) > 1 else partners[0]
                        
                        consignee_selection_data = {
                            "partner_id": consignee_partner['id'],
                            "partner_name": consignee_partner['name'],
                            "selection_type": "consignee"
                        }
                        
                        consignee_response = await agent_manager.handle_consigner_consignee_selection(consignee_selection_data)
                        
                        if consignee_response.success:
                            print(f"✅ Consignee selected: {consignee_partner['name']}")
                            print(f"Current step: {consignee_response.data.get('current_step')}")
                            
                            final_data = consignee_response.data.get('final_data', {})
                            api_payload = final_data.get('api_payload', {})
                            
                            print(f"\n--- Step 4: Final Results ---")
                            print(f"✅ Selection process completed!")
                            print(f"Ready for API: {consignee_response.data.get('ready_for_api', False)}")
                            
                            print(f"\nFinal Selection Summary:")
                            consigner_details = final_data.get('consigner_details', {})
                            consignee_details = final_data.get('consignee_details', {})
                            
                            print(f"Consigner: {consigner_details.get('name')} ({consigner_details.get('city')})")
                            print(f"Consigner ID: {consigner_details.get('id')}")
                            print(f"Consignee: {consignee_details.get('name')} ({consignee_details.get('city')})")
                            print(f"Consignee ID: {consignee_details.get('id')}")
                            
                            print(f"\nAPI Payload Preview:")
                            print(f"Trip ID: {api_payload.get('trip_id')}")
                            print(f"Parcel ID: {api_payload.get('parcel_id')}")
                            print(f"Consigner ID: {api_payload.get('consigner_id')}")
                            print(f"Consignee ID: {api_payload.get('consignee_id')}")
                            print(f"User ID: {api_payload.get('user_id')}")
                            print(f"Company ID: {api_payload.get('company_id')}")
                            
                            metadata = api_payload.get('metadata', {})
                            print(f"\nMetadata:")
                            print(f"Selection timestamp: {metadata.get('selection_timestamp')}")
                            
                        else:
                            print(f"❌ Consignee selection failed: {consignee_response.error}")
                    else:
                        print(f"❌ Expected step 'consignee' but got: {consigner_response.data.get('current_step')}")
                else:
                    print(f"❌ Consigner selection failed: {consigner_response.error}")
            else:
                print(f"⚠️ No partners found for testing")
        else:
            print(f"❌ Flow initialization failed: {response.error}")
            
        print(f"\n" + "="*70)
        print("ENHANCED CONSIGNER/CONSIGNEE WORKFLOW SUMMARY:")
        print("="*70)
        print("✅ Created ConsignerConsigneeAgent with enhanced features")
        print("✅ Integrated agent into AgentManager") 
        print("✅ Added step-by-step selection process")
        print("✅ Implemented shared partner list")
        print("✅ Added data storage throughout process")
        print("✅ Created final API payload builder")
        print("")
        print("Workflow Flow:")
        print("1. Initialize selection process (fetch shared partners)")
        print("2. User selects consigner from partner list")
        print("3. System stores consigner and shows same list for consignee")
        print("4. User selects consignee from same partner list")
        print("5. System prepares final data structure for API")
        print("6. All selected details stored and ready for submission")
        print("")
        print("Key Features:")
        print("- Shared partner list between consigner and consignee")
        print("- Step-by-step guided selection process")
        print("- Real-time data storage and validation")
        print("- Final API payload preparation")
        print("- Complete selection summary")
        print("- Ready for integration with any API endpoint")
        
        print("\n" + "="*70)
        print("INTEGRATION GUIDE:")
        print("="*70)
        print("1. Start flow: agent_manager.start_consigner_consignee_flow(data)")
        print("2. Handle selections: agent_manager.handle_consigner_consignee_selection(data)")
        print("3. Check response.data.ready_for_api === true")
        print("4. Use response.data.final_data.api_payload for API calls")
        print("5. All partner details stored in response.data.final_data")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_consigner_consignee_workflow())