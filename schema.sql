-- ═══════════════════════════════════════════════════════
-- SafeTrail Database Schema (FIXED)
-- ═══════════════════════════════════════════════════════

-- Users table — stores name, type, country, phone, lat, lng (Fix #4)
CREATE TABLE IF NOT EXISTS users (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL,
    phone               TEXT    UNIQUE NOT NULL,       -- exactly 10 digits, enforced in backend
    emergency_contact   TEXT    DEFAULT '',
    emergency_contact2  TEXT    DEFAULT '',
    emergency_email     TEXT    DEFAULT '',
    medical_info        TEXT    DEFAULT '',
    id_number           TEXT    DEFAULT '',
    address             TEXT    DEFAULT '',
    current_city        TEXT    DEFAULT 'Navi Mumbai',
    blockchain_id       TEXT    UNIQUE,
    latitude            REAL,                          -- Fix #4: live location
    longitude           REAL,                          -- Fix #4: live location
    user_type           TEXT    DEFAULT 'tourist',     -- Fix #4: type field
    country             TEXT    DEFAULT 'India',       -- Fix #4: country field
    created_at          TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- Location tracking table
CREATE TABLE IF NOT EXISTS locations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    latitude    REAL    NOT NULL,
    longitude   REAL    NOT NULL,
    zone_status TEXT    DEFAULT 'SAFE',
    speed       REAL    DEFAULT 0,
    timestamp   TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- SOS alerts table
CREATE TABLE IF NOT EXISTS sos_alerts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER,
    user_name           TEXT,
    user_phone          TEXT,
    latitude            REAL,
    longitude           REAL,
    maps_link           TEXT,
    alert_type          TEXT    DEFAULT 'MANUAL',
    email_sent          INTEGER DEFAULT 0,
    call_initiated      INTEGER DEFAULT 0,
    police_notified     INTEGER DEFAULT 0,
    contacts_notified   TEXT,
    blockchain_hash     TEXT,
    timestamp           TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,
    incident_type   TEXT,
    description     TEXT,
    latitude        REAL,
    longitude       REAL,
    blockchain_hash TEXT,
    timestamp       TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- City services cache
CREATE TABLE IF NOT EXISTS city_services (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name   TEXT NOT NULL,
    svc_type    TEXT NOT NULL,
    svc_name    TEXT NOT NULL,
    latitude    REAL,
    longitude   REAL,
    phone       TEXT,
    open_hours  TEXT DEFAULT 'Open',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_phone       ON users(phone);
CREATE INDEX IF NOT EXISTS idx_locations_user    ON locations(user_id);
CREATE INDEX IF NOT EXISTS idx_sos_user          ON sos_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_city_services     ON city_services(city_name, svc_type);
