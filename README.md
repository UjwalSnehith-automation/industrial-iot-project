# Multi-Plant IIoT Gateway Project

A robust edge-to-cloud industrial IoT architecture built to collect machine telemetry from three production plants, organize it using ANSI/ISA-95 standards, stream it securely over MQTT, store it centrally, enforce operator safety interlocks, and provide real-time ML-based anomaly detection.


## 1. Protocol Choice: Why OPC UA and MQTT?

To connect physical factory floors to the central platform, communication is split into two specialized layers:

**At the Machines (OPC UA):** 
  - Most modern industrial controllers support OPC UA natively, eliminating custom hardware driver overhead.
  - Its browsable address space maps naturally onto standard plant hierarchies.
  - The gateway utilizes asynchronous event-driven subscriptions instead of continuous polling, significantly reducing network bandwidth and CPU load.

**Between Plants and the Center (MQTT):**
  - Extremely lightweight protocol ideal for variable or constrained industrial network links.
  - The publish/subscribe architecture decouples producers from consumers; storage and visualization microservices listen to topics independently.
  - Gateways initiate outbound TCP connections from the plant network to the central broker, avoiding risky inbound firewall holes.

## 2. ISA-95 Architecture Mapping

To ensure compliance with ANSI/ISA-95 enterprise-control system integration standards, this project explicitly separates the physical asset model from the software functional levels.

### A. Physical Equipment Hierarchy (Asset Model)
Data points and OPC UA nodes follow a standardized 5-level naming convention defined in `config/plants.yaml`:

$$\text{Enterprise} > \text{Site} > \text{Area} > \text{Line} > \text{Cell}$$

*Example Topic:* `enterprise/plant_kronach/assembly/line_1/cell_1/telemetry`

### B. ISA-95 Functional Levels (Software Architecture)
- **Level 0 (Physical Process):** Simulated physical machinery (motor temperatures, power draw, part counts).
- **Level 1 (Sensing & Control):** OPC UA servers exposing real-time tags and process variables.
- **Level 2 (Supervisory Edge Gateway):** Python IIoT gateway reading OPC UA subscriptions, executing local data normalization, and capturing dual timestamps (`source_timestamp` vs. `received_timestamp`).
- **Level 3 (Operations / MES):** MQTT broker and SQLite persistence layer routing telemetry and fault alarms.
- **Level 4 (Business Planning / ERP):** Streamlit dashboard and cross-plant analytics layer.

## 3. What I Built

The project is structured into modular, decoupled packages:
1. **Simulators (`simulators/`):** Three OPC UA servers representing Coburg, Kronach, and Bamberg plants featuring 10 total machine cells.
2. **Gateway (`gateway/`):** Asynchronous client reading OPC UA nodes, stamping telemetry with source and ingestion times, and publishing normalized JSON over MQTT.
3. **Central Platform (`central/`):** MQTT event listener persisting all readings into SQLite (`data.db`) and managing alarm states.
4. **Dashboard (`dashboard/`):** Streamlit web interface displaying real-time plant metrics and running an unsupervised **Isolation Forest** model for anomaly detection.

## 4. Automation, Safety & Machine Learning

- **Human-in-the-Loop (HITL) Safety:** To comply with industrial safety principles (preventing unexpected machine restarts while an operator services a cell), automated resets have been removed. When a machine faults (`status = 2`), the system triggers an operator alert (`requires_operator_ack: true`) requiring explicit manual intervention.
- **Telemetry Integrity:** The normalizer preserves both `source_timestamp` (generated at the machine PLC) and `received_timestamp` (ingested at the edge gateway) to accurately calculate network propagation jitter and support historical backfilling.
- **Machine Learning (Anomaly Detection):** The dashboard runs an unsupervised **Isolation Forest** model on incoming telemetry (`temperature`, `power`, `status`) to flag statistically rare operating points in real time with adjustable sensitivity.

## 5. Security & Production Readiness

- **Local Demo Scope:** For zero-friction local reproducibility, this demonstration uses unencrypted OPC UA (`NoSecurity`) and an anonymous MQTT broker.
- **Production Hardening Requirements:**
  - **OT Layer (OPC UA):** Enforce `Basic256Sha256` (`SignAndEncrypt`) with X.509 mutual certificate exchange between the gateway and plant controllers.
  - **IT/OT Boundary (MQTT):** Enforce TLS 1.3 encryption (port 8883), disable anonymous connections, require client token/certificate authentication, and enforce strict topic ACLs.

## 6. How to Run the Demo

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_demo.py --fast-faults --dashboard