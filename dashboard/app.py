import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent)) 
import altair as alt
import streamlit as st
import analytics
from config.loader import load_config

STATUS_NAMES = {0: "idle", 1: "running", 2: "fault"}

st.set_page_config(page_title="Plant dashboard", layout="wide")
cfg = load_config()
plant_names = {p["id"]: p["name"] for p in cfg["plants"]}
st.title(f"{cfg['enterprise']}: machine data from three plants")

@st.cache_data(ttl=2)   
def get_data(db_path):
    return analytics.load_readings(db_path), analytics.load_actions(db_path)

db_path = st.sidebar.text_input("Database file", "data.db")
st.sidebar.button("Refresh")   
readings, actions = get_data(db_path)

if readings.empty:
    st.warning("No data yet. Start the broker, simulators, gateway and center first.")
    st.stop()

st.subheader("Latest values of all machines")
overview = analytics.latest_values(readings)
overview["status"] = overview["status"].map(lambda s: STATUS_NAMES.get(int(s), "?") if s == s else "?")
overview.insert(0, "plant name", overview["plant"].map(plant_names))
st.dataframe(overview, hide_index=True)

st.subheader("Automatic actions taken by the rule engine")
if actions.empty:
    st.info("No automatic actions yet. They appear when a machine reports a fault.")
else:
    st.write(f"{len(actions)} recent actions")
    st.dataframe(actions, hide_index=True)

st.sidebar.header("Machine")
plant = st.sidebar.selectbox("Plant", sorted(readings.plant.unique()), format_func=lambda p: plant_names.get(p, p))
d = readings[readings.plant == plant]
area = st.sidebar.selectbox("Area", sorted(d.area.unique()))
d = d[d.area == area]
line = st.sidebar.selectbox("Line", sorted(d.line.unique()))
d = d[d.line == line]
cell = st.sidebar.selectbox("Cell", sorted(d.cell.unique()))

st.subheader(f"{plant} / {area} / {line} / {cell}")
frame = analytics.cell_frame(readings, plant, area, line, cell)
if frame.empty:
    st.info("No data for this machine yet.")
    st.stop()

last = frame.iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Status", STATUS_NAMES.get(int(last["status"]), "?"))
c2.metric("Temperature (degC)", f"{last['temperature']:.1f}")
c3.metric("Power (kW)", f"{last['power']:.1f}")
c4.metric("Part count", int(last["part_count"]))

st.subheader("Anomaly detection (Isolation Forest)")
contamination = st.slider("Expected share of unusual points", 0.005, 0.10, 0.02, 0.005)
result = analytics.detect_anomalies(frame, contamination)
n_anomalies = int(result["anomaly"].sum())
st.write(f"{n_anomalies} unusual points out of {len(result)} readings.")

plot_df = result.reset_index()
line_chart = alt.Chart(plot_df).mark_line().encode(
    x=alt.X("ts:T", title="Time"), y=alt.Y("temperature:Q", title="Temperature (degC)")
)
points = alt.Chart(plot_df[plot_df["anomaly"]]).mark_circle(size=80, color="red").encode(
    x="ts:T", y="temperature:Q", tooltip=["ts:T", "temperature:Q", "power:Q", "status:Q", "score:Q"]
)
st.altair_chart(line_chart + points)
st.caption(
    "The Isolation Forest learns which combinations of temperature, power and status are "
    "typical for this machine and flags the rarest ones. The data is simulated, so "
    "'unusual' only means 'statistically rare', not 'broken'."
)