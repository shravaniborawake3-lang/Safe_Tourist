"""
SafeTrail — Smart Tourist Safety System
Backend: Flask + SQLite
Port: 5500
Run: cd Backend && python App.py
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3, os, json, hashlib, smtplib, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__, static_folder='../Frontend')
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), '../Database/safetrail.db')

# ── EMAIL CONFIG ──────────────────────────────────────────────────
SENDER_EMAIL    = "your_app_email@gmail.com"
SENDER_PASSWORD = "your_app_password_here"
EMAIL_ENABLED   = False
POLICE_EMAIL    = "navipolice.alert@gmail.com"

# ═══════════════════════════════════════════════════════════════════
# PHONE VALIDATION — FIX #1
# ═══════════════════════════════════════════════════════════════════

def validate_phone(phone: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    Accepts ONLY exactly 10 digits (strips leading +91 or 0 if present).
    """
    if not phone:
        return False, "Phone number is required"
    # Strip common Indian prefixes so +919876543210 or 09876543210 → 9876543210
    cleaned = re.sub(r'^\+91|^91|^0', '', phone.strip())
    cleaned = re.sub(r'[\s\-\(\)]', '', cleaned)  # remove spaces/dashes/parens
    if not cleaned.isdigit():
        return False, "Phone number must contain digits only"
    if len(cleaned) != 10:
        return False, f"Phone number must be exactly 10 digits (got {len(cleaned)})"
    return True, cleaned   # return normalised 10-digit string as second element

