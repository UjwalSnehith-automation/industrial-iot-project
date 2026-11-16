# Multi-Plant IIoT Gateway Project

A sample project I built to collect machine data from three production plants, organize it using the ISA-95 standard, stream it over MQTT, store it centrally, automate control actions, and add real-time anomaly detection.

---

## 1. Protocol Choice: Why OPC UA and MQTT?

To connect the physical machines to our central system, I split the communication into two layers:

*   **At the machines (OPC UA):** 
    *   Most modern industrial controllers speak OPC UA out of the box, so I didn't need custom hardware drivers.
    *   Its browsable tree structure mapped naturally onto our ISA-95 equipment hierarchy.
    *   The gateway uses event-driven subscriptions instead of constantly polling the machines, which saves a lot of network bandwidth.

*   **Between plants and the center (MQTT):**
    *   It is lightweight and works great over slower or variable network links.
    *   The publish/subscribe model decouples producers and consumers—our dashboard and storage services just listen to topics without the plants needing to know who is listening.
    *   Plant gateways connect outward to the central broker, meaning we don't need risky inbound firewall holes into plant networks.

---

## 2. ISA-95 Structure

To keep everything organized and scalable, every data point follows a 6-level hierarchy defined in a single configuration file (`config/plants.yaml`):

$$\text{Enterprise} > \text{Site} > \text{Area} > \text{Line} > \text{Cell} > \text{Metric}$$

*Example Topic:* `reckoning/plant_kronach/process_lab/process_line_1/printer_1/temperature`

Because this path serves as both the OPC UA address and the MQTT topic, adding new machines or plants later requires zero code changes.

---

## 3. What I Built

I organized the project into modular parts:
1. **Three simulated plants (`simulators/`):** OPC UA servers for Coburg, Kronach, and Bamberg with 10 total machine cells reporting temperature, power, part count, and status.
2. **The Gateway (`gateway/`):** Asynchronously reads all plant servers, normalizes the data into standard JSON, and publishes it over MQTT.
3. **The Center (`central/`):** Listens to MQTT, saves every reading into SQLite (`data.db`), and runs our automation rules.
4. **The Dashboard (`dashboard/`):** A Streamlit web UI that shows real-time data and runs an Isolation Forest model to spot unusual machine behavior.

---

## 4. Automation, Safety & Machine Learning

*   **Rule Engine:** When a machine reports `status = 2` (fault), the center automatically issues a `reset` command.
*   **Circuit Breaker:** To prevent infinite loops on broken hardware, resets are capped at 3 per machine within 60 seconds. If it keeps failing, the system pauses resets and logs a `"maintenance needed"` alert.
*   **Security:** The gateway whitelists the `reset` command and ensures commands are non-retained so old instructions never run after a restart.
*   **Machine Learning (Anomaly Detection):** The dashboard runs an unsupervised **Isolation Forest** model on incoming telemetry (`temperature`, `power`, `status`). It flags statistically rare operating points in real time without needing pre-labeled training data, complete with a user-adjustable sensitivity slider.

---

## 5. How to Run the Demo

I created a master script to start the entire environment with a single command:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_demo.py --fast-faults --dashboard