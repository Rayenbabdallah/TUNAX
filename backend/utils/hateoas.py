"""
HATEOAS (Hypermedia as the Engine of Application State) Helper
Adds hypermedia links to API responses for REST Level 3 maturity
"""
from flask import url_for
from flask_jwt_extended import get_jwt_identity
from models.user import User, UserRole


class HATEOASBuilder:
    """Builder for generating HATEOAS links in API responses"""
    
    @staticmethod
    def get_current_user():
        """Get current authenticated user"""
        try:
            user_id = get_jwt_identity()
            return User.query.get(user_id)
        except:
            return None
    
    @staticmethod
    def add_property_links(property_obj, include_actions=True):
        """
        Add HATEOAS links to property resource
        
        Args:
            property_obj: Property model instance
            include_actions: Whether to include action links (update, delete)
        
        Returns:
            dict: Links dictionary to add to response
        """
        links = {
            "self": {
                "href": f"/api/v1/tib/properties/{property_obj.id}",
                "method": "GET"
            },
            "taxes": {
                "href": f"/api/v1/tib/properties/{property_obj.id}/taxes",
                "method": "GET",
                "description": "Get all taxes for this property"
            }
        }
        
        if include_actions:
            current_user = HATEOASBuilder.get_current_user()
            
            # Owner can update/delete
            if current_user and current_user.id == property_obj.owner_id:
                links["update"] = {
                    "href": f"/api/v1/tib/properties/{property_obj.id}",
                    "method": "PUT",
                    "description": "Update property details"
                }
                links["delete"] = {
                    "href": f"/api/v1/tib/properties/{property_obj.id}",
                    "method": "DELETE",
                    "description": "Delete this property"
                }
            
            # Agent/Inspector can verify
            if current_user and current_user.role in [UserRole.INSPECTOR, UserRole.MUNICIPAL_AGENT]:
                if property_obj.status.value == "declared":
                    links["verify"] = {
                        "href": f"/api/v1/agent/verify/property/{property_obj.id}",
                        "method": "POST",
                        "description": "Verify property declaration"
                    }
            
            # Link to owner profile
            links["owner"] = {
                "href": f"/api/v1/auth/users/{property_obj.owner_id}",
                "method": "GET",
                "description": "View property owner details"
            }
        
        return links
    
    @staticmethod
    def add_land_links(land_obj, include_actions=True):
        """
        Add HATEOAS links to land resource
        
        Args:
            land_obj: Land model instance
            include_actions: Whether to include action links
        
        Returns:
            dict: Links dictionary
        """
        links = {
            "self": {
                "href": f"/api/v1/ttnb/lands/{land_obj.id}",
                "method": "GET"
            },
            "taxes": {
                "href": f"/api/v1/ttnb/lands/{land_obj.id}/taxes",
                "method": "GET",
                "description": "Get all taxes for this land"
            }
        }
        
        if include_actions:
            current_user = HATEOASBuilder.get_current_user()
            
            # Owner can update/delete
            if current_user and current_user.id == land_obj.owner_id:
                links["update"] = {
                    "href": f"/api/v1/ttnb/lands/{land_obj.id}",
                    "method": "PUT",
                    "description": "Update land details"
                }
                links["delete"] = {
                    "href": f"/api/v1/ttnb/lands/{land_obj.id}",
                    "method": "DELETE",
                    "description": "Delete this land"
                }
            
            # Agent/Inspector can verify
            if current_user and current_user.role in [UserRole.INSPECTOR, UserRole.MUNICIPAL_AGENT]:
                if land_obj.status.value == "declared":
                    links["verify"] = {
                        "href": f"/api/v1/agent/verify/land/{land_obj.id}",
                        "method": "POST",
                        "description": "Verify land declaration"
                    }
            
            links["owner"] = {
                "href": f"/api/v1/auth/users/{land_obj.owner_id}",
                "method": "GET",
                "description": "View land owner details"
            }
        
        return links
    
    @staticmethod
    def add_tax_links(tax_obj, resource_type="property"):
        """
        Add HATEOAS links to tax resource
        
        Args:
            tax_obj: Tax model instance
            resource_type: "property" or "land"
        
        Returns:
            dict: Links dictionary
        """
        links = {
            "self": {
                "href": f"/api/v1/taxes/{tax_obj.id}",
                "method": "GET"
            }
        }
        
        # Link back to property/land
        if resource_type == "property" and tax_obj.property_id:
            links["property"] = {
                "href": f"/api/v1/tib/properties/{tax_obj.property_id}",
                "method": "GET",
                "description": "View related property"
            }
        elif resource_type == "land" and tax_obj.land_id:
            links["land"] = {
                "href": f"/api/v1/ttnb/lands/{tax_obj.land_id}",
                "method": "GET",
                "description": "View related land"
            }
        
        # Payment actions based on status
        if tax_obj.status.value == "pending" and tax_obj.is_payable:
            links["pay"] = {
                "href": "/api/v1/payments/pay",
                "method": "POST",
                "description": "Make payment for this tax",
                "body": {
                    "tax_id": tax_obj.id,
                    "amount": float(tax_obj.tax_amount),
                    "method": "card|bank_transfer|cash|e_dinar"
                }
            }
        
        if tax_obj.status.value == "paid":
            links["receipt"] = {
                "href": f"/api/v1/payments/receipt/{tax_obj.id}",
                "method": "GET",
                "description": "Download payment receipt"
            }
        
        # Dispute option
        current_user = HATEOASBuilder.get_current_user()
        if current_user and tax_obj.status.value in ["pending", "overdue"]:
            links["dispute"] = {
                "href": "/api/v1/disputes/",
                "method": "POST",
                "description": "Submit a dispute for this tax",
                "body": {
                    "tax_id": tax_obj.id,
                    "reason": "string",
                    "description": "string"
                }
            }
        
        return links
    
    @staticmethod
    def add_payment_links(payment_obj):
        """
        Add HATEOAS links to payment resource
        
        Args:
            payment_obj: Payment model instance
        
        Returns:
            dict: Links dictionary
        """
        links = {
            "self": {
                "href": f"/api/v1/payments/{payment_obj.id}",
                "method": "GET"
            },
            "receipt": {
                "href": f"/api/v1/payments/receipt/{payment_obj.id}",
                "method": "GET",
                "description": "Download payment receipt"
            }
        }
        
        # Link to related tax
        if payment_obj.tax_id:
            links["tax"] = {
                "href": f"/api/v1/taxes/{payment_obj.tax_id}",
                "method": "GET",
                "description": "View related tax"
            }
        
        # Link to attestation
        links["attestation"] = {
            "href": f"/api/v1/payments/attestation/{payment_obj.user_id}",
            "method": "GET",
            "description": "Get tax compliance attestation"
        }
        
        return links
    
    @staticmethod
    def add_dispute_links(dispute_obj):
        """
        Add HATEOAS links to dispute resource
        
        Args:
            dispute_obj: Dispute model instance
        
        Returns:
            dict: Links dictionary
        """
        links = {
            "self": {
                "href": f"/api/v1/disputes/{dispute_obj.id}",
                "method": "GET"
            }
        }
        
        current_user = HATEOASBuilder.get_current_user()
        
        # Link to related tax
        if dispute_obj.tax_id:
            links["tax"] = {
                "href": f"/api/v1/taxes/{dispute_obj.tax_id}",
                "method": "GET",
                "description": "View disputed tax"
            }
        
        # State-based actions
        if dispute_obj.status.value == "pending":
            # Contentieux officer can assign
            if current_user and current_user.role == UserRole.CONTENTIEUX_OFFICER:
                links["assign"] = {
                    "href": f"/api/v1/disputes/{dispute_obj.id}/assign",
                    "method": "PATCH",
                    "description": "Assign dispute to officer"
                }
        
        if dispute_obj.status.value == "assigned":
            # Assigned officer can review
            if current_user and dispute_obj.assigned_to == current_user.id:
                links["commission_review"] = {
                    "href": f"/api/v1/disputes/{dispute_obj.id}/commission-review",
                    "method": "PATCH",
                    "description": "Submit for commission review"
                }
        
        if dispute_obj.status.value == "commission_review":
            # Contentieux officer can make decision
            if current_user and current_user.role == UserRole.CONTENTIEUX_OFFICER:
                links["decision"] = {
                    "href": f"/api/v1/disputes/{dispute_obj.id}/decision",
                    "method": "PATCH",
                    "description": "Make final decision",
                    "body": {
                        "decision": "approved|rejected",
                        "notes": "string"
                    }
                }
        
        if dispute_obj.status.value == "rejected":
            # Claimant can appeal
            if current_user and dispute_obj.claimant_id == current_user.id:
                links["appeal"] = {
                    "href": f"/api/v1/disputes/{dispute_obj.id}/appeal",
                    "method": "POST",
                    "description": "Submit appeal to higher authority",
                    "body": {
                        "appeal_reason": "string"
                    }
                }
        
        return links
    
    @staticmethod
    def add_permit_links(permit_obj):
        """
        Add HATEOAS links to permit resource
        
        Args:
            permit_obj: Permit model instance
        
        Returns:
            dict: Links dictionary
        """
        links = {
            "self": {
                "href": f"/api/v1/permits/{permit_obj.id}",
                "method": "GET"
            }
        }
        
        current_user = HATEOASBuilder.get_current_user()
        
        # Link to related property
        if permit_obj.property_id:
            links["property"] = {
                "href": f"/api/v1/tib/properties/{permit_obj.property_id}",
                "method": "GET",
                "description": "View related property"
            }
        
        # State-based actions
        if permit_obj.status == "pending":
            # Urbanism officer can decide
            if current_user and current_user.role == UserRole.URBANISM_OFFICER:
                links["decide"] = {
                    "href": f"/api/v1/permits/{permit_obj.id}/decide",
                    "method": "PATCH",
                    "description": "Approve or deny permit",
                    "body": {
                        "decision": "approved|denied",
                        "notes": "string"
                    }
                }
        
        if permit_obj.status == "approved":
            links["download"] = {
                "href": f"/api/v1/permits/{permit_obj.id}/certificate",
                "method": "GET",
                "description": "Download permit certificate"
            }
        
        # Eligibility check
        if current_user:
            links["check_eligibility"] = {
                "href": f"/api/v1/payments/check-permit-eligibility/{current_user.id}",
                "method": "GET",
                "description": "Check if eligible for permit (taxes paid)"
            }
        
        return links
    
    @staticmethod
    def add_links_to_response(data, links):
        """
        Add _links key to response data
        
        Args:
            data: Response dictionary
            links: Links dictionary
        
        Returns:
            dict: Response with _links added
        """
        if isinstance(data, dict):
            data["_links"] = links
        return data
