# Multi-Plant IIoT Gateway Project

A modular edge-to-cloud IIoT architecture collecting machine telemetry from three simulated plants, organizing it via ANSI/ISA-95 standards, streaming it over MQTT, enforcing operator safety, and running real-time ML anomaly detection.

## 1. Protocols: OPC UA & MQTT
- **OPC UA (Machine Layer):** Native PLC support, browsable address spaces, and event-driven subscriptions instead of heavy polling.
- **MQTT (Plant-to-Center):** Lightweight publish/subscribe model over variable networks with secure outbound gateway connections (no inbound firewall holes).

## 2. Language Choice: Why Python?
- **Python Selected:** Provides a mature async industrial ecosystem (`asyncua`, `paho-mqtt`) and native data science libraries (`scikit-learn`, `numpy`) for inline ML anomaly detection.
- **Alternatives Considered:** 
  - *C/C++:* Maximum speed for embedded PLCs, but high development overhead for rapid prototyping.
  - *Go:* Great concurrency, but lacks Python's out-of-the-box ML/statistical stack.
  - *Java/C#:* Strong enterprise support, but too heavy and verbose for a lightweight edge gateway.

## 3. ISA-95 Architecture
- **Physical Equipment Hierarchy:** `Enterprise > Site > Area > Line > Cell` (drives OPC UA paths and MQTT topics).
- **Functional Software Levels:** 
  - *Level 0–1:* Simulated physical sensors and OPC UA servers.
  - *Level 2:* Edge gateway handling normalization and dual timestamps (`source` vs. `received`).
  - *Level 3:* Central MQTT broker and SQLite storage.
  - *Level 4:* Streamlit dashboard and analytics.

## 4. Key Features & Safety
- **Human-in-the-Loop (HITL) Safety:** Automated machine resets are disabled. Faults (`status = 2`) trigger persistent operator alerts requiring manual acknowledgment per industrial safety standards.
- **Telemetry Integrity:** Captures both `source_timestamp` (machine generation) and `received_timestamp` (gateway ingestion) to track network jitter.
- **ML Anomaly Detection:** Unsupervised *Isolation Forest* model flags unusual telemetry in real time via the dashboard.

## 5. Security & Production Scope
- **Current Local Scope:** Unencrypted OPC UA (`NoSecurity`) and anonymous MQTT for zero-friction local testing.
- **Production Requirements:** TLS 1.3, X.509 mutual certificates, token authentication, and strict topic ACLs.

## 6. How to Run
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_demo.py --fast-faults --dashboard