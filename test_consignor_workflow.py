#!/usr/bin/env python3
"""
Test the complete parcel + consignor selection workflow
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_consignor_workflow():
    """Test complete workflow: Trip + Parcel creation + Consignor selection"""
    print("Testing complete parcel + consignor selection workflow...")
    
    try:
        from agent_service import agent_service, ChatRequest
        
        # Test message that should trigger trip + parcel creation + consignor selection
        test_message = "Create a trip from Mumbai to Delhi with steel"
        
        print(f"\n=== Testing Complete Workflow ===")
        print(f"Request: {test_message}")
        print(f"Expected: Trip creation -> Parcel creation -> Consignor selection")
        
        chat_request = ChatRequest(
            message=test_message,
            user_id="6257f1d75b42235a2ae4ab34"
        )
        
        chat_request.user_context = {
            "user_id": "6257f1d75b42235a2ae4ab34",
            "username": "917340224449", 
            "name": "Aman yadav",
            "email": "yadavaman2282000@gmail.com",
            "current_company": "62d66794e54f47829a886a1d"
        }
        
        try:
            response = await agent_service.process_message(chat_request)
            
            print(f"\n--- Response ---")
            try:
                print(f"Message: {response.response}")
            except UnicodeEncodeError as e:
                print(f"Message: <Unicode encoding error: {str(e)}>")
                print(f"Message length: {len(response.response)}")
            print(f"Tools used: {response.tools_used}")
            
            # Debug: Check if response has consignor selection fields
            if hasattr(response, 'data') and response.data:
                print(f"Response data keys: {list(response.data.keys()) if isinstance(response.data, dict) else 'Not a dict'}")
                if isinstance(response.data, dict):
                    print(f"requires_user_input: {response.data.get('requires_user_input')}")
                    print(f"input_type: {response.data.get('input_type')}")
                    print(f"consignor_selection: {bool(response.data.get('consignor_selection'))}")
            
            # Check workflow completion
            if "Successfully created trip" in response.response and "parcel" in response.response:
                print(f"\nSUCCESS: Trip and parcel creation workflow completed")
                
                # Check for consignor selection trigger - in response data or message
                consignor_triggered = False
                if hasattr(response, 'data') and response.data and isinstance(response.data, dict):
                    if response.data.get('requires_user_input') and response.data.get('input_type') == 'consignor_selection':
                        consignor_triggered = True
                
                if not consignor_triggered:
                    if "consignor" in response.response.lower() or "preferred partners" in response.response.lower():
                        consignor_triggered = True
                
                if consignor_triggered:
                    print(f"SUCCESS: Consignor selection initiated")
                    print(f"SUCCESS: User should see preferred partners for selection")
                else:
                    print(f"PARTIAL: Parcel created but consignor selection not triggered")
                    
            elif "Failed to create" in response.response:
                print(f"ERROR: Workflow failed - {response.response}")
            else:
                print(f"UNKNOWN: Check response for workflow status")
                
        except Exception as e:
            print(f"EXCEPTION: {str(e)}")
        
        print(f"\n" + "="*70)
        print("CONSIGNOR SELECTION WORKFLOW TEST SUMMARY:")
        print("="*70)
        print("+ Created ConsignorSelectionAgent with preferred partners API")
        print("+ Integrated agent into AgentManager")
        print("+ Added post-parcel-creation trigger")
        print("+ Added consignor selection handling methods")
        print("")
        print("Workflow Flow:")
        print("1. User requests trip creation with material")  
        print("2. System creates trip using TripCreationAgent")
        print("3. System creates parcel using ParcelCreationAgent + MaterialAgent")
        print("4. System triggers ConsignorSelectionAgent for preferred partners")
        print("5. User sees 5 preferred partners with selection options")
        print("6. User can select partner, see more, or skip")
        print("")
        print("API Integration:")
        print("- Endpoint: https://35.244.19.78:8042/preferred_partners")
        print("- Query: embedded={user_preferred_partner:1} & where={user_company}")
        print("- Pagination: 5 partners per page")
        print("- Selection: Updates parcel with chosen consignor")
        
        print("\n" + "="*70)
        print("NEXT STEPS FOR FRONTEND INTEGRATION:")
        print("="*70)
        print("1. Check response.requires_user_input === true")
        print("2. Check response.input_type === 'consignor_selection'")
        print("3. Display response.consignor_selection.formatted_message")
        print("4. Handle user selection (1-5, 'more', 'skip')")
        print("5. Call agent_manager.handle_consignor_selection() with user input")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_consignor_agent_directly():
    """Test ConsignorSelectionAgent directly"""
    print("\n" + "="*50)
    print("TESTING CONSIGNOR AGENT DIRECTLY:")
    print("="*50)
    
    try:
        from agents.agent_manager import agent_manager
        from agents.base_agent import APIIntent
        
        # Test getting preferred partners
        consignor_data = {
            "company_id": "62d66794e54f47829a886a1d",
            "page": 0,
            "page_size": 5
        }
        
        print("Testing ConsignorSelectionAgent.SEARCH...")
        response = await agent_manager.execute_single_intent(
            "consignor_selector", APIIntent.SEARCH, consignor_data
        )
        
        if response.success and response.data:
            partners = response.data.get("partners", [])
            print(f"+ Found {len(partners)} preferred partners")
            
            if partners:
                consignor_agent = agent_manager.get_agent("consignor_selector")
                formatted_message = consignor_agent.format_partners_for_chat(partners, 0)
                print(f"+ Formatted message preview:")
                print(formatted_message[:300] + "..." if len(formatted_message) > 300 else formatted_message)
            else:
                print("i No partners found for test company")
                
        else:
            print(f"- ConsignorSelectionAgent failed: {response.error}")
            
    except Exception as e:
        print(f"ERROR testing ConsignorSelectionAgent directly: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_consignor_workflow())
    asyncio.run(test_consignor_agent_directly())