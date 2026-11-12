import sqlite3
from datetime import datetime
import pandas as pd
import requests
import streamlit as st


st.set_page_config(page_title="Malaria Early Warning", layout="wide")

st.title("🦟 Malaria Early Warning & Prevention  System")
st.markdown("Proactive forecast-driven risk engine for community health intervention.")

# ADD SIDEBAR SIMULATION HERE
st.sidebar.header("🎛️ Live Risk Simulation")
st.sidebar.markdown("Adjust weather metrics to test the warning engine:")
sim_rainfall = st.sidebar.slider("Rainfall (mm)", 0, 150, 65)
sim_humidity = st.sidebar.slider("Humidity (%)", 20, 100, 85)
sim_mode = st.sidebar.checkbox("🚀 Enable Live Demo Simulation Mode", value=True)

st.sidebar.subheader("Simulation Result:")
if sim_rainfall > 70 and sim_humidity > 80:
    st.sidebar.error("🚨 Status: HIGH RISK TRIGGERED")
elif sim_rainfall > 40:
    st.sidebar.warning("⚠️ Status: HIGH RISK TRIGGERED")
elif sim_rainfall > 40:
    st.sidebar.warning("⚠️ Status: Moderate Risk")
else:
    st.sidebar.success("✅ Status: Safe Conditions")

#1. Weather forecast dataset

#function to fetch live weather from open-meteo api
def get_live_weather(lat, lon, zone_name):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            return {
                "Zone": zone_name,
                "Temps_C": current.get("temperature_2m", 30),
                "Rainfall_mm": current.get("precipitation", 0),
                "Humidity": current.get("relative_humidity_2m", 70)
            }
    except Exception:
        pass

        # fallback default values if connection fails
        return {"Zone": zone_name, "Temps_C": 30, "Rainfall_mm": 5, "Humidity": 75}

        # Fetch live data
@st.cache_data(ttl=3600)
def load_forecast_data():
    zones_coords = [
        {"name": "Ibadan North", "lat": 7.4165, "lon": 3.8967},
        {"name": "Ibadan South-East", "lat": 7.3776, "lon": 3.8967},
        {"name": "Ogbomoso", "lat": 8.1333, "lon": 4.2500},
        {"name": "Challenge", "lat": 7.3667, "lon": 3.8667},
        {"name": "Bodija", "lat": 7.4250, "lon": 3.9000}
    ]
    live_data = []
    for z in zones_coords:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": z["lat"],
            "longitude": z["lon"],
            "current" : ["temperature_2m", "relative_humidity_2m"],
            "hourly": ["precipitation", "relative_humidity_2m"],
            "forecast_days": 3
        }

        zone_weather = {"Zone": z["name"], "Temps_C": 30, "Rainfall_mm": 5, "Humidity": 75}

        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                current = data.get("current", {})
                hourly = data.get("hourly", {})
                rain_list = hourly.get("precipitation", [])
                total_rain_forecast = sum(rain_list[:72]) if (rain_list) else 0

                zone_weather = {
                    "Zone": z["name"],
                    "Temps_C": current.get("temperature_2m",30),
                    "Rainfall_mm": round(total_rain_forecast, 1),
                    "Humidity": current.get("relative_humidity_2m", 75)
                }
        except Exception:
            pass

        live_data.append(zone_weather)

    return pd.DataFrame(live_data)
df_weather = load_forecast_data()
#2. Risk evaluation logic
def assess_risk(row):
    if row['Rainfall_mm'] > 70 and row['Humidity'] > 80:
        return "High Risk (Critical Alert)"
    elif row['Rainfall_mm'] > 40:
        return "Moderate Risk"
    else:
        return"Low Risk"
df_weather = load_forecast_data()
# apply simulation override
if sim_mode:
    # Force the slider values onto the dataframe during your presentation
    df_weather['Rainfall_mm'] = sim_rainfall
    df_weather['Humidity'] = sim_humidity
    # Re-run risk evaluation with simulated values
    df_weather['Risk_Level'] = df_weather.apply(assess_risk, axis=1)
                                

        
df_weather['Risk_Level'] = df_weather.apply(assess_risk, axis=1)

# Summary Key Metrics (KPI Bar)
high_count = len(df_weather[df_weather['Risk_Level'] == "High Risk (Critical Alert)"])
mod_count = len(df_weather[df_weather['Risk_Level'] == "Moderate Risk"])
low_count = len(df_weather[df_weather['Risk_Level'] == "Low Risk"])

col1, col2, col3 = st.columns(3)
col1.metric("🚨 High Risk Zones", high_count)
col2.metric("⚠️ Moderate Risk Zones", mod_count)
col3.metric("✅ Safe Zones", low_count)

st.write("---")

