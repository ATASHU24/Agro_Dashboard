import streamlit as st
import google.generativeai as genai
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Agro-Agent Dashboard", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- AGENT DATABASE (AUTHENTICATION) ---
# Hardcoded credentials for your initial team
VALID_AGENTS = {
    "alpha": {"name": "Youth Agent Alpha", "password": "123", "region": "Taraba State"},
    "beta": {"name": "Youth Agent Beta", "password": "456", "region": "Benue State"}
}

# --- INITIALIZE REAL-TIME DATABASE STATES ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['current_agent'] = None

if 'farmers_assisted' not in st.session_state:
    st.session_state['farmers_assisted'] = 0

if 'agent_revenue' not in st.session_state:
    st.session_state['agent_revenue'] = 0

if 'farm_data' not in st.session_state:
    # Notice this exactly matches your new Google Sheet columns!
    st.session_state['farm_data'] = pd.DataFrame(columns=["Agent Name", "Farmer Name", "Size (Hectares)", "Crop / Soil Type", "Status"])

# --- AI BACKEND LOGIC ---
def generate_local_advice(query, target_language):
    model = genai.GenerativeModel('gemini-2.5-flash')
    system_instruction = f"""
    You are the AI Command Center for the ATA INNOVATE HUB Agro-Agent Dashboard.
    Your goal is to provide scientifically accurate, highly actionable agricultural advice to field workers.
    The field agent has submitted this query: "{query}"
    Output your ENTIRE final response seamlessly in {target_language}.
    """
    config = genai.GenerationConfig(temperature=0.2, max_output_tokens=2500)
    
    try:
        response = model.generate_content(system_instruction, generation_config=config)
        return response.text
    except Exception as e:
        return f"🟢 **OFFLINE CACHE ACCESSED**\nNetwork limitation reached. Standard protocol: maintain irrigation and monitor crop health."

# --- 1. LOGIN SCREEN INTERFACE ---
def login_screen():
    # Adding some blank space to center the login box
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 ATA INNOVATE HUB")
        st.subheader("Field Agent Secure Portal")
        
        with st.form("login_form"):
            st.write("Please log in to access your regional dashboard.")
            username = st.text_input("Username (Try: alpha)").lower()
            password = st.text_input("Password (Try: 123)", type="password")
            submit = st.form_submit_button("Access Dashboard")
            
            if submit:
                if username in VALID_AGENTS and VALID_AGENTS[username]["password"] == password:
                    st.session_state['logged_in'] = True
                    st.session_state['current_agent'] = VALID_AGENTS[username]
                    st.rerun() # Instantly reloads the page to show dashboard
                else:
                    st.error("Access Denied: Invalid username or password.")

# --- 2. MAIN DASHBOARD INTERFACE ---
def main_dashboard():
    agent = st.session_state['current_agent']
    
    st.title("ATA INNOVATE HUB - Agro-Agent Dashboard")
    tab1, tab2, tab3 = st.tabs(["🤖 AI Command Center", "📈 Regional Data", "📝 Log Field Data"])

    # --- TAB 1: AI COMMAND CENTER ---
    with tab1:
        st.subheader("Field Assistant AI")
        language_choice = st.selectbox("Select Output Language:", ["English", "Hausa", "Pidgin English", "Fulfulde"])
        farmer_query = st.text_area("Field Assistant Query:")
        
        if st.button("Analyze Data"):
            if farmer_query:
                with st.spinner(f"Generating data in {language_choice}..."):
                    final_advice = generate_local_advice(farmer_query, language_choice)
                    st.success("Analysis Complete")
                    st.write(final_advice)
            else:
                st.warning("Please enter a query first.")

    # --- TAB 2: REGIONAL DATA ---
    with tab2:
        st.subheader("Regional Agricultural Metrics")
        col1, col2, col3 = st.columns(3)
        col1.metric(label="Maize (Per Ton)", value="₦450,000", delta="5.2%")
        col2.metric(label="Fertilizer Stock (Bags)", value="1,240", delta="-120")
        col3.metric(label="Rainfall Forecast", value="High Risk", delta="80% Chance", delta_color="inverse")

    # --- TAB 3: LOG FIELD DATA ---
    with tab3:
        st.subheader("Register Farmer & Log Data")
        with st.form("farmer_form", clear_on_submit=True):
            f_name = st.text_input("Farmer Name")
            f_size = st.text_input("Farm Size (Hectares)")
            f_soil = st.selectbox("Crop / Soil Type", ["Maize / Sandy", "Cassava / Clay", "Rice / Loamy", "Other"])
            submitted = st.form_submit_button("Submit to ATA Database")
            
            if submitted:
                if f_name and f_size:
                    # Automatically tags the specific agent who is logged in!
                    new_entry = pd.DataFrame([{
                        "Agent Name": agent['name'], 
                        "Farmer Name": f_name, 
                        "Size (Hectares)": f_size, 
                        "Crop / Soil Type": f_soil, 
                        "Status": "Pending Cloud Sync ☁️"
                    }])
                    st.session_state['farm_data'] = pd.concat([st.session_state['farm_data'], new_entry], ignore_index=True)
                    
                    st.session_state['farmers_assisted'] += 1
                    st.session_state['agent_revenue'] += 2500
                    st.success(f"Data for {f_name} recorded securely by {agent['name']}.")
                else:
                    st.error("Please fill in the Farmer Name and Size.")
        
        if not st.session_state['farm_data'].empty:
            st.write("### Recent Field Submissions")
            display_df = st.session_state['farm_data'].copy()
            display_df.index = display_df.index + 1 
            st.dataframe(display_df, use_container_width=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("🧑🏽‍🌾 Agent Profile")
        # Dynamically displays the logged-in agent's details
        st.write(f"**Name:** {agent['name']}")
        st.write(f"**Region:** {agent['region']}")
        st.write("**Clearance:** Level 2 (Agro-Dealer)")
        
        st.divider() 
        
        st.write("Agent Performance")
        st.metric(label="Farmers Assisted", value=str(st.session_state['farmers_assisted']))
        st.metric(label="Wallet (₦2.5k / Farmer)", value=f"₦{st.session_state['agent_revenue']:,}")
        
        st.divider()
        if st.button("Log Out"):
            st.session_state['logged_in'] = False
            st.session_state['current_agent'] = None
            st.rerun() # instantly sends them back to the login screen

# --- APP ROUTING (THE GATEKEEPER) ---
if not st.session_state['logged_in']:
    login_screen()
else:
    main_dashboard()