# ═══════════════════════════════════════════════════════════════════
# CITY SERVICES
# ═══════════════════════════════════════════════════════════════════
CITY_SERVICES = {
  "Vashi": [
    {"type":"hospital",  "name":"MGM Hospital Vashi",        "lat":19.0790,"lng":73.0075,"phone":"022-2765-7777","open":"24/7"},
    {"type":"hospital",  "name":"Fortis Hiranandani",         "lat":19.0730,"lng":73.0110,"phone":"022-6742-2000","open":"Open"},
    {"type":"police",    "name":"Vashi Police Station",       "lat":19.0755,"lng":73.0070,"phone":"022-2765-8200","open":"24/7"},
    {"type":"police",    "name":"Sector-17 Police Chowki",    "lat":19.0785,"lng":73.0065,"phone":"022-2765-9100","open":"24/7"},
    {"type":"pharmacy",  "name":"Apollo Pharmacy Vashi",      "lat":19.0780,"lng":73.0090,"phone":"1860-500-0101","open":"Open"},
    {"type":"pharmacy",  "name":"MedPlus Vashi",              "lat":19.0762,"lng":73.0088,"phone":"040-6715-1515","open":"Open"},
    {"type":"bank",      "name":"SBI Bank Vashi",             "lat":19.0758,"lng":73.0076,"phone":"1800-425-3800","open":"Open"},
    {"type":"bank",      "name":"HDFC Bank Vashi",            "lat":19.0770,"lng":73.0060,"phone":"1800-202-6161","open":"Open"},
    {"type":"atm",       "name":"SBI ATM Sector-17",          "lat":19.0765,"lng":73.0055,"phone":"",             "open":"24/7"},
    {"type":"hotel",     "name":"Hotel Regency Vashi",        "lat":19.0760,"lng":73.0095,"phone":"022-2765-0000","open":"Open"},
    {"type":"hotel",     "name":"OYO Rooms Vashi Station",    "lat":19.0745,"lng":73.0083,"phone":"0800-825-8258","open":"Open"},
    {"type":"restaurant","name":"Mainland China Vashi",       "lat":19.0742,"lng":73.0110,"phone":"022-6741-9999","open":"Open"},
    {"type":"transport", "name":"Vashi Railway Station",      "lat":19.0771,"lng":73.0084,"phone":"139",           "open":"24/7"},
    {"type":"transport", "name":"Vashi Bus Depot",            "lat":19.0780,"lng":73.0075,"phone":"022-2765-5050","open":"24/7"},
  ],
  "Nerul": [
    {"type":"hospital",  "name":"DY Patil Hospital Nerul",    "lat":19.0350,"lng":73.0200,"phone":"022-2771-5555","open":"24/7"},
    {"type":"hospital",  "name":"Nerul Govt Hospital",        "lat":19.0300,"lng":73.0160,"phone":"022-2771-6600","open":"24/7"},
    {"type":"police",    "name":"Nerul Police Station",       "lat":19.0315,"lng":73.0180,"phone":"022-2771-8201","open":"24/7"},
    {"type":"pharmacy",  "name":"Apollo Pharmacy Nerul",      "lat":19.0330,"lng":73.0195,"phone":"1860-500-0101","open":"Open"},
    {"type":"bank",      "name":"SBI Nerul Branch",           "lat":19.0325,"lng":73.0165,"phone":"1800-425-3800","open":"Open"},
    {"type":"atm",       "name":"HDFC ATM Nerul",             "lat":19.0318,"lng":73.0175,"phone":"",             "open":"24/7"},
    {"type":"hotel",     "name":"Hotel Nerul Executive",      "lat":19.0330,"lng":73.0200,"phone":"022-2771-0000","open":"Open"},
    {"type":"restaurant","name":"Domino's Pizza Nerul",       "lat":19.0335,"lng":73.0165,"phone":"1800-208-1234","open":"Open"},
    {"type":"transport", "name":"Nerul Railway Station",      "lat":19.0321,"lng":73.0177,"phone":"139",           "open":"24/7"},
  ],
  "Belapur": [
    {"type":"hospital",  "name":"Belapur District Hospital",  "lat":19.0160,"lng":73.0400,"phone":"022-2757-5555","open":"24/7"},
    {"type":"police",    "name":"Belapur Police Station",     "lat":19.0155,"lng":73.0370,"phone":"022-2757-8200","open":"24/7"},
    {"type":"pharmacy",  "name":"Apollo Pharmacy Belapur",    "lat":19.0148,"lng":73.0395,"phone":"1860-500-0101","open":"Open"},
    {"type":"bank",      "name":"SBI CBD Belapur",            "lat":19.0142,"lng":73.0385,"phone":"1800-425-3800","open":"Open"},
    {"type":"atm",       "name":"ICICI ATM Belapur",          "lat":19.0150,"lng":73.0390,"phone":"",             "open":"24/7"},
    {"type":"hotel",     "name":"Ramada by Wyndham",          "lat":19.0148,"lng":73.0395,"phone":"022-6730-7000","open":"Open"},
    {"type":"restaurant","name":"Food Mall Belapur",          "lat":19.0152,"lng":73.0382,"phone":"",             "open":"Open"},
    {"type":"transport", "name":"CBD Belapur Station",        "lat":19.0148,"lng":73.0389,"phone":"139",           "open":"24/7"},
  ],
  "Kharghar": [
    {"type":"hospital",  "name":"Kharghar Hospital",          "lat":19.0490,"lng":73.0700,"phone":"022-2774-5555","open":"24/7"},
    {"type":"police",    "name":"Kharghar Police Station",    "lat":19.0470,"lng":73.0680,"phone":"022-2774-8200","open":"24/7"},
    {"type":"pharmacy",  "name":"Apollo Pharmacy Kharghar",   "lat":19.0480,"lng":73.0695,"phone":"1860-500-0101","open":"Open"},
    {"type":"bank",      "name":"SBI Kharghar",               "lat":19.0475,"lng":73.0688,"phone":"1800-425-3800","open":"Open"},
    {"type":"atm",       "name":"HDFC ATM Kharghar",          "lat":19.0472,"lng":73.0695,"phone":"",             "open":"24/7"},
    {"type":"hotel",     "name":"Hotel Hilton Kharghar",      "lat":19.0478,"lng":73.0700,"phone":"022-2799-0000","open":"Open"},
    {"type":"restaurant","name":"KFC Kharghar",               "lat":19.0485,"lng":73.0672,"phone":"1800-209-2942","open":"Open"},
    {"type":"transport", "name":"Kharghar Railway Station",   "lat":19.0474,"lng":73.0692,"phone":"139",           "open":"24/7"},
  ],
  "Panvel": [
    {"type":"hospital",  "name":"Raigad Dist Hospital Panvel","lat":18.9910,"lng":73.1190,"phone":"022-2745-0101","open":"24/7"},
    {"type":"hospital",  "name":"Panvel Multispeciality",     "lat":18.9875,"lng":73.1160,"phone":"022-2740-2222","open":"Open"},
    {"type":"police",    "name":"Panvel Police Station",      "lat":18.9900,"lng":73.1168,"phone":"022-2746-8200","open":"24/7"},
    {"type":"police",    "name":"New Panvel Police Chowki",   "lat":18.9888,"lng":73.1185,"phone":"022-2746-9100","open":"24/7"},
    {"type":"pharmacy",  "name":"Apollo Pharmacy Panvel",     "lat":18.9895,"lng":73.1178,"phone":"1860-500-0101","open":"Open"},
    {"type":"bank",      "name":"SBI Panvel Main Branch",     "lat":18.9898,"lng":73.1172,"phone":"1800-425-3800","open":"Open"},
    {"type":"atm",       "name":"SBI ATM Panvel Station",     "lat":18.9892,"lng":73.1175,"phone":"",             "open":"24/7"},
    {"type":"hotel",     "name":"Hotel Presidency Panvel",    "lat":18.9905,"lng":73.1165,"phone":"022-2740-0000","open":"Open"},
    {"type":"restaurant","name":"Maratha Bhojanalaya Panvel", "lat":18.9895,"lng":73.1180,"phone":"022-2741-3333","open":"Open"},
    {"type":"transport", "name":"Panvel Railway Station",     "lat":18.9894,"lng":73.1175,"phone":"139",           "open":"24/7"},
    {"type":"transport", "name":"MSRTC Bus Depot Panvel",     "lat":18.9902,"lng":73.1160,"phone":"020-2612-5740","open":"24/7"},
  ],
  "Airoli": [
    {"type":"hospital",  "name":"Airoli Govt Hospital",       "lat":19.1565,"lng":73.0180,"phone":"022-2769-5555","open":"24/7"},
    {"type":"police",    "name":"Airoli Police Station",      "lat":19.1550,"lng":73.0162,"phone":"022-2769-8200","open":"24/7"},
    {"type":"pharmacy",  "name":"Apollo Pharmacy Airoli",     "lat":19.1558,"lng":73.0175,"phone":"1860-500-0101","open":"Open"},
    {"type":"bank",      "name":"SBI Airoli Branch",          "lat":19.1562,"lng":73.0165,"phone":"1800-425-3800","open":"Open"},
    {"type":"hotel",     "name":"Airoli Business Hotel",      "lat":19.1560,"lng":73.0180,"phone":"022-2769-4444","open":"Open"},
    {"type":"transport", "name":"Airoli Railway Station",     "lat":19.1557,"lng":73.0169,"phone":"139",           "open":"24/7"},
  ],
  "Seawoods": [
    {"type":"hospital",  "name":"Fortis Seawoods",            "lat":19.0175,"lng":73.0142,"phone":"022-6152-6000","open":"24/7"},
    {"type":"police",    "name":"Seawoods Police Station",    "lat":19.0182,"lng":73.0148,"phone":"022-2771-8300","open":"24/7"},
    {"type":"pharmacy",  "name":"Apollo Pharmacy Seawoods",   "lat":19.0190,"lng":73.0155,"phone":"1860-500-0101","open":"Open"},
    {"type":"bank",      "name":"HDFC Seawoods Grand",        "lat":19.0185,"lng":73.0145,"phone":"1800-202-6161","open":"Open"},
    {"type":"atm",       "name":"SBI ATM Seawoods Mall",      "lat":19.0188,"lng":73.0152,"phone":"",             "open":"24/7"},
    {"type":"hotel",     "name":"Novotel Seawoods",           "lat":19.0192,"lng":73.0158,"phone":"022-6152-6000","open":"Open"},
    {"type":"hotel",     "name":"Holiday Inn Seawoods",       "lat":19.0178,"lng":73.0148,"phone":"022-6666-7777","open":"Open"},
    {"type":"restaurant","name":"Pizza Hut Seawoods",         "lat":19.0180,"lng":73.0142,"phone":"1800-202-2222","open":"Open"},
    {"type":"transport", "name":"Seawoods-Darave Station",    "lat":19.0186,"lng":73.0150,"phone":"139",           "open":"24/7"},
  ],
}
for city_extra in ["Ghansoli","Turbhe","Koparkhairane","Sanpada","Juinagar","Ulwe",
                   "Dronagiri","Taloja","Kamothe","Kalamboli","New Panvel",
                   "Roadpali","Khandeshwar","Nhava Sheva","Uran","Pen"]:
    if city_extra not in CITY_SERVICES:
        CITY_SERVICES[city_extra] = []

