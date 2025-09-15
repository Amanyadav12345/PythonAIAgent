#!/usr/bin/env python3
"""
ParcelUpdateAgent - Handles PATCH updates to parcels with consigner/consignee details
Manages _etag handling and complete parcel update workflow
"""
import json
import httpx
from typing import Dict, List, Any, Optional
from .base_agent import BaseAPIAgent, APIIntent, APIResponse

class ParcelUpdateAgent(BaseAPIAgent):
    """Agent for updating parcels via PATCH API with consigner/consignee data"""
    
    def __init__(self):
        auth_config = {
            "username": "917340224449",
            "password": "12345",
            "token": None
        }
        super().__init__(
            name="parcel_update",
            base_url="https://35.244.19.78:8042/parcels",
            auth_config=auth_config
        )
        
        # Store parcel data for _etag management
        self.parcel_cache = {}
    
    async def execute(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Execute parcel update based on intent"""
        try:
            if intent == APIIntent.UPDATE:
                return await self._update_parcel(data)
            elif intent == APIIntent.READ:
                return await self._get_parcel_details(data)
            elif intent == APIIntent.CREATE:
                return await self._update_parcel_with_consigner_consignee(data)
            else:
                return APIResponse(
                    success=False,
                    error=f"Unsupported intent: {intent}",
                    agent_name=self.name
                )
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"ParcelUpdateAgent error: {str(e)}",
                agent_name=self.name
            )
    
    async def _get_parcel_details(self, data: Dict[str, Any]) -> APIResponse:
        """Get current parcel details including _etag"""
        try:
            parcel_id = data.get("parcel_id")
            if not parcel_id:
                return APIResponse(
                    success=False,
                    error="parcel_id is required to get parcel details",
                    agent_name=self.name
                )
            
            print(f"ParcelUpdateAgent: Getting parcel details for ID: {parcel_id}")
            
            response = await self._make_request("GET", f"/{parcel_id}")
            
            if response.success and response.data:
                # Cache the parcel data including _etag
                self.parcel_cache[parcel_id] = {
                    "data": response.data,
                    "_etag": response.data.get("_etag"),
                    "last_updated": self._get_current_timestamp()
                }
                
                print(f"ParcelUpdateAgent: Cached parcel data with _etag: {response.data.get('_etag')}")
                
                return APIResponse(
                    success=True,
                    data={
                        "parcel": response.data,
                        "_etag": response.data.get("_etag"),
                        "parcel_id": parcel_id
                    },
                    agent_name=self.name
                )
            else:
                return APIResponse(
                    success=False,
                    error=f"Failed to get parcel details: {response.error}",
                    agent_name=self.name
                )
                
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Error getting parcel details: {str(e)}",
                agent_name=self.name
            )
    
    async def _update_parcel(self, data: Dict[str, Any]) -> APIResponse:
        """Update parcel with PATCH request"""
        try:
            parcel_id = data.get("parcel_id")
            if not parcel_id:
                return APIResponse(
                    success=False,
                    error="parcel_id is required for parcel update",
                    agent_name=self.name
                )
            
            # Get _etag if not provided
            etag = data.get("_etag")
            if not etag:
                # Try to get from cache first
                cached_parcel = self.parcel_cache.get(parcel_id)
                if cached_parcel:
                    etag = cached_parcel.get("_etag")
                    print(f"ParcelUpdateAgent: Using cached _etag: {etag}")
                else:
                    # Fetch current parcel to get _etag
                    parcel_response = await self._get_parcel_details({"parcel_id": parcel_id})
                    if parcel_response.success:
                        etag = parcel_response.data.get("_etag")
                        print(f"ParcelUpdateAgent: Fetched _etag: {etag}")
                    else:
                        return APIResponse(
                            success=False,
                            error=f"Could not get _etag for parcel update: {parcel_response.error}",
                            agent_name=self.name
                        )
            
            if not etag:
                return APIResponse(
                    success=False,
                    error="_etag is required for parcel update",
                    agent_name=self.name
                )
            
            # Prepare update payload
            update_payload = data.get("update_payload", {})
            
            print(f"ParcelUpdateAgent: Updating parcel {parcel_id} with _etag: {etag}")
            print(f"ParcelUpdateAgent: Update payload keys: {list(update_payload.keys())}")
            
            # Make PATCH request with _etag in headers
            headers = {
                "If-Match": etag,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                auth = (self.auth_config["username"], self.auth_config["password"])
                url = f"{self.base_url}/{parcel_id}"
                
                response = await client.patch(
                    url,
                    json=update_payload,
                    headers=headers,
                    auth=auth
                )
                
                print(f"ParcelUpdateAgent: PATCH response status: {response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Update cache with new data
                    self.parcel_cache[parcel_id] = {
                        "data": response_data,
                        "_etag": response_data.get("_etag"),
                        "last_updated": self._get_current_timestamp()
                    }
                    
                    print(f"ParcelUpdateAgent: Parcel updated successfully")
                    print(f"ParcelUpdateAgent: New _etag: {response_data.get('_etag')}")
                    
                    return APIResponse(
                        success=True,
                        data={
                            "updated_parcel": response_data,
                            "parcel_id": parcel_id,
                            "_etag": response_data.get("_etag"),
                            "update_payload": update_payload
                        },
                        agent_name=self.name
                    )
                else:
                    error_text = response.text
                    print(f"ParcelUpdateAgent: PATCH failed: {error_text}")
                    
                    return APIResponse(
                        success=False,
                        error=f"PATCH request failed with status {response.status_code}: {error_text}",
                        agent_name=self.name
                    )
                    
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Error updating parcel: {str(e)}",
                agent_name=self.name
            )
    
    async def _update_parcel_with_consigner_consignee(self, data: Dict[str, Any]) -> APIResponse:
        """Update parcel with consigner/consignee details from selection workflow"""
        try:
            parcel_id = data.get("parcel_id")
            final_data = data.get("final_data", {})

            if not parcel_id:
                return APIResponse(
                    success=False,
                    error="parcel_id is required for consigner/consignee update",
                    agent_name=self.name
                )

            if not final_data:
                return APIResponse(
                    success=False,
                    error="final_data from consigner/consignee selection is required",
                    agent_name=self.name
                )

            # Extract _etag from final_data (passed from ConsignerConsigneeAgent)
            parcel_etag = final_data.get("parcel_etag") or data.get("_etag")

            # COMPREHENSIVE LOGGING - ParcelUpdateAgent execution starts
            print(f"ParcelUpdateAgent: ==========================================")
            print(f"ParcelUpdateAgent: PARCEL UPDATE AGENT EXECUTING")
            print(f"ParcelUpdateAgent: ==========================================")
            print(f"ParcelUpdateAgent: ← Triggered by: AgentManager (automatic chain)")
            print(f"ParcelUpdateAgent: → Parcel ID: {parcel_id}")
            print(f"ParcelUpdateAgent: → Trip ID: {final_data.get('trip_id')}")
            if parcel_etag:
                print(f"ParcelUpdateAgent: → Using _etag from selection workflow: {parcel_etag}")
            else:
                print(f"ParcelUpdateAgent: → No _etag provided, will fetch from API")
            print(f"ParcelUpdateAgent: → Target API: PATCH /parcels/{parcel_id}")
            print(f"ParcelUpdateAgent: → Headers will include: If-Match: {parcel_etag}")
            print(f"ParcelUpdateAgent: ==========================================")

            # Log the stored selection data
            consigner_name = final_data.get('consigner_details', {}).get('name', 'N/A')
            consignee_name = final_data.get('consignee_details', {}).get('name', 'N/A')
            print(f"ParcelUpdateAgent: PROCESSING STORED BACKEND DATA:")
            print(f"ParcelUpdateAgent: → Consigner (from backend): {consigner_name}")
            print(f"ParcelUpdateAgent: → Consignee (from backend): {consignee_name}")
            print(f"ParcelUpdateAgent: → Both selections retrieved from ConsignerConsigneeAgent storage")
            print(f"ParcelUpdateAgent: → Ready to build complete PATCH payload...")
            print(f"ParcelUpdateAgent: ==========================================")
            
            # Extract consigner/consignee details
            consigner_details = final_data.get("consigner_details", {})
            consignee_details = final_data.get("consignee_details", {})
            user_context = final_data.get("user_context", {})
            
            # Build the update payload based on the provided structure
            update_payload = await self._build_update_payload(
                parcel_id=parcel_id,
                consigner_details=consigner_details,
                consignee_details=consignee_details,
                user_context=user_context,
                additional_data=data
            )
            
            print(f"ParcelUpdateAgent: Built update payload for parcel {parcel_id}")
            
            # Perform the update with the stored _etag
            update_response = await self._update_parcel({
                "parcel_id": parcel_id,
                "update_payload": update_payload,
                "_etag": parcel_etag  # Use _etag from selection workflow
            })
            
            if update_response.success:
                # FINAL SUCCESS LOGGING
                new_etag = update_response.data.get("_etag")
                print(f"ParcelUpdateAgent: ==========================================")
                print(f"ParcelUpdateAgent: ✅ PATCH API EXECUTION SUCCESSFUL!")
                print(f"ParcelUpdateAgent: ==========================================")
                print(f"ParcelUpdateAgent: → Parcel {parcel_id} updated successfully")
                print(f"ParcelUpdateAgent: → Original _etag: {parcel_etag}")
                print(f"ParcelUpdateAgent: → New _etag returned: {new_etag}")
                print(f"ParcelUpdateAgent: → Consigner data applied: {consigner_name}")
                print(f"ParcelUpdateAgent: → Consignee data applied: {consignee_name}")
                print(f"ParcelUpdateAgent: → PATCH API: https://35.244.19.78:8042/parcels/{parcel_id}")
                print(f"ParcelUpdateAgent: → Status: 200 OK ✅")
                print(f"ParcelUpdateAgent: ==========================================")

                return APIResponse(
                    success=True,
                    data={
                        "action": "parcel_updated_with_consigner_consignee",
                        "parcel_id": parcel_id,
                        "consigner_details": consigner_details,
                        "consignee_details": consignee_details,
                        "update_result": update_response.data,
                        "message": self._build_success_message(consigner_details, consignee_details, parcel_id)
                    },
                    agent_name=self.name
                )
            else:
                return update_response
                
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Error updating parcel with consigner/consignee: {str(e)}",
                agent_name=self.name
            )
    
    async def _build_update_payload(self, parcel_id: str, consigner_details: Dict[str, Any], 
                                  consignee_details: Dict[str, Any], user_context: Dict[str, Any],
                                  additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build the complete update payload structure for PATCH request with all consigner/consignee details"""
        try:
            # Get current parcel data to preserve existing fields
            current_parcel_response = await self._get_parcel_details({"parcel_id": parcel_id})
            
            if not current_parcel_response.success:
                print(f"ParcelUpdateAgent: Could not get current parcel data, building payload from available data")
                current_parcel = {}
            else:
                current_parcel = current_parcel_response.data.get("parcel", {})
                print(f"ParcelUpdateAgent: Retrieved current parcel data successfully")
            
            # Build the complete payload based on the provided structure
            payload = {}
            
            # Preserve ALL existing core fields (as per your example payload)
            core_fields = [
                "material_type", "quantity", "quantity_unit", "description", 
                "cost", "part_load", "pickup_postal_address", "unload_postal_address",
                "created_by", "trip_id", "verification", "created_by_company", "_id"
            ]
            
            for field in core_fields:
                if field in current_parcel:
                    payload[field] = current_parcel[field]
            
            # Set defaults for required fields if not present
            if "_id" not in payload:
                payload["_id"] = parcel_id
            
            if "verification" not in payload:
                payload["verification"] = "Verified"
                
            if "created_by" not in payload and user_context.get("user_id"):
                payload["created_by"] = user_context["user_id"]
                
            if "created_by_company" not in payload and user_context.get("current_company"):
                payload["created_by_company"] = user_context["current_company"]
                
            if "trip_id" not in payload and additional_data and additional_data.get("trip_id"):
                payload["trip_id"] = additional_data["trip_id"]
            
            # Get company details for consigner and consignee (if needed)
            consigner_company_info = await self._get_partner_company_details(consigner_details.get("id"))
            consignee_company_info = await self._get_partner_company_details(consignee_details.get("id"))
            
            # Update sender (consigner) information with complete details
            if consigner_details.get("id"):
                sender_info = {
                    "sender_person": consigner_details["id"],
                    "name": consigner_details.get("name", ""),
                }
                
                # Add company information
                if consigner_company_info.get("success") and consigner_company_info.get("companies"):
                    primary_company = consigner_company_info["companies"][0]
                    sender_info["sender_company"] = primary_company.get("_id", "")
                    sender_info["gstin"] = primary_company.get("gstin", consigner_details.get("gstin", ""))
                else:
                    # Fallback to existing or provided data
                    sender_info["sender_company"] = consigner_details.get("company_id", "")
                    sender_info["gstin"] = consigner_details.get("gstin", "")
                    
                    # If still empty, try to preserve existing
                    if not sender_info["sender_company"] and "sender" in current_parcel:
                        sender_info["sender_company"] = current_parcel["sender"].get("sender_company", "")
                    if not sender_info["gstin"] and "sender" in current_parcel:
                        sender_info["gstin"] = current_parcel["sender"].get("gstin", "")
                
                payload["sender"] = sender_info
                print(f"ParcelUpdateAgent: Updated sender with person: {sender_info['sender_person']}, company: {sender_info['sender_company']}")
            elif "sender" in current_parcel:
                payload["sender"] = current_parcel["sender"]
                print(f"ParcelUpdateAgent: Preserved existing sender information")
            
            # Update receiver (consignee) information with complete details
            if consignee_details.get("id"):
                receiver_info = {
                    "receiver_person": consignee_details["id"],
                    "name": consignee_details.get("name", ""),
                }
                
                # Add company information
                if consignee_company_info.get("success") and consignee_company_info.get("companies"):
                    primary_company = consignee_company_info["companies"][0]
                    receiver_info["receiver_company"] = primary_company.get("_id", "")
                    receiver_info["gstin"] = primary_company.get("gstin", consignee_details.get("gstin", ""))
                else:
                    # Fallback to existing or provided data
                    receiver_info["receiver_company"] = consignee_details.get("company_id", "")
                    receiver_info["gstin"] = consignee_details.get("gstin", "")
                    
                    # If still empty, try to preserve existing
                    if not receiver_info["receiver_company"] and "receiver" in current_parcel:
                        receiver_info["receiver_company"] = current_parcel["receiver"].get("receiver_company", "")
                    if not receiver_info["gstin"] and "receiver" in current_parcel:
                        receiver_info["gstin"] = current_parcel["receiver"].get("gstin", "")
                
                payload["receiver"] = receiver_info
                print(f"ParcelUpdateAgent: Updated receiver with person: {receiver_info['receiver_person']}, company: {receiver_info['receiver_company']}")
            elif "receiver" in current_parcel:
                payload["receiver"] = current_parcel["receiver"]
                print(f"ParcelUpdateAgent: Preserved existing receiver information")
            
            # Override with any additional data provided
            if additional_data:
                for key, value in additional_data.items():
                    if key not in ["parcel_id", "final_data", "_etag", "user_context"]:
                        payload[key] = value
                        print(f"ParcelUpdateAgent: Added additional field: {key}")
            
            print(f"ParcelUpdateAgent: Built complete payload with {len(payload)} fields")
            print(f"ParcelUpdateAgent: Payload keys: {list(payload.keys())}")
            
            # Log the important updates
            if "sender" in payload:
                print(f"ParcelUpdateAgent: Sender details - Person: {payload['sender'].get('sender_person')}, Name: {payload['sender'].get('name')}")
            if "receiver" in payload:
                print(f"ParcelUpdateAgent: Receiver details - Person: {payload['receiver'].get('receiver_person')}, Name: {payload['receiver'].get('name')}")
            
            return payload
            
        except Exception as e:
            print(f"ParcelUpdateAgent: Error building update payload: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Return comprehensive minimal payload on error
            minimal_payload = {
                "_id": parcel_id,
                "verification": "Verified"
            }
            
            # Add user context if available
            if user_context.get("user_id"):
                minimal_payload["created_by"] = user_context["user_id"]
            if user_context.get("current_company"):
                minimal_payload["created_by_company"] = user_context["current_company"]
            
            # Add trip ID if available
            if additional_data and additional_data.get("trip_id"):
                minimal_payload["trip_id"] = additional_data["trip_id"]
            
            # Add basic sender/receiver if we have the details
            if consigner_details.get("id"):
                minimal_payload["sender"] = {
                    "sender_person": consigner_details["id"],
                    "name": consigner_details.get("name", ""),
                    "sender_company": consigner_details.get("company_id", ""),
                    "gstin": consigner_details.get("gstin", "")
                }
            
            if consignee_details.get("id"):
                minimal_payload["receiver"] = {
                    "receiver_person": consignee_details["id"],
                    "name": consignee_details.get("name", ""),
                    "receiver_company": consignee_details.get("company_id", ""),
                    "gstin": consignee_details.get("gstin", "")
                }
            
            return minimal_payload
    
    async def _get_partner_company_details(self, partner_id: str) -> Dict[str, Any]:
        """Get company details for a partner using getUserCompany API"""
        if not partner_id:
            return {"success": False, "error": "No partner ID provided"}
        
        try:
            import httpx
            
            # Build the API URL
            api_url = f"https://35.244.19.78:8042/get_user_companies"
            params = {"user_id": partner_id}
            
            print(f"ParcelUpdateAgent: Getting company details for partner: {partner_id}")
            
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                # Use Basic Auth
                auth = (self.auth_config["username"], self.auth_config["password"])
                
                response = await client.get(api_url, params=params, auth=auth)
                
                if response.status_code == 200:
                    data = response.json()
                    companies = data.get("companies", []) if isinstance(data, dict) else []
                    
                    print(f"ParcelUpdateAgent: Found {len(companies)} companies for partner {partner_id}")
                    
                    return {
                        "success": True,
                        "companies": companies,
                        "total": len(companies)
                    }
                else:
                    print(f"ParcelUpdateAgent: Failed to get companies for partner {partner_id}: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API call failed with status {response.status_code}",
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            print(f"ParcelUpdateAgent: Exception getting company details for partner {partner_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Exception: {str(e)}"
            }
    
    def _build_success_message(self, consigner_details: Dict[str, Any], 
                             consignee_details: Dict[str, Any], parcel_id: str) -> str:
        """Build success message for parcel update"""
        message = "🎉 **Parcel Updated Successfully!**\n\n"
        
        message += f"📦 **Parcel ID:** {parcel_id}\n\n"
        
        if consigner_details:
            message += "**CONSIGNER (Sender) Updated:**\n"
            message += f"• Name: {consigner_details.get('name', 'N/A')}\n"
            message += f"• Location: {consigner_details.get('city', 'N/A')}\n"
            message += f"• ID: {consigner_details.get('id', 'N/A')}\n\n"
        
        if consignee_details:
            message += "**CONSIGNEE (Receiver) Updated:**\n"
            message += f"• Name: {consignee_details.get('name', 'N/A')}\n"
            message += f"• Location: {consignee_details.get('city', 'N/A')}\n"
            message += f"• ID: {consignee_details.get('id', 'N/A')}\n\n"
        
        message += "✅ **Parcel is now ready with complete consigner/consignee information!**"
        
        return message
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_supported_intents(self) -> List[APIIntent]:
        """Return list of supported intents"""
        return [APIIntent.UPDATE, APIIntent.READ, APIIntent.CREATE]
    
    async def handle_intent(self, intent: APIIntent, data: Dict[str, Any]) -> APIResponse:
        """Handle intent - delegates to execute method"""
        return await self.execute(intent, data)
    
    def validate_payload(self, intent: APIIntent, data: Dict[str, Any]) -> Optional[str]:
        """Validate payload for specific intent"""
        if intent in [APIIntent.UPDATE, APIIntent.READ, APIIntent.CREATE]:
            parcel_id = data.get("parcel_id")
            if not parcel_id:
                return "parcel_id is required for parcel operations"
        return None