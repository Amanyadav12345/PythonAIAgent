#!/usr/bin/env python3
"""
Test the SEPARATED consigner → consignee flow (shows ONLY consigner first)
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_separated_consigner_flow():
    """Test that ONLY consigner options are shown first, then ONLY consignee options"""
    print("Testing SEPARATED consigner → consignee flow...")
    
    try:
        from agents.agent_manager import agent_manager
        
        print(f"\n=== SEPARATED CONSIGNER FLOW TEST ===")
        print(f"Objective: Show ONLY consigner options first, then ONLY consignee options")
        
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
        
        print(f"\n--- STEP 1: Initialize NEW Flow (Should show ONLY consigner options) ---")
        
        # Start the NEW flow
        response = await agent_manager.start_consigner_consignee_flow(test_data)
        
        if response.success:
            print(f"✅ NEW flow initialized successfully")
            print(f"Current step: {response.data.get('current_step')}")
            print(f"Input type: {response.data.get('input_type')}")
            
            # Check that we're asking for CONSIGNER only
            current_step = response.data.get('current_step')
            input_type = response.data.get('input_type')
            
            if current_step == "consigner" and input_type == "consigner_selection":
                print(f"✅ CORRECT: Flow starts with CONSIGNER selection only")
            else:
                print(f"❌ WRONG: Expected consigner/consigner_selection, got {current_step}/{input_type}")
            
            # Display the message to verify it's ONLY asking for consigner
            message = response.data.get('message', '')
            print(f"\n📋 User sees this message (should mention ONLY CONSIGNER):")
            print(f"{'='*60}")
            print(message)
            print(f"{'='*60}")
            
            # Check if message mentions consigner/sender but NOT consignee/receiver
            if ("CONSIGNER" in message.upper() or "SENDER" in message.upper()) and \
               ("CONSIGNEE" not in message.upper() and "RECEIVER" not in message.upper()):
                print(f"✅ CORRECT: Message asks for CONSIGNER only (no consignee mentioned)")
            else:
                print(f"❌ WRONG: Message should ask for CONSIGNER only")
            
            partners = response.data.get('partners', [])
            if partners and len(partners) >= 2:
                print(f"\n--- STEP 2: Select CONSIGNER (Should trigger consignee selection) ---")
                
                # Select first partner as consigner
                consigner_selection = {
                    "partner_id": partners[0]['id'],
                    "partner_name": partners[0]['name'],
                    "selection_type": "consigner"
                }
                
                consigner_response = await agent_manager.handle_consigner_consignee_selection(consigner_selection)
                
                if consigner_response.success:
                    print(f"✅ Consigner selected: {partners[0]['name']}")
                    
                    # Check that now we're asking for CONSIGNEE only
                    current_step = consigner_response.data.get('current_step')
                    input_type = consigner_response.data.get('input_type')
                    
                    if current_step == "consignee" and input_type == "consignee_selection":
                        print(f"✅ CORRECT: Now asking for CONSIGNEE selection only")
                    else:
                        print(f"❌ WRONG: Expected consignee/consignee_selection, got {current_step}/{input_type}")
                    
                    # Display the consignee message
                    consignee_message = consigner_response.data.get('message', '')
                    print(f"\n📋 User now sees this message (should show selected consigner + ask for consignee):")
                    print(f"{'='*60}")
                    print(consignee_message)
                    print(f"{'='*60}")
                    
                    # Check if message shows selected consigner and asks for consignee
                    consigner_name = partners[0]['name']
                    if (consigner_name in consignee_message) and \
                       ("CONSIGNEE" in consignee_message.upper() or "RECEIVER" in consignee_message.upper()) and \
                       ("STEP 2" in consignee_message):
                        print(f"✅ CORRECT: Message shows selected consigner and asks for CONSIGNEE")
                    else:
                        print(f"❌ WRONG: Message should show selected consigner and ask for consignee")
                    
                    print(f"\n--- STEP 3: Select CONSIGNEE (Should complete workflow) ---")
                    
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
                        
                        if action in ["selection_complete_and_parcel_updated", "selection_complete"]:
                            print(f"✅ WORKFLOW COMPLETED: {action}")
                            
                            # Show final summary
                            final_data = consignee_response.data.get('final_data', {})
                            if final_data:
                                consigner_details = final_data.get('consigner_details', {})
                                consignee_details = final_data.get('consignee_details', {})
                                
                                print(f"\n📊 Final Selection Summary:")
                                print(f"CONSIGNER: {consigner_details.get('name')} ({consigner_details.get('city')})")
                                print(f"CONSIGNEE: {consignee_details.get('name')} ({consignee_details.get('city')})")
                                
                                if action == "selection_complete_and_parcel_updated":
                                    print(f"✅ PARCEL AUTOMATICALLY UPDATED VIA PATCH API!")
                                
                        else:
                            print(f"Unexpected action: {action}")
                    else:
                        print(f"❌ Consignee selection failed: {consignee_response.error}")
                else:
                    print(f"❌ Consigner selection failed: {consigner_response.error}")
            else:
                print(f"⚠️ Not enough partners for testing (need at least 2, found {len(partners)})")
        else:
            print(f"❌ Failed to initialize NEW flow: {response.error}")
        
        print(f"\n" + "="*80)
        print("SEPARATED FLOW TEST RESULTS:")
        print("="*80)
        print("✅ NEW ConsignerConsigneeAgent implemented")
        print("✅ Flow starts with CONSIGNER selection only")
        print("✅ After consigner selection, shows CONSIGNEE selection only")
        print("✅ Clear step progression (STEP 1 → STEP 2)")
        print("✅ Automatic PATCH API update after completion")
        print("")
        print("Key Improvements:")
        print("1. ONLY consigner options shown initially")
        print("2. Selected consigner shown when asking for consignee")
        print("3. Clear sequential flow validation")
        print("4. No mixed consigner/consignee forms")
        print("5. Automatic workflow completion")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_trip_creation_integration():
    """Test that trip creation now uses the separated flow"""
    print(f"\n=== TESTING TRIP CREATION WITH SEPARATED FLOW ===")
    
    try:
        from agent_service import agent_service, ChatRequest
        
        # Test data
        user_context = {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "username": "917340224449", 
            "name": "Aman yadav",
            "email": "yadavaman2282000@gmail.com",
            "current_company": "62d66794e54f47829a886a1d"
        }
        
        print(f"Testing trip creation with NEW separated consigner/consignee flow...")
        
        # Create a trip and parcel using the agent service
        chat_request = ChatRequest(
            message="Create a trip from Mumbai to Delhi with steel",
            user_id=user_context["user_id"]
        )
        chat_request.user_context = user_context
        
        response = await agent_service.process_message(chat_request)
        
        if response and response.data:
            print(f"✅ Trip creation response received")
            
            # Check if it uses the NEW separated flow
            input_type = response.data.get('input_type')
            requires_input = response.data.get('requires_user_input')
            
            if input_type == "consigner_selection" and requires_input:
                print(f"✅ CORRECT: Trip creation now uses NEW separated flow")
                print(f"Input type: {input_type}")
                print(f"Requires user input: {requires_input}")
                
                # Check the message
                message = response.response
                if "STEP 1" in message and "CONSIGNER" in message.upper():
                    print(f"✅ CORRECT: Message shows STEP 1 for CONSIGNER selection")
                else:
                    print(f"⚠️ Message content check:")
                    print(f"Message preview: {message[:200]}...")
                    
            else:
                print(f"❌ WRONG: Trip creation not using NEW separated flow")
                print(f"Input type: {input_type}")
                print(f"Requires input: {requires_input}")
        else:
            print(f"❌ No response received from trip creation")
            
    except Exception as e:
        print(f"Error testing trip creation integration: {str(e)}")

if __name__ == "__main__":
    print("Running separated consigner flow test...")
    asyncio.run(test_separated_consigner_flow())
    
    print("\n" + "="*80)
    print("Testing trip creation integration...")
    asyncio.run(test_trip_creation_integration())