ALL_CITIES = list(CITY_SERVICES.keys())

# ═══════════════════════════════════════════════════════════════════
# DATABASE — FIX #3 & #4
# ═══════════════════════════════════════════════════════════════════

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    # Apply schema (CREATE TABLE IF NOT EXISTS — safe to re-run)
    schema_path = os.path.join(os.path.dirname(__file__), '../Database/schema.sql')
    with open(schema_path, 'r') as f:
        c.executescript(f.read())

    # ── Seed city_services from in-memory CITY_SERVICES dict ──────
    # Only insert if table is empty (avoids duplicates on restart)
    count = conn.execute("SELECT COUNT(*) FROM city_services").fetchone()[0]
    if count == 0:
        rows = []
        for city, services in CITY_SERVICES.items():
            for svc in services:
                rows.append((
                    city,
                    svc.get("type", ""),
                    svc.get("name", ""),
                    svc.get("lat"),
                    svc.get("lng"),
                    svc.get("phone", ""),
                    svc.get("open", "Open")
                ))
        c.executemany(
            "INSERT INTO city_services (city_name,svc_type,svc_name,latitude,longitude,phone,open_hours) VALUES (?,?,?,?,?,?,?)",
            rows
        )
        conn.commit()
        print(f"\u2705 Seeded {len(rows)} city services into DB")
    else:
        print(f"\u2705 city_services already has {count} rows \u2014 skipping seed")

    conn.commit()
    conn.close()
    print("\u2705 Database ready:", DB_PATH)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def blockchain_id(data: str) -> str:
    return "0x" + hashlib.sha256(data.encode()).hexdigest()[:40]


