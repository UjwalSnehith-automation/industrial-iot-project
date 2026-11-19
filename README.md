# Multi-Plant IIoT Gateway Project

A demo that collects machine data from three simulated plants over OPC UA, organizes it according to ISA-95,
streams it over MQTT, stores it centrally, handles faults with operator acknowledgment (simulator only), and shows the data in a dashboard.
All machines are simulated.

## 1. Protocols: OPC UA & MQTT
- **OPC UA inside the plants:** modern controllers already have an OPC UA server, its browsable tree of typed
  variables fits the ISA-95 hierarchy, subscriptions avoid polling, and security is part of the standard.
- **MQTT from plants to center:** light, works on slow links, a broker decouples producers from consumers, and the
  plant gateway connects outward, so no inbound firewall opening into a plant is needed.
- **Trade-offs:** OPC UA is heavier, so it stays inside the plants. MQTT has no data model, so I define the topic
  structure and message format myself.
- **Alternatives:** Modbus TCP (no data model, no security, polling only), MQTT only (machines rarely speak it
  natively), OPC UA to the center (heavier, needs access into every plant).

## 2. Language: Python
- **Advantages:** libraries for OPC UA (`asyncua`), MQTT (`paho-mqtt`, `mqttools`) and ML (`scikit-learn`), fast to write,
  and `asyncio` fits a gateway that mostly waits for the network. The load here is small (40 values).
- **Disadvantages:** slower for CPU-heavy work, no real-time guarantees, dynamic typing (so tests matter),
  and heavier on very small devices.
- **C#/.NET:** OPC Foundation reference stack, static typing, common in industry, but more code and weaker for quick
  data experiments. 
  **Java:** mature libraries and common in MES back-ends, but more boilerplate and memory.
- **C/C++:** best performance and footprint for embedded devices, but slow to develop and riskier.
- **Go:** small static binaries and easy concurrency, but less mature OPC UA libraries and weak ML tools.
- **TypeScript:** mature OPC UA and MQTT libraries, but weaker for data analysis.
- **Rust:** safe and fast, but a young OPC UA ecosystem and a steep learning curve.

## 3. ISA-95
Two separate ideas, kept apart:
- **Equipment hierarchy:** `Enterprise > Site > Area > Line > Cell`, for example
  `reckoning / plant_kronach / process_lab / process_line_1 / printer_1`. The metric (temperature, power,
  part count, status) is a property of a cell, not a level. It is appended only to make each address unique:
  `reckoning/plant_kronach/process_lab/process_line_1/printer_1/temperature`. This path is both the OPC UA path
  and the MQTT topic, generated from `config/plants.yaml`. Three plants, 10 machines.
- **Functional levels (simplified):** Level 0 and 1 are the simulated process and machine values. Level 2 is the
  plant OPC UA servers, standing in for machine controllers. The gateway connects levels 2 and 3. Level 3 is the
  center: broker, storage, rules and dashboard. Level 4 (ERP) is not implemented.

## 4. Features & Safety
- **Data flow:** machines (OPC UA) -> gateway -> MQTT broker -> center (storage, rules, dashboard).
- **Timestamps:** each message has `timestamp` (the machine's own time) and `received_timestamp` (gateway time).
- **Fault handling with an operator:** when a machine reports `status = 2` (fault), the center records an alert and sends no command. On the dashboard, an operator enters their name and acknowledges the alert. Only then does the center send `reset` through the gateway into the machine. An acknowledgement only counts if there is an open alert for that machine, and who acknowledged what and when is stored.
- **Faults stay until reset:** in the simulator, a faulty machine does not repair itself (this can be switched on with `REPAIR_CHANCE`).
- **Optional automatic mode (simulator only):** a rule with `requires_ack: false` resets automatically, limited by a circuit breaker (at most 3 resets per machine per 60 seconds, then an alert). It is off by default.
- **Command checks:** the gateway accepts only the action `reset` and well-formed command topics. Commands are not retained, so an old command is never replayed.
- **Safety note:** the acknowledgement is a software confirmation in a simulator, not a safety function. Real equipment needs safety functions in the PLC or safety controller, operator login and roles, and a check that the machine is safe to restart.
- **ML:** the dashboard marks unusual points with an unsupervised Isolation Forest. The data is simulated, so
  "unusual" only means "statistically rare", and its accuracy cannot be measured.

## 5. Security & Limits
- **Demo:** OPC UA without security and anonymous MQTT, both bound to localhost only.
- **Production:** TLS, X.509 certificates, authentication, topic ACLs and network segmentation.
- **Other limits:** simulated data, SQLite instead of a time-series database, retained MQTT values can be old and there is no freshness check, no duplicate handling, and a single broker is a single point of failure. The operator name is typed, not authenticated: anyone who can open the dashboard can acknowledge.

## 6. How to Run
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_demo.py --fast-faults