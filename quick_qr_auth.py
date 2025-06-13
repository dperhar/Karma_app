#!/usr/bin/env python3
import requests
import time
import urllib.parse

def generate_and_monitor_qr():
    """Generate QR code and monitor for authentication."""
    base_url = "http://localhost:8000/api/v1/telegram/auth"
    
    print("🚀 Generating QR code...")
    
    # Generate QR code
    response = requests.post(f"{base_url}/qr-code")
    if not response.ok:
        print(f"❌ Failed to generate QR: {response.text}")
        return
    
    data = response.json()
    if not data.get("success"):
        print(f"❌ QR generation failed: {data.get('message')}")
        return
    
    token = data["data"]["token"]
    encoded_token = urllib.parse.quote(token)
    qr_url = f"tg://login?token={encoded_token}"
    
    print(f"\n🔥 QR CODE GENERATED!")
    print(f"Token: {token}")
    print(f"URL: {qr_url}")
    print(f"\n⚡ SCAN THIS QR CODE IMMEDIATELY WITH TELEGRAM!")
    print(f"📱 Telegram → Settings → Privacy & Security → Log in with Telegram → Scan QR Code")
    print(f"\n⏱️  Monitoring for authentication...")
    
    # Monitor for authentication
    for i in range(15):  # Check for 30 seconds
        time.sleep(2)
        
        check_response = requests.post(
            f"{base_url}/check",
            json={"token": token}
        )
        
        if check_response.ok:
            check_data = check_response.json()
            print(f"Check #{i+1}: {check_data.get('message', 'Unknown status')}")
            
            if check_data.get("success") and check_data.get("data", {}).get("status") == "success":
                print("🎉 AUTHENTICATION SUCCESSFUL!")
                print(f"User ID: {check_data['data'].get('user_id')}")
                return True
                
        else:
            print(f"Check #{i+1}: HTTP Error {check_response.status_code}")
    
    print("⏰ QR code expired. Need to generate a new one.")
    return False

if __name__ == "__main__":
    while True:
        success = generate_and_monitor_qr()
        if success:
            break
        
        print("\n🔄 Generating new QR code...")
        time.sleep(1) 