# ═══════════════════════════════════════════════════════════════════
# EMAIL
# ═══════════════════════════════════════════════════════════════════

def send_email(to: str, subject: str, html: str) -> bool:
    if not EMAIL_ENABLED:
        print(f"[EMAIL DEMO] To:{to} | Subject:{subject}")
        return True
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL; msg['To'] = to; msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(SENDER_EMAIL, SENDER_PASSWORD)
            s.sendmail(SENDER_EMAIL, to, msg.as_string())
        print(f"✅ Email sent → {to}"); return True
    except Exception as e:
        print(f"❌ Email error: {e}"); return False

def build_email(user: dict, maps_link: str, alert_type: str) -> str:
    t = datetime.now().strftime('%d %b %Y, %I:%M %p')
    return f"""<html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px">
<div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;overflow:hidden">
  <div style="background:#ff4757;padding:26px;text-align:center">
    <h1 style="color:white;margin:0;font-size:26px">🚨 EMERGENCY SOS ALERT</h1>
    <p style="color:rgba(255,255,255,.9);margin:6px 0 0">SafeTrail — Navi Mumbai Tourist Safety</p>
  </div>
  <div style="padding:28px">
    <div style="background:#fff5f5;border:2px solid #ff4757;border-radius:8px;padding:14px;margin-bottom:18px">
      <p style="margin:0;color:#cc0000;font-weight:bold">⚠️ This person may be in danger — immediate assistance required!</p>
    </div>
    <table style="width:100%;border-collapse:collapse">
      <tr><td style="padding:7px 0;border-bottom:1px solid #eee;color:#666;width:35%"><b>👤 Name</b></td><td style="padding:7px 0;border-bottom:1px solid #eee"><b>{user.get('name','Unknown')}</b></td></tr>
      <tr><td style="padding:7px 0;border-bottom:1px solid #eee;color:#666"><b>📞 Phone</b></td><td style="padding:7px 0;border-bottom:1px solid #eee">{user.get('phone','N/A')}</td></tr>
      <tr><td style="padding:7px 0;border-bottom:1px solid #eee;color:#666"><b>🏥 Medical</b></td><td style="padding:7px 0;border-bottom:1px solid #eee">{user.get('medical','Not given')}</td></tr>
      <tr><td style="padding:7px 0;border-bottom:1px solid #eee;color:#666"><b>🏨 Address</b></td><td style="padding:7px 0;border-bottom:1px solid #eee">{user.get('address','Unknown')}</td></tr>
      <tr><td style="padding:7px 0;border-bottom:1px solid #eee;color:#666"><b>⏰ Time</b></td><td style="padding:7px 0;border-bottom:1px solid #eee">{t}</td></tr>
      <tr><td style="padding:7px 0;color:#666"><b>🔔 Alert</b></td><td style="padding:7px 0">{alert_type}</td></tr>
    </table>
    <div style="margin:22px 0;text-align:center">
      <a href="{maps_link}" style="background:#00c9ff;color:white;padding:13px 28px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:15px;display:inline-block">📍 View Live Location on Google Maps</a>
    </div>
  </div>
</div></body></html>"""



