from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
import requests

app = Flask(__name__)

# =========================================================================
# ADVANCED SYSTEM CONFIGURATION MATRIX
# =========================================================================
TELEGRAM_TOKEN = "8785171952:AAHoL6q374HXrDct9WWFnvJmKz1tHVcvBgk"
TELEGRAM_CHAT_ID = "8841335760"
LOG_FILE = "logs/triggers.json"

def get_geolocation(ip_address):
    """Queries a free public API to fetch real-time geographic variables."""
    # Skip geolocation query if testing locally on 127.0.0.1 loopback
    if ip_address in ["127.0.0.1", "localhost"]:
        return {"country": "Local Lab", "city": "Loopback", "isp": "VirtualBox Internal"}
    
    try:
        # Querying ip-api.com without an API key for school development
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country", "Unknown"),
                    "city": data.get("city", "Unknown"),
                    "isp": data.get("isp", "Unknown")
                }
    except Exception as e:
        print(f"[-] Geolocation Enrichment Lookup Failed: {e}")
        
    return {"country": "Unknown", "city": "Unknown", "isp": "Unknown"}

def send_telegram_alert(source_ip, user_agent, geo_info, payload_data):
    """Dispatches an enriched, highly detailed alert notification to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    alert_message = (
        "🚨 **HONEYTOKEN TRIGGERED!** 🚨\n\n"
        f"🌐 **Attacker IP:** `{source_ip}`\n"
        f"⏱️ **Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"📍 **Location:** {geo_info['city']}, {geo_info['country']}\n"
        f"🏢 **ISP Provider:** {geo_info['isp']}\n"
        f"📱 **User Agent:** `{user_agent}`\n\n"
        f"📦 **Payload Content:** `{json.dumps(payload_data)}`\n\n"
        "⚠️ *Warning: Malicious activity logged across environment.*"
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": alert_message,
        "parse_mode": "Markdown"
    }
    
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[-] Failed to establish connection to Telegram Gateway: {e}")

def log_to_json(data):
    """Appends full enriched event records into triggers.json array file."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try: logs = json.load(f)
            except json.JSONDecodeError: logs = []
    else:
        logs = []
        
    logs.append(data)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

@app.route('/webhook', methods=['POST'])
def mock_webhook_listener():
    """Ingest payload, parse headers, fetch geolocation, log, and alert."""
    content = request.get_json(silent=True) or {}
    
    # Capture the real IP when running behind the Ngrok gateway proxy
    if request.headers.getlist("X-Forwarded-For"):
        source_ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        source_ip = request.remote_addr
        
    user_agent = request.headers.get('User-Agent', 'Unknown Browser')
    
    # Step 1: Perform the Geolocation enrichment lookup
    geo_info = get_geolocation(source_ip)
    
    # Step 2: Structure compilation log data payload
    compiled_log = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_ip": source_ip,
        "user_agent": user_agent,
        "location": geo_info,
        "payload": content
    }
    
    # Step 3: Run execution pipelines
    log_to_json(compiled_log)
    send_telegram_alert(source_ip, user_agent, geo_info, content)
    
    return jsonify({"status": "logged", "message": "Enriched event recorded"}), 200

if __name__ == '__main__':
    print("[+] Framework: Initializing local JSON logging structures...")
    app.run(host='0.0.0.0', port=5000, debug=True)
