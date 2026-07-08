import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests
from datetime import timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="ATA INNOVATE HUB", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- GOOGLE SHEETS CONNECTION ---
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open("ATA_Agro_Database").sheet1

# --- AGENT DATABASE ---
VALID_AGENTS = {
    "alpha": {"name": "Youth Agent Alpha", "password": "123", "region": "Taraba", "lat": 8.89, "lon": 11.36}, # Jalingo coords
    "beta": {"name": "Youth Agent Beta", "password": "456", "region": "Benue", "lat": 7.73, "lon": 8.52} # Makurdi coords
}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['current_agent'] = None

# --- LIVE DATA FETCHING (CACHED TO SAVE TOKENS) ---
@st.cache_data(ttl=timedelta(hours=12))
def fetch_regional_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(url)
        data = response.json()
        temp = data['current_weather']['temperature']
        wind = data['current_weather']['windspeed']
        return f"{temp}°C, Wind: {wind} km/h"
    except:
        return "Weather tracking temporarily offline"

# --- AI BACKEND (WITH CONTEXT INJECTION & TOKEN LIMITS) ---
def generate_local_advice(query, target_language, region, live_weather):
    # We use max_output_tokens to force short, cheap answers!
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"max_output_tokens": 150})
    
    # We inject the local data secretly into the AI's brain
    system_instruction = f"""
    You are the AI Command Center for ATA INNOVATE HUB. 
    The agent asking you this is currently in {region} State. 
    The current weather there is: {live_weather}.
    Use this local weather context to give practical, hyper-local agricultural advice.
    CRITICAL: Keep your response under 3 bullet points. Be direct. No long intros.
    Respond in {target_language}.
    """
    
    try:
        response = model.generate_content(system_instruction + query)
        return response.text
    except Exception as e:
        return "System temporarily offline. Standard protocols apply."

# --- DATABASE FUNCTION ---
def save_to_sheet(agent_name, farmer_name, size, crop):
    sheet.append_row([agent_name, farmer_name, size, crop, "Synced"])

# --- 1. LOGIN SCREEN ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 ATA INNOVATE HUB")
        with st.form("login_form"):
            username = st.text_input("Username").lower()
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Access Dashboard"):
                if username in VALID_AGENTS and VALID_AGENTS[username]["password"] == password:
                    st.session_state['logged_in'] = True
                    st.session_state['current_agent'] = VALID_AGENTS[username]
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

# --- 2. MAIN DASHBOARD ---
def main_dashboard():
    agent = st.session_state['current_agent']
    
    # 1. FETCH LIVE DATA (Happens instantly from memory if already checked today)
    live_weather = fetch_regional_weather(agent['lat'], agent['lon'])
    
    st.title("ATA INNOVATE HUB - Agro-Agent Dashboard")
    tab1, tab2, tab3 = st.tabs(["🤖 AI Command Center", "📈 Regional Data", "📝 Log Field Data"])

    with tab1:
        lang = st.selectbox("Language:", ["English", "Hausa", "Pidgin English", "Fulfulde"])
        query = st.text_area("Field Assistant Query:")
        if st.button("Analyze Data"):
            with st.spinner("Analyzing local conditions..."):
                # 2. INJECT DATA INTO AI
                advice = generate_local_advice(query, lang, agent['region'], live_weather)
                st.write(advice)

    with tab2:
        st.subheader(f"Live Intelligence: {agent['region']} State")
        col1, col2 = st.columns(2)
        col1.metric("Current Weather", live_weather)
        col2.metric("Maize Price (Est)", "₦450,000", "5.2%")

    with tab3:
        st.subheader("Register Farmer")
        with st.form("farmer_form", clear_on_submit=True):
            f_name = st.text_input("Farmer Name")
            f_size = st.text_input("Farm Size (Hectares)")
            f_crop = st.selectbox("Crop", ["Maize", "Cassava", "Rice", "Other"])
            if st.form_submit_button("Submit to ATA Database"):
                save_to_sheet(agent['name'], f_name, f_size, f_crop)
                st.success(f"Data for {f_name} saved securely to cloud!")

    with st.sidebar:
        st.write(f"**Agent:** {agent['name']}")
        st.write(f"**Operating Region:** {agent['region']}")
        if st.button("Log Out"):
            st.session_state['logged_in'] = False
            st.rerun()

if not st.session_state['logged_in']:
    login_screen()
else:
    main_dashboard()