# ═══════════════════════════════════════════════════════════════════
# DEBUG — Test DB is working (visit /api/test-db in browser)
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/test-db')
def test_db():
    try:
        db = get_db()
        users     = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        services  = db.execute("SELECT COUNT(*) AS c FROM city_services").fetchone()["c"]
        alerts    = db.execute("SELECT COUNT(*) AS c FROM sos_alerts").fetchone()["c"]
        all_users = [dict(r) for r in db.execute("SELECT id,name,phone,current_city,created_at FROM users ORDER BY id DESC LIMIT 10").fetchall()]
        db.close()
        return jsonify({
            "status": "OK",
            "db_path": DB_PATH,
            "users": users,
            "city_services": services,
            "sos_alerts": alerts,
            "recent_users": all_users
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "error": str(e)}), 500

def build_welcome_email(user: dict) -> str:
    t = datetime.now().strftime('%d %b %Y, %I:%M %p')
    return f"""<html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px">
<div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;overflow:hidden">
  <div style="background:linear-gradient(135deg,#0a0f1e,#0d1528);padding:30px;text-align:center;border-bottom:3px solid #00c9ff">
    <h1 style="color:#00c9ff;margin:0;font-size:28px">🛡️ SafeTrail</h1>
    <p style="color:rgba(255,255,255,.7);margin:8px 0 0;font-size:14px">Smart Tourist Safety System — Navi Mumbai</p>
  </div>
  <div style="padding:30px">
    <h2 style="color:#0a0f1e;margin-bottom:6px">Welcome, {user.get('name','Tourist')}! 🎉</h2>
    <p style="color:#555;margin-bottom:20px">Your SafeTrail safety profile has been successfully created. You are now protected.</p>
    <div style="background:#f8f9ff;border:1px solid #e0e8ff;border-radius:10px;padding:18px;margin-bottom:20px">
      <h3 style="color:#0a0f1e;margin:0 0 12px;font-size:15px">📋 Your Registered Details</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <tr><td style="padding:6px 0;color:#666;width:40%"><b>👤 Name</b></td><td style="padding:6px 0"><b>{user.get('name','')}</b></td></tr>
        <tr><td style="padding:6px 0;color:#666"><b>📞 Phone</b></td><td style="padding:6px 0">{user.get('phone','')}</td></tr>
        <tr><td style="padding:6px 0;color:#666"><b>🆘 Emergency</b></td><td style="padding:6px 0">{user.get('emergency_contact','Not set')}</td></tr>
        <tr><td style="padding:6px 0;color:#666"><b>🏥 Medical</b></td><td style="padding:6px 0">{user.get('medical','Not provided')}</td></tr>
        <tr><td style="padding:6px 0;color:#666"><b>🏙️ City</b></td><td style="padding:6px 0">{user.get('city','Navi Mumbai')}</td></tr>
        <tr><td style="padding:6px 0;color:#666"><b>🔐 ID</b></td><td style="padding:6px 0;font-size:11px;color:#0077ff">{user.get('blockchain_id','')}</td></tr>
        <tr><td style="padding:6px 0;color:#666"><b>⏰ Registered</b></td><td style="padding:6px 0">{t}</td></tr>
      </table>
    </div>
    <div style="background:#fff5f5;border:1px solid #ffd0d0;border-radius:10px;padding:16px;margin-bottom:20px">
      <b style="color:#cc0000">🚨 In an Emergency:</b>
      <p style="color:#444;margin:6px 0 0;font-size:13px">
        Open SafeTrail → Press the <b>SOS button</b> → Your location is automatically sent to police + emergency contacts.<br>
        Or call <b>112</b> (Police) · <b>102</b> (Ambulance) · <b>101</b> (Fire)
      </p>
    </div>
    <div style="text-align:center;margin-top:24px">
      <a href="http://127.0.0.1:5500/" style="background:#00c9ff;color:#0a0f1e;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:15px;display:inline-block">🗺️ Open Live Map →</a>
    </div>
    <p style="text-align:center;color:#aaa;font-size:11px;margin-top:24px">SafeTrail · Navi Mumbai Tourist Safety · Stay Safe Always</p>
  </div>
</div></body></html>"""


# ═══════════════════════════════════════════════════════════════════
# STATIC FILES
# ═══════════════════════════════════════════════════════════════════

@app.route('/')
def index(): return send_from_directory('../Frontend', 'index.html')

@app.route('/<path:fn>')
def static_files(fn): return send_from_directory('../Frontend', fn)