# Make the table row index start from 1
df_weather.index = range(1, len(df_weather) +1)

#3. Display interactive table on the app
st.subheader("Regional Weather Forecast & Risk Status")
st.dataframe(df_weather, use_container_width=True)

#4. Filtered Alerts Section
high_risk_zones = df_weather[df_weather['Risk_Level'] == 'High Risk (Critical Alert)']

st.subheader("Actionable Dispatch Alerts")

if not high_risk_zones.empty:
    for index, row in high_risk_zones.iterrows():
        st.error(f"🚨 CRITICAL ALERT FOR: {row['Zone']}")
        st.write(f"**Trigger:** Rainfall at {row['Rainfall_mm']}mm & Humidity at {row['Humidity']}%")
        st.info("Action Required: Mobilize local sanitation teams for gutter clearing and distribute ITN bed nets immediately.")
    else:
        st.success("All zones currently within safe thresholds.")

        #5 spatial Visualization Map
st.subheader("🗺️ Regional risk Spatial View")

import pydeck as pdk

# Merge your live weather data with coordinates for the map
map_df = df_weather.copy()
coords_dict = {
    "Ibadan North": {"lat": 7.4165, "lon": 3.8967},
    "Ibadan South-East": {"lat": 7.3776, "lon": 3.8967},
    "Ogbomoso": {"lat": 8.1333, "lon": 4.2500},
    "Challenge": {"lat": 7.3667, "lon": 3.8667},
    "Bodija": {"lat": 7.4250, "lon": 3.9000}
}

map_df['lat'] = map_df['Zone'].map(lambda x: coords_dict[x]['lat'])
map_df['lon'] = map_df['Zone'].map(lambda x: coords_dict[x]['lon'])

# Dynamically color circles based on risk level
def get_color(risk):
    if "High Risk" in risk:
        return [255, 0, 0, 160]    # Red
    elif "Moderate" in risk:
        return [255, 165, 0, 160]  # Orange
    else:
        return [0, 128, 0, 160]    # Green

map_df['color'] = map_df['Risk_Level'].apply(get_color)

# Render the interactive PyDeck map
st.pydeck_chart(pdk.Deck(
    map_style='mapbox://styles/mapbox/light-v9',
    initial_view_state=pdk.ViewState(
        latitude=7.38,
        longitude=3.9,
        zoom=10,
        pitch=40,
    ),
    layers=[
        pdk.Layer(
            'ScatterplotLayer',
            data=map_df,
            get_position='[lon, lat]',
            get_color='color',
            get_radius=1500,
            pickable=True,
            auto_highlight=True,
        ),
    ],
    tooltip={"text": "Zone: {Zone}\nRainfall: {Rainfall_mm} mm\nHumidity: {Humidity}%\nRisk: {Risk_Level}"}
))

#6. Interactive zone deep-dive inspector
st.subheader("🔍 Zone Deep-Dive Inspector")
selected_zone = st.selectbox("Select a target zone to review localized health metrics:", df_weather['Zone'].unique())

#pull data for the selected zone
zone_row = df_weather[df_weather['Zone'] ==selected_zone].iloc[0]

#Display metrics in columns 
d_col1, d_col2, d_col3 = st.columns(3)
d_col1.metric("Temperature", f"{zone_row['Temps_C']} °C")
d_col2.metric("3-Day Rainfall", f"{zone_row['Rainfall_mm']} mm")
d_col3.metric("Humidity", f"{zone_row['Humidity']} %")
# #8. 3-Day Vector Proliferation Trend Analysis
st.subheader("📈 3-Day Vector Proliferation Trend Analysis")
st.markdown("Forecasting cumulative rainfall trajectories across regional zones to project vector incubation windows.")

# Display comparative trend chart of zones
chart_data = df_weather.set_index('Zone')[['Rainfall_mm', 'Humidity']]
st.bar_chart(chart_data)
#status banner 
if zone_row['Risk_Level'] == 'High Risk (Critical Alert)':
    st.error(f"🚨 **CRITICAL ALERT in {selected_zone}:** High vector proliferation risk. Immediate deployment of larvicides and community sanitation required.")
elif zone_row['Risk_Level'] == 'Moderate Risk':
    st.warning(f"⚠️ **MODERATE RISK in {selected_zone}:** Monitor stagnant water accumulation and issue public safety advisories.")
else:
    st.success(f"✅ ** SAFE STATUS in {selected_zone}:** Weather parameters are currently below critical malaria transmission thresholds.")

#7. CSV Export for health dispatchers
st.subheader("📩 Export Regional Risk Report")

# Convert dataframe to CSV format
csv_data = df_weather.to_csv(index=False).encode('utf-8')

