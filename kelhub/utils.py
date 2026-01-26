import os
import requests

BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")

headers = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def purchase_data(self,phone_number,network,amount,capacity):
    payload = {
        "phone_number": phone_number,
        "network": network,
        "amount": amount,
        "capacity": capacity,
    }
    try:
        response = requests.post(f"{BASE_URL}/purchase", json=payload, headers=headers)
        return response.json()
    except requests.exceptions.RequestException as e:
        return response.raise_for_status()
    

def get_data_plans(self,network):
    params = {
        "network": network
    }
    try:
        response = requests.get(f"{BASE_URL}/data-packages", params=params, headers=headers)
        return response.json()
    except requests.exceptions.RequestException as e:
        return response.raise_for_status()
    