# ═══════════════════════════════════════════════════════════════════
# AUTH — FIX #1 (phone validation) + FIX #3 (DB commit)
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/register', methods=['POST'])
def register():
    d = request.json or {}

    # ── Validate name ──
    if not d.get('name', '').strip():
        return jsonify({'error': 'Name is required'}), 400

    # ── FIX #1: strict phone validation ──
    raw_phone = d.get('phone', '')
    valid, result = validate_phone(raw_phone)
    if not valid:
        return jsonify({'error': result}), 400
    phone_10 = result   # clean 10-digit string stored in DB

    bid = blockchain_id(phone_10 + d['name'] + datetime.now().isoformat())
    lat = d.get('latitude')    # FIX #4: store lat/lng
    lng = d.get('longitude')

    try:
        db = get_db()
        db.execute(
            '''INSERT INTO users
               (name, phone, emergency_contact, emergency_contact2,
                emergency_email, medical_info, id_number, address,
                current_city, blockchain_id, latitude, longitude)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (
                d['name'].strip(),
                phone_10,
                d.get('emergency_contact', ''),
                d.get('emergency_contact2', ''),
                d.get('emergency_email', ''),
                d.get('medical', ''),
                d.get('id_number', ''),
                d.get('address', ''),
                d.get('city', 'Navi Mumbai'),
                bid,
                lat,
                lng
            )
        )
        db.commit()   # FIX #3: explicit commit
        uid = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        db.close()
        print(f"✅ Registered user: {d['name']} ({phone_10}) uid={uid}")

        # ── Send welcome email to user ──────────────────────────────
        welcome_user = {
            'name': d['name'].strip(),
            'phone': phone_10,
            'emergency_contact': d.get('emergency_contact', ''),
            'medical': d.get('medical', 'Not provided'),
            'city': d.get('city', 'Navi Mumbai'),
            'blockchain_id': bid
        }
        if d.get('emergency_email'):
            html = build_welcome_email(welcome_user)
            send_email(d['emergency_email'], f"🛡️ Welcome to SafeTrail, {d['name']}!", html)
            print(f"📧 Welcome email sent to {d['emergency_email']}")

        # ── Send welcome SMS-style notification (via tel: link info) ──
        # This is stored so the frontend can trigger it
        sms_sent = bool(d.get('emergency_contact'))

        return jsonify({
            'success': True,
            'user_id': uid,
            'blockchain_id': bid,
            'message': f'Welcome {d["name"]}!',
            'email_sent': bool(d.get('emergency_email')),
            'sms_ready': sms_sent,
            'emergency_contact': d.get('emergency_contact', '')
        })
    except sqlite3.IntegrityError as e:
        print(f"❌ IntegrityError: {e}")
        return jsonify({'error': 'Phone already registered'}), 409
    except Exception as e:
        print(f"❌ DB error: {e}")
        return jsonify({'error': 'Database error, please retry'}), 500


@app.route('/api/login', methods=['POST'])
def login():
    d = request.json or {}

    # FIX #1: validate phone on login too
    raw_phone = d.get('phone', '')
    valid, result = validate_phone(raw_phone)
    if not valid:
        return jsonify({'error': result}), 400

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE phone=?', (result,)).fetchone()
    db.close()
    if user:
        return jsonify({'success': True, 'user': dict(user)})
    return jsonify({'error': 'Phone number not registered'}), 404


# ═══════════════════════════════════════════════════════════════════
# CITY SERVICES
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/cities', methods=['GET'])
def get_cities():
    return jsonify({'cities': ALL_CITIES, 'count': len(ALL_CITIES)})

@app.route('/api/city/<city_name>/services', methods=['GET'])
def get_city_services(city_name):
    services = CITY_SERVICES.get(city_name, [])
    svc_type = request.args.get('type')
    if svc_type:
        services = [s for s in services if s['type'] == svc_type]
    return jsonify({'city': city_name, 'total': len(services), 'services': services})

@app.route('/api/city/<city_name>/services/<svc_type>', methods=['GET'])
def get_city_services_by_type(city_name, svc_type):
    services = [s for s in CITY_SERVICES.get(city_name, []) if s['type'] == svc_type]
    return jsonify({'city': city_name, 'type': svc_type, 'total': len(services), 'services': services})


# ═══════════════════════════════════════════════════════════════════
# LOCATION — FIX #2 (store live lat/lng)
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/location/update', methods=['POST'])
def update_location():
    d = request.json or {}
    uid = d.get('user_id')
    lat = d.get('latitude')
    lng = d.get('longitude')
    if uid is None or lat is None or lng is None:
        return jsonify({'error': 'user_id, latitude and longitude are required'}), 400
    zone = 'SAFE'
    danger_zones = [(18.9894, 73.1175, 1.0), (19.0474, 73.0692, 0.8)]
    for zlat, zlng, r in danger_zones:
        if ((lat - zlat) ** 2 + (lng - zlng) ** 2) ** 0.5 * 111 < r:
            zone = 'HIGH_RISK'; break
    db = get_db()
    db.execute(
        'INSERT INTO locations (user_id, latitude, longitude, zone_status) VALUES (?,?,?,?)',
        (uid, lat, lng, zone)
    )
    # Also update users table with latest lat/lng
    db.execute(
        'UPDATE users SET latitude=?, longitude=? WHERE id=?',
        (lat, lng, uid)
    )
    db.commit()
    db.close()
    return jsonify({'success': True, 'zone': zone, 'ts': datetime.now().isoformat()})

@app.route('/api/location/history/<int:uid>')
def location_history(uid):
    db = get_db()
    rows = db.execute(
        'SELECT * FROM locations WHERE user_id=? ORDER BY timestamp DESC LIMIT 100', (uid,)
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# ═══════════════════════════════════════════════════════════════════
# SOS
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/sos/trigger', methods=['POST'])
def trigger_sos():
    d = request.json or {}
    user = {
        'name': d.get('name', 'Unknown Tourist'),
        'phone': d.get('phone', ''),
        'emergency_contact': d.get('emergency_contact', ''),
        'emergency_contact2': d.get('emergency_contact2', ''),
        'emergency_email': d.get('emergency_email', ''),
        'medical': d.get('medical', 'Not provided'),
        'address': d.get('address', 'Unknown'),
    }
    lat = d.get('latitude', 19.0330)
    lng = d.get('longitude', 73.0297)
    maps_link = d.get('maps_link') or f"https://maps.google.com/?q={lat},{lng}"
    alert_type = d.get('type', 'MANUAL_SOS')
    results = {'email_sent': False, 'call_initiated': False, 'police_notified': False}
    if user['emergency_email']:
        html = build_email(user, maps_link, alert_type)
        results['email_sent'] = send_email(user['emergency_email'],
                                           f"🚨 SOS ALERT — {user['name']} — SafeTrail", html)
    send_email(POLICE_EMAIL, f"🚨 TOURIST EMERGENCY — {user['name']}",
               build_email(user, maps_link, "POLICE_NOTIFICATION"))
    results['police_notified'] = True
    results['call_initiated'] = bool(user['emergency_contact'])
    bhash = blockchain_id(f"{user['phone']}{lat}{lng}{datetime.now().isoformat()}")
    db = get_db()
    db.execute(
        '''INSERT INTO sos_alerts
           (user_name,user_phone,latitude,longitude,maps_link,alert_type,
            email_sent,call_initiated,police_notified,contacts_notified,blockchain_hash)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (user['name'], user['phone'], lat, lng, maps_link, alert_type,
         int(results['email_sent']), int(results['call_initiated']),
         int(results['police_notified']),
         json.dumps([user['emergency_contact'], user['emergency_contact2']]), bhash)
    )
    db.execute(
        'INSERT INTO incidents (incident_type,description,latitude,longitude,blockchain_hash) VALUES (?,?,?,?,?)',
        (alert_type, f"SOS by {user['name']}", lat, lng, bhash)
    )
    db.commit()
    db.close()
    return jsonify({'success': True, 'results': results, 'maps_link': maps_link,
                    'incident_hash': bhash, 'nearest_police': 'Vashi PS: 022-2765-8200',
                    'timestamp': datetime.now().isoformat()})

