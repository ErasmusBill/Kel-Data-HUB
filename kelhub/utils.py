import os
import requests
from typing import Dict, List, Optional
from .models import DataBundle

BASE_URL = os.getenv("API_BASE_URL", "https://api.datamartgh.com/api/developer")
API_KEY = os.getenv("API_KEY")

headers = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}


def get_data_plans(network: str) -> List[Dict]:
    params = {"network": network}
    
    try:
        response = requests.get(f"{BASE_URL}/data-packages",params=params,headers=headers,timeout=10)
        response.raise_for_status()
    
        data = response.json()
        
        if data.get("status") == "success":             
            return data.get("data", [])
        
        print(f"API returned non-success status: {data}")
        return []
        
    except requests.exceptions.Timeout:
        print("API request timed out")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data plans: {e}")
        return []


def purchase_data(phone_number: str, network: str, amount: float, capacity: str) -> Dict:
    payload = {
        "phone_number": phone_number,
        "network": network,
        "amount": str(amount),
        "capacity": capacity,
    }
    
    try:
        response = requests.post(f"{BASE_URL}/purchase",json=payload,headers=headers,timeout=30)
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "Request timed out. Please try again."
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Purchase failed: {str(e)}"
        }


def sync_data_bundles(network_key: str, network_obj) -> int:  
    api_data = get_data_plans(network_key)
    synced_count = 0
    
    for plan in api_data:
        try:
            DataBundle.objects.update_or_create(
                network=network_obj,
                plan_code=f"{plan['capacity']}GB",
                defaults={
                    'capacity': f"{plan['capacity']}GB",
                    'mb': plan['mb'],
                    'price': float(plan['price']),
                    'is_active': True
                }
            )
            synced_count += 1
        except Exception as e:
            print(f"Error syncing bundle: {e}")
    
    return synced_count

