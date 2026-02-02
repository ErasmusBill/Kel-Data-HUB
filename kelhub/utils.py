import os
import requests
import time
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from .models import DataBundle, TransactionLog
from django.conf import settings

# DataMart API Configuration
BASE_URL = os.getenv("API_BASE_URL", "https://datamartbackened.onrender.com/api/developer")
API_KEY = os.getenv("API_KEY")

# Paystack Configuration
PAYSTACK_SECRET_KEY = getattr(settings, 'PAYSTACK_SECRET_KEY', os.getenv('PAYSTACK_SECRET_KEY'))
PAYSTACK_PUBLIC_KEY = getattr(settings, 'PAYSTACK_PUBLIC_KEY', os.getenv('PAYSTACK_PUBLIC_KEY'))
PAYSTACK_BASE_URL = "https://api.paystack.co"




def initialize_paystack_payment(email: str,phone_number:str,amount: Decimal,callback_url: str,reference: Optional[str] = None,metadata: Optional[Dict] = None,channels: Optional[List[str]] = None) -> Dict:
    
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    
    amount_pesewas = int(amount * 100)
    
    payload = {
        "email": email,
        "phone_number":phone_number,
        "amount": amount_pesewas,
        "currency": "GHS",  
        "callback_url": callback_url,
        "channels": channels or ["card", "mobile_money", "bank"],
    }
    
    
    if reference:
        payload["reference"] = reference
    
    
    if metadata:
        payload["metadata"] = metadata
    
    try:
        response = requests.post(f"{PAYSTACK_BASE_URL}/transaction/initialize",json=payload,headers=headers,timeout=30)
        
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get("status"):
            return {
                "status": "success",
                "data": response_data.get("data", {}),
                "message": response_data.get("message", "Payment initialized successfully")
            }
        else:
            return {
                "status": "error",
                "message": response_data.get("message", "Failed to initialize payment"),
                "raw_response": response_data
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Payment initialization failed: {str(e)}"
        }


def verify_paystack_payment(reference: str) -> Dict:
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",headers=headers,timeout=30)
        
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get("status"):
            data = response_data.get("data", {})
            
            payment_successful = data.get("status") == "success"
            
            return {
                "status": "success",
                "verified": payment_successful,
                "amount": Decimal(str(data.get("amount", 0))) / 100,  
                "reference": data.get("reference"),
                "channel": data.get("channel"),
                "paid_at": data.get("paid_at"),
                "gateway_response": data.get("gateway_response"),
                "customer_email": data.get("customer", {}).get("email"),
                "metadata": data.get("metadata", {}),
                "raw_data": data
            }
        else:
            return {
                "status": "error",
                "verified": False,
                "message": response_data.get("message", "Payment verification failed"),
                "raw_response": response_data
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "verified": False,
            "message": f"Verification request failed: {str(e)}"
        }


def charge_mobile_money(email: str,amount: Decimal,phone_number: str,provider: str = "mtn",reference: Optional[str] = None,metadata: Optional[Dict] = None) -> Dict:
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    amount_pesewas = int(amount * 100)
    
    payload = {
        "email": email,
        "amount": amount_pesewas,
        "currency": "GHS",
        "mobile_money": {
            "phone": phone_number,
            "provider": provider  
        }
    }
    
    if reference:
        payload["reference"] = reference
    
    if metadata:
        payload["metadata"] = metadata
    
    try:
        response = requests.post(f"{PAYSTACK_BASE_URL}/charge",json=payload,headers=headers,timeout=30)
        
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get("status"):
            return {
                "status": "success",
                "data": response_data.get("data", {}),
                "message": response_data.get("message", "Charge initiated")
            }
        else:
            return {
                "status": "error",
                "message": response_data.get("message", "Charge failed"),
                "raw_response": response_data
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Charge request failed: {str(e)}"
        }



def get_headers():
    """Get headers for DataMart API requests"""
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }


