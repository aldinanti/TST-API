"""
Script untuk testing EV Charging Management API
Run setelah server berjalan: python test_api.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
token = None

def print_response(response, title):
    """Helper function untuk print response dengan format rapi"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, default=str))
    except:
        print(response.text)

def test_register():
    """Test registrasi user baru"""
    url = f"{BASE_URL}/auth/register"
    data = {
        "name": "Test User",
        "email": f"test_{datetime.now().timestamp()}@example.com",
        "phone": "08123456789",
        "password": "password123"
    }
    response = requests.post(url, json=data)
    print_response(response, "1. REGISTER USER")
    return response.json()

def test_login(email):
    """Test login dan dapatkan token"""
    global token
    url = f"{BASE_URL}/auth/login"
    data = {
        "email": email,
        "password": "password123"
    }
    response = requests.post(url, json=data)
    print_response(response, "2. LOGIN")
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"\nToken saved: {token[:50]}...")
    return response.json()

def test_get_me():
    """Test get current user"""
    url = f"{BASE_URL}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print_response(response, "3. GET CURRENT USER")
    return response.json()

def test_create_vehicle():
    """Test create vehicle"""
    url = f"{BASE_URL}/vehicles"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "nomor_plat": f"B{int(datetime.now().timestamp())}XYZ",
        "battery_capacity": 75.0,
        "connector_port": {
            "standard_name": "CCS Type 2",
            "max_power_supported": 150.0
        }
    }
    response = requests.post(url, json=data, headers=headers)
    print_response(response, "4. CREATE VEHICLE")
    return response.json()

def test_get_my_vehicles():
    """Test get user's vehicles"""
    url = f"{BASE_URL}/vehicles/me"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print_response(response, "5. GET MY VEHICLES")
    return response.json()

def test_create_station():
    """Test create station"""
    url = f"{BASE_URL}/stations"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "station_operator": "PLN Icon Plus",
        "location": {
            "latitude": -6.914744,
            "longitude": 107.609810,
            "address": "Jl. Ganesha No.10, Bandung"
        },
        "connector_list": ["CCS Type 2", "CHAdeMO", "Type 2"]
    }
    response = requests.post(url, json=data, headers=headers)
    print_response(response, "6. CREATE STATION")
    return response.json()

def test_list_stations():
    """Test list all stations (public)"""
    url = f"{BASE_URL}/stations"
    response = requests.get(url)
    print_response(response, "7. LIST STATIONS")
    return response.json()

def test_create_station_asset(station_id):
    """Test create station asset"""
    url = f"{BASE_URL}/station-assets"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "station_id": station_id,
        "model": "ABB Terra 54 CJG",
        "connector_port": {
            "standard_name": "CCS Type 2",
            "max_power_supported": 50.0
        }
    }
    response = requests.post(url, json=data, headers=headers)
    print_response(response, "8. CREATE STATION ASSET")
    return response.json()

def test_get_station_detail(station_id):
    """Test get station with assets"""
    url = f"{BASE_URL}/stations/{station_id}"
    response = requests.get(url)
    print_response(response, "9. GET STATION DETAIL")
    return response.json()

def test_start_charging_session(assets_id):
    """Test start charging session"""
    url = f"{BASE_URL}/charging-sessions/start"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "assets_id": assets_id
    }
    response = requests.post(url, json=data, headers=headers)
    print_response(response, "10. START CHARGING SESSION")
    return response.json()

def test_get_active_session():
    """Test get active session"""
    url = f"{BASE_URL}/charging-sessions/me/active"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print_response(response, "11. GET ACTIVE SESSION")
    return response.json()

def test_stop_charging_session(session_id):
    """Test stop charging session"""
    import time
    print("\nWaiting 3 seconds to simulate charging...")
    time.sleep(3)
    
    url = f"{BASE_URL}/charging-sessions/{session_id}/stop"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"kwh_consumed": 15.5}
    response = requests.post(url, headers=headers, params=params)
    print_response(response, "12. STOP CHARGING SESSION")
    return response.json()

def test_get_session_detail(session_id):
    """Test get session detail with relations"""
    url = f"{BASE_URL}/charging-sessions/{session_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print_response(response, "13. GET SESSION DETAIL")
    return response.json()

def test_get_my_invoices():
    """Test get user's invoices"""
    url = f"{BASE_URL}/invoices/me"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print_response(response, "14. GET MY INVOICES")
    return response.json()

def test_update_invoice_payment(invoice_id):
    """Test update invoice payment"""
    url = f"{BASE_URL}/invoices/{invoice_id}/payment"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "payment_status": "Completed",
        "payment_method": "credit_card"
    }
    response = requests.patch(url, json=data, headers=headers)
    print_response(response, "15. UPDATE INVOICE PAYMENT")
    return response.json()

def test_get_my_sessions():
    """Test get all user's sessions"""
    url = f"{BASE_URL}/charging-sessions/me"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print_response(response, "16. GET MY ALL SESSIONS")
    return response.json()

def main():
    """Main test flow"""
    print("\n" + "="*60)
    print("EV CHARGING MANAGEMENT API - INTEGRATION TEST")
    print("="*60)
    
    try:
        # 1. Account Context
        user = test_register()
        test_login(user["email"])
        test_get_me()
        test_create_vehicle()
        test_get_my_vehicles()
        
        # 2. Station Management Context
        station = test_create_station()
        test_list_stations()
        asset = test_create_station_asset(station["station_id"])
        test_get_station_detail(station["station_id"])
        
        # 3. Charging Session Context
        session = test_start_charging_session(asset["asset_id"])
        test_get_active_session()
        test_stop_charging_session(session["session_id"])
        test_get_session_detail(session["session_id"])
        
        # 4. Billing Context
        invoices = test_get_my_invoices()
        if invoices:
            test_update_invoice_payment(invoices[0]["invoice_id"])
        
        test_get_my_sessions()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)
        
    except Exception as e:
        print(f"\n Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()