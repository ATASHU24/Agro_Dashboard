import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests
from datetime import timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="AGRO AGENT DASHBOARD", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- UI ENTERPRISE UPGRADE (FORCED OVERRIDE CSS) ---
st.markdown("""
    <style>
    /* Import modern font and force Streamlit to use it everywhere */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    html, body, [class*="css"], [class*="st-"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Hide the developer menus */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Padding fix for mobile */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 100px !important; 
    }
    
    /* Force Sleek Metric Cards and fix the text cutoff */
    div[data-testid="metric-container"] {
        background-color: #1e1e1e !important;
        border: 1px solid #333 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        border-left: 4px solid #0078D7 !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3) !important;
    }
    
    /* Prevents the weather numbers from getting cut off with '...' */
    div[data-testid="stMetricValue"] > div {
        white-space: normal !important; 
        font-size: 1.6rem !important;
        line-height: 1.2 !important;
    }
    
    /* Force Premium Buttons */
    .stButton>button, .stFormSubmitButton>button {
        border-radius: 8px !important;
        background-color: #0078D7 !important;
        color: white !important;
        border: none !important;
        transition: all 0.2s ease !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
    }
    
    .stButton>button:hover, .stFormSubmitButton>button:hover {
        background-color: #005A9E !important;
        transform: translateY(-2px) !important;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.4) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open("ATA_Agro_Database").sheet1

# --- SECURE AGENT DATABASE ---
VALID_AGENTS = {
    "alpha": {"name": "Youth Agent Alpha", "password": st.secrets["AGENT_ALPHA_PASS"], "region": "Taraba", "lat": 8.89, "lon": 11.36}, 
    "beta": {"name": "Youth Agent Beta", "password": st.secrets["AGENT_BETA_PASS"], "region": "Benue", "lat": 7.73, "lon": 8.52} 
}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['current_agent'] = None

# --- LIVE DATA FETCHING ---
@st.cache_data(ttl=timedelta(hours=1))
def fetch_regional_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        headers = {"User-Agent": "ATA_Innovate_Hub_Field_App/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return f"API Blocked (Error {response.status_code})"
            
        data = response.json()
        temp = data['current_weather']['temperature']
        wind = data['current_weather']['windspeed']
        return f"{temp}°C, Wind: {wind} km/h"
    except Exception as e:
        return f"System Error: {str(e)}"

@st.cache_data(ttl=timedelta(hours=2))
def fetch_market_prices():
    try:
        price_sheet = client.open("ATA_Agro_Database").worksheet("Market_Prices")
        records = price_sheet.get_all_records()
        prices = {}
        for row in records:
            crop_name = str(row.get('Crop', '')).strip().title()
            if crop_name:
                prices[crop_name] = {
                    "price": str(row.get('Price', 'N/A')),
                    "trend": str(row.get('Trend', ''))
                }
        return prices
    except Exception:
        return {}

# --- AI BACKEND ---
@st.cache_data(ttl=timedelta(days=1), show_spinner=False)
def call_gemini_api(query, target_language, region, live_weather, market_context):
    actual_language = "Nigerian Pidgin (Naija)" if target_language == "Pidgin English" else target_language
    
    sys_instruct = f"""
    You are the Chief Agricultural Advisor for ATA INNOVATE HUB. 
    Agent Location: {region} State. Weather: {live_weather}. Prices: {market_context}.
    
    CRITICAL INSTRUCTIONS FOR HIGH-QUALITY ANALYSIS:
    1. Provide a comprehensive, highly detailed agricultural diagnostic. 
    2. Structure: Start with a clear introductory paragraph diagnosing the issue. Follow this with EXACTLY 4 to 5 detailed bullet points explaining the scientific cause and step-by-step practical solutions.
    3. You MUST provide the ENTIRE, full-length response in {actual_language}. 
    4. Do NOT summarize or shorten the translation. The {actual_language} response must be just as long and detailed as the English version.
    5. Never cut off your response mid-sentence.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=sys_instruct)
        response = model.generate_content(query)
        return response.text
    except Exception as e:
        return f"🚨 AI Processing Error: {str(e)}"

def generate_local_advice(query, target_language, region, live_weather, market_prices):
    market_context = ", ".join([f"{c} at {d['price']}" for c, d in market_prices.items()]) if market_prices else "Unavailable"
    return call_gemini_api(query, target_language, region, live_weather, market_context)

# --- DATABASE FUNCTION ---
def save_to_sheet(agent_name, farmer_name, size, crop):
    sheet.append_row([agent_name, farmer_name, size, crop, "Synced"])

# --- 1. LOGIN SCREEN ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 AGRO AGENT DASHBOARD")
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
    
    live_weather = fetch_regional_weather(agent['lat'], agent['lon'])
    market_prices = fetch_market_prices()
    
    st.title("AGRO AGENT DASHBOARD")
    
    tab1, tab2, tab3 = st.tabs(["🤖 AI Command Center", "📈 Regional Data", "📝 Log Field Data"])

    with tab1:
        lang = st.selectbox("Language:", ["English", "Hausa", "Pidgin English", "Fulfulde"])
        query = st.text_area("Field Assistant Query:")
        if st.button("Analyze Data"):
            if not query.strip():
                st.warning("Please enter a query.")
            else:
                with st.spinner("Analyzing local conditions..."):
                    advice = generate_local_advice(query, lang, agent['region'], live_weather, market_prices)
                    st.write(advice)

    with tab2:
        st.subheader(f"Live Intelligence: {agent['region']} State")
        st.metric("Current Weather", live_weather)
        
        st.divider()
        st.subheader("Market Prices")
        if market_prices:
            cols = st.columns(3)
            for i, (crop, data) in enumerate(market_prices.items()):
                cols[i % 3].metric(crop, data["price"], data["trend"])
        else:
            st.info("Market pricing sheet is empty or unavailable.")

    with tab3:
        st.subheader("Register Farmer")
        with st.form("farmer_form", clear_on_submit=True):
            f_name = st.text_input("Farmer Name")
            f_size = st.text_input("Farm Size (Hectares)")
            f_crop = st.selectbox("Crop", ["Maize", "Cassava", "Rice", "Other"])
            if st.form_submit_button("Submit to ATA Database"):
                save_to_sheet(agent['name'], f_name, f_size, f_crop)
                st.success(f"Data for {f_name} saved securely to cloud!")

    # --- SIDEBAR ---
    with st.sidebar:
        st.write(f"**Agent:** {agent['name']}")
        st.write(f"**Operating Region:** {agent['region']}")
        st.divider()
        st.metric("Live Regional Weather", live_weather) 
        st.divider()
        
        if st.button("Log Out"):
            st.session_state['logged_in'] = False
            st.rerun()

if not st.session_state['logged_in']:
    login_screen()
else:
    main_dashboard()