def get_data_plans(network: Optional[str] = None):
    try:
        params = {"network": network} if network else {}
        
        response = requests.get(f"{BASE_URL}/data-packages",params=params,headers=get_headers(),timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "success":
            return data.get("data", [] if network else {})
        
        print(f"API returned non-success status: {data}")
        return [] if network else {}
        
    except requests.exceptions.Timeout:
        print("API request timed out")
        return [] if network else {}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data plans: {e}")
        return [] if network else {}


def purchase_data(phone_number: str,network: str,capacity: str,order=None,gateway: str = "wallet") -> Tuple[bool, Dict]:
  
   
    capacity_clean = str(capacity).replace("GB", "").replace("gb", "").strip()
    
    payload = {
        "phoneNumber": phone_number,
        "network": network,
        "capacity": capacity_clean,
        "gateway": gateway
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(f"{BASE_URL}/purchase",json=payload,headers=get_headers(),timeout=30)
        
        response_time = time.time() - start_time
        response_data = response.json()
        
        if order:
            TransactionLog.objects.create(
                order=order,
                endpoint="/api/developer/purchase",
                request_method="POST",
                request_payload=payload,
                request_headers={"X-API-Key": "***hidden***"},
                response_payload=response_data,
                status_code=response.status_code,
                response_time=response_time
            )
        
        if response.status_code == 200 and response_data.get("status") == "success":
            return True, response_data
        else:
            error_msg = response_data.get("message", "Unknown error occurred")
            return False, {
                "status": "error",
                "message": error_msg,
                "raw_response": response_data
            }
        
    except requests.exceptions.Timeout:
        response_time = time.time() - start_time
        error_response = {
            "status": "error",
            "message": "Request timed out. Please try again."
        }
        
        if order:
            TransactionLog.objects.create(
                order=order,
                endpoint="/api/developer/purchase",
                request_method="POST",
                request_payload=payload,
                response_payload=error_response,
                status_code=0,
                response_time=response_time,
                error_message="Timeout"
            )
        
        return False, error_response
        
    except requests.exceptions.RequestException as e:
        response_time = time.time() - start_time
        error_response = {
            "status": "error",
            "message": f"Purchase failed: {str(e)}"
        }
        
        if order:
            TransactionLog.objects.create(
                order=order,
                endpoint="/api/developer/purchase",
                request_method="POST",
                request_payload=payload,
                response_payload=error_response,
                status_code=0,
                response_time=response_time,
                error_message=str(e)
            )
        
        return False, error_response


def sync_data_bundles(network_key: str, network_obj) -> int:
    """Sync data bundles from DataMart API to database"""
    api_data = get_data_plans(network_key)
    
    if not isinstance(api_data, list):
        print(f"Unexpected API response format for {network_key}")
        return 0
    
    synced_count = 0
    
    for plan in api_data:
        try:
            capacity = str(plan['capacity'])
            mb = str(plan['mb'])
            price = Decimal(str(plan['price']))
            
            DataBundle.objects.update_or_create(
                network=network_obj,
                capacity=capacity,
                defaults={
                    'mb': mb,
                    'price': price,
                    'plan_code': f"{capacity}GB",
                    'is_active': True
                }
            )
            synced_count += 1
            
        except Exception as e:
            print(f"Error syncing bundle {plan.get('capacity', 'unknown')}: {e}")
    
    return synced_count


def sync_all_bundles() -> Dict[str, int]:
    """Sync data bundles for all networks"""
    from .models import Network
    
    results = {}
    
    try:
        all_plans = get_data_plans()
        
        if not isinstance(all_plans, dict):
            print("Unexpected API response format")
            return results
        
        for network_key, plans in all_plans.items():
            try:
                network_obj = Network.objects.get(key=network_key)
                
                synced_count = 0
                for plan in plans:
                    try:
                        capacity = str(plan['capacity'])
                        mb = str(plan['mb'])
                        price = Decimal(str(plan['price']))
                        
                        DataBundle.objects.update_or_create(
                            network=network_obj,
                            capacity=capacity,
                            defaults={
                                'mb': mb,
                                'price': price,
                                'plan_code': f"{capacity}GB",
                                'is_active': True
                            }
                        )
                        synced_count += 1
                        
                    except Exception as e:
                        print(f"Error syncing {network_key} bundle: {e}")
                
                results[network_key] = synced_count
                
            except Network.DoesNotExist:
                print(f"Network {network_key} not found in database")
                results[network_key] = 0
    
    except Exception as e:
        print(f"Error syncing all bundles: {e}")
    
    return results


def validate_phone_number(phone_number: str) -> Optional[str]:
   
    if not phone_number:
        return None
    
    cleaned = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    if cleaned.startswith("+233"):
        if len(cleaned) == 13:
            return "0" + cleaned[4:]
    elif cleaned.startswith("233"):
        if len(cleaned) == 12:
            return "0" + cleaned[3:]
    elif cleaned.startswith("0"):
        if len(cleaned) == 10:
            return cleaned
    elif len(cleaned) == 9:
        return "0" + cleaned
    
    return None


def generate_guest_email(phone_number: str) -> str:
   
    clean_phone = phone_number.lstrip('0').replace('+233', '').replace('233', '')
    return f"guest_{clean_phone}@datahub.temp"


def detect_mobile_money_provider(phone_number: str) -> str:
    """
    Detect mobile money provider from phone number
    
    Args:
        phone_number: Phone number (format: 0551234567)
    
    Returns:
        Provider code (mtn, tgo, vod)
    """
    if not phone_number or len(phone_number) < 4:
        return "mtn"  
    
    # Get the network prefix (first 3 digits after 0)
    prefix = phone_number[1:4] if phone_number.startswith('0') else phone_number[:3]
    
  
    mtn_prefixes = ['024', '054', '055', '059']
    
    vod_prefixes = ['020', '050']
   
    tgo_prefixes = ['027', '057', '026', '056']
    
    if prefix in mtn_prefixes:
        return "mtn"
    elif prefix in vod_prefixes:
        return "vod"
    elif prefix in tgo_prefixes:
        return "tgo"
    else:
        return "mtn"  # Default to MTN


def verify_api_key() -> bool:
    """Verify DataMart API key is valid"""
    try:
        response = requests.get(f"{BASE_URL}/data-packages",headers=get_headers(),params={"network": "YELLO"},timeout=5)
        return response.status_code in [200, 201]
    except requests.exceptions.RequestException:
        return False