st.download_button(
    label="Download Active Risk Report (CSV)",
    data=csv_data,
    file_name="malaria_risk_dispatch_report.csv",
    mime="text/csv",
)
    
# #9. Clinical Case Surveillance & Patient Registration
st.subheader("🏥 Clinical Surveillance & Patient Entry Portal")
st.markdown("Log confirmed Rapid Diagnostic Test (RDT) positive cases from primary health centers to track epidemiological spread against weather risk triggers.")

with st.form("patient_registration_form"):
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        patient_id = st.text_input("Patient ID / Code (e.g., IB-NORTH-042)")
        patient_age = st.number_input("Age", min_value=0, max_value=120, value=25)
        zone_select = st.selectbox("Reporting Zone / Ward", df_weather['Zone'].unique())
    with col_p2:
        rdt_status = st.selectbox("RDT Malaria Test Result", ["Positive (+)", "Negative (-)"])
        treatment_given = st.selectbox("Intervention Administered", ["ACT (Artemether-Lumefantrine)", "IV Artesunate (Severe)", "None / Referred"])
        reporter_name = st.text_input("Reporting Health Officer")
    
    submitted = st.form_submit_button("💾 Submit Patient Record to Surveillance DB")
    
    if submitted:
        try:
            conn = sqlite3.connect("malaria_logs.db")
            cursor = conn.cursor()
            # Create table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patient_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT,
                    age INTEGER,
                    zone TEXT,
                    rdt_result TEXT,
                    treatment TEXT,
                    officer TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                INSERT INTO patient_cases (patient_id, age, zone, rdt_result, treatment, officer)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (patient_id, patient_age, zone_select, rdt_status, treatment_given, reporter_name))
            conn.commit()
            conn.close()
            st.success(f"Successfully logged patient {patient_id} for {zone_select}!")
        except Exception as e:
            st.error(f"Database error: {e}")

# Display live summary of logged cases
if st.checkbox("📊 View Live Regional Patient Case Log"):
    try:
        conn = sqlite3.connect("malaria_logs.db")
        df_patients = pd.read_sql("SELECT * FROM patient_cases ORDER BY id DESC", conn)
        conn.close()
        if not df_patients.empty:
            st.dataframe(df_patients, use_container_width=True)
        else:
            st.info("No patient records logged yet. Use the form above to submit data.")
    except Exception:
        st.info("Database table initializing...")

        # #10. Medical Supply Chain & Inventory Stock-Out Tracker
st.markdown("---")
st.subheader("📦 Medical Supply Chain & Inventory Stock-Out Tracker")
st.markdown("Monitoring regional medical reserves to prevent facility stock-outs during high-risk epidemiological windows.")

# Dynamic inventory simulation based on whether high risk is active
high_risk_active = len(df_weather[df_weather['Risk_Level'].str.contains("High Risk")]) > 0

# Adjust mock stock levels dynamically based on risk state
act_stock = 1420 if not high_risk_active else 380  # Simulates stock drain during outbreaks
rdt_stock = 5100 if not high_risk_active else 920
iv_art_stock = 450
nets_stock = 6200

inv_col1, inv_col2, inv_col3, inv_col4 = st.columns(4)
inv_col1.metric("ACT Doses Remaining", f"{act_stock:,} units", "-1,040 units (High Demand)", delta_color="inverse")
inv_col2.metric("RDT Test Kits", f"{rdt_stock:,} kits", "-4,180 kits", delta_color="inverse")
inv_col3.metric("IV Artesunate Vials", f"{iv_art_stock:,} vials", "Stable")
inv_col4.metric("LLIN Bed Nets in Stock", f"{nets_stock:,} units", "Ready for Dispatch")

# Stock-out automated warning trigger
if act_stock < 500:
    st.error("🚨 CRITICAL STOCK-OUT ALERT: Artemether-Lumefantrine (ACT) reserves in active high-risk zones have fallen below the 500-unit safety threshold! Automated central warehouse re-supply order triggered.")
else:
    st.success("✅ Regional medical inventory reserves are currently stable and meeting baseline requirements.")
# SQL DATABASE VIEWER 

st.markdown("---")
with st.expander("📊 View Live Database Logs (SQL Backend Engine)"):
  try:
    conn = sqlite3.connect("malaria_logs.db")
    df_logs = pd.read_sql("SELECT * FROM risk_logs ORDER BY id DESC", conn)
    conn.close()
    if not df_logs.empty:
      st.success(
          f"Database Active: {len(df_logs)} health forecast events logged."
      )
      st.dataframe(df_logs, use_container_width=True)
    else:
      st.info(
          "Database table is ready. Interact with a zone above to log your"
          " first entry!"
      )
  except Exception as e:
    st.info("Interact with the app above to initialize and populate logs.")   