@app.route('/api/distress/report', methods=['POST'])
def distress_report():
    d = request.json or {}
    d['type'] = 'AUTO_DISTRESS'
    # Build response directly instead of re-calling trigger_sos() which re-reads request.json
    user = {
        'name': d.get('name', 'Unknown Tourist'),
        'phone': d.get('phone', ''),
        'emergency_contact': d.get('emergency_contact', ''),
        'emergency_contact2': d.get('emergency_contact2', ''),
        'emergency_email': d.get('emergency_email', ''),
        'medical': d.get('medical', 'Not provided'),
        'address': d.get('address', 'Unknown'),
    }
    lat = d.get('latitude', 19.0330)
    lng = d.get('longitude', 73.0297)
    maps_link = f"https://maps.google.com/?q={lat},{lng}"
    bhash = blockchain_id(f"{user['phone']}{lat}{lng}{datetime.now().isoformat()}")
    results = {'email_sent': False, 'call_initiated': False, 'police_notified': False}
    if user['emergency_email']:
        html = build_email(user, maps_link, 'AUTO_DISTRESS')
        results['email_sent'] = send_email(user['emergency_email'],
                                           f"🚨 AUTO DISTRESS — {user['name']} — SafeTrail", html)
    send_email(POLICE_EMAIL, f"🚨 AUTO DISTRESS — {user['name']}",
               build_email(user, maps_link, "AUTO_DISTRESS_POLICE"))
    results['police_notified'] = True
    results['call_initiated'] = bool(user['emergency_contact'])
    try:
        db = get_db()
        db.execute(
            '''INSERT INTO sos_alerts
               (user_name,user_phone,latitude,longitude,maps_link,alert_type,
                email_sent,call_initiated,police_notified,contacts_notified,blockchain_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (user['name'], user['phone'], lat, lng, maps_link, 'AUTO_DISTRESS',
             int(results['email_sent']), int(results['call_initiated']),
             int(results['police_notified']),
             json.dumps([user['emergency_contact'], user['emergency_contact2']]), bhash)
        )
        db.execute(
            'INSERT INTO incidents (incident_type,description,latitude,longitude,blockchain_hash) VALUES (?,?,?,?,?)',
            ('AUTO_DISTRESS', f"Auto distress by {user['name']}", lat, lng, bhash)
        )
        db.commit()
        db.close()
    except Exception as e:
        print(f"❌ DB error in distress_report: {e}")
    return jsonify({'success': True, 'results': results, 'maps_link': maps_link,
                    'incident_hash': bhash, 'timestamp': datetime.now().isoformat()})



@app.route('/api/send-welcome', methods=['POST'])
def send_welcome():
    """Send welcome email + return SMS body for frontend to trigger"""
    d = request.json or {}
    name  = d.get('name', 'Tourist')
    email = d.get('emergency_email', '')
    phone = d.get('emergency_contact', '')
    city  = d.get('city', 'Navi Mumbai')
    bid   = d.get('blockchain_id', '')

    user = {'name': name, 'phone': d.get('phone',''), 'emergency_contact': phone,
            'medical': d.get('medical',''), 'city': city, 'blockchain_id': bid}

    email_sent = False
    if email:
        html = build_welcome_email(user)
        email_sent = send_email(email, f"🛡️ Welcome to SafeTrail, {name}!", html)

    sms_body = (f"🛡️ SafeTrail: {name} has registered on SafeTrail Tourist Safety System "
                f"in Navi Mumbai. In case of emergency they will alert you automatically. "
                f"Stay safe!")

    return jsonify({
        'success': True,
        'email_sent': email_sent,
        'sms_body': sms_body,
        'sms_to': phone
    })

# ═══════════════════════════════════════════════════════════════════
# ADMIN STATS
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/admin/stats')
def admin_stats():
    db = get_db()
    users     = db.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c']
    alerts    = db.execute('SELECT COUNT(*) AS c FROM sos_alerts').fetchone()['c']
    incidents = db.execute('SELECT COUNT(*) AS c FROM incidents').fetchone()['c']
    recent    = db.execute('SELECT * FROM sos_alerts ORDER BY timestamp DESC LIMIT 5').fetchall()
    db.close()
    return jsonify({'total_users': users, 'sos_alerts': alerts, 'incidents': incidents,
                    'cities_monitored': len(ALL_CITIES),
                    'recent_alerts': [dict(r) for r in recent],
                    'last_updated': datetime.now().isoformat()})


# ═══════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    print("\n" + "="*60)
    print("  🛡️  SafeTrail Server — Navi Mumbai")
    print("="*60)
    print(f"  💾  DATABASE : {os.path.abspath(DB_PATH)}")
    print("  ─"*30)
    print("  🌐  http://127.0.0.1:5500/")
    print("  🗺️   http://127.0.0.1:5500/map.html")
    print("  🆘  http://127.0.0.1:5500/sos.html")
    print("  🏨  http://127.0.0.1:5500/hotels.html")
    print("  🔍  http://127.0.0.1:5500/api/test-db     ← verify DB live")
    print("  📊  http://127.0.0.1:5500/api/admin/stats")
    print("="*60)
    print(f"  ✉️  Email: {'ENABLED' if EMAIL_ENABLED else 'DEMO MODE'}")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5500, use_reloader=False)
