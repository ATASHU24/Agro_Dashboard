import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
st.set_page_config(page_title="ATA INNOVATE HUB", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- GOOGLE SHEETS CONNECTION ---
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open("ATA_Agro_Database").sheet1

# --- AGENT DATABASE (AUTHENTICATION) ---
VALID_AGENTS = {
    "alpha": {"name": "Youth Agent Alpha", "password": "123", "region": "Taraba State"},
    "beta": {"name": "Youth Agent Beta", "password": "456", "region": "Benue State"}
}

# --- INITIALIZE STATES ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['current_agent'] = None

# --- AI BACKEND LOGIC ---
def generate_local_advice(query, target_language):
    model = genai.GenerativeModel('gemini-2.5-flash')
    system_instruction = f"You are the AI Command Center for ATA INNOVATE HUB. Respond in {target_language}."
    try:
        response = model.generate_content(system_instruction + query)
        return response.text
    except:
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
    st.title("ATA INNOVATE HUB - Agro-Agent Dashboard")
    tab1, tab2, tab3 = st.tabs(["🤖 AI Command Center", "📈 Regional Data", "📝 Log Field Data"])

    with tab1:
        lang = st.selectbox("Language:", ["English", "Hausa", "Pidgin English", "Fulfulde"])
        query = st.text_area("Field Assistant Query:")
        if st.button("Analyze Data"):
            st.write(generate_local_advice(query, lang))

    with tab2:
        st.subheader("Market Intelligence")
        st.metric("Maize Price", "₦450,000", "5.2%")

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
        if st.button("Log Out"):
            st.session_state['logged_in'] = False
            st.rerun()

if not st.session_state['logged_in']:
    login_screen()
else:
    main_dashboard()