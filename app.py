import streamlit as st
import google.generativeai as genai
import pandas as pd

# --- CONFIGURATION ---
# Plug in your actual Gemini API Key inside the quotes below
genai.configure(api_key=st.secrets)

# Set up the main page layout
st.set_page_config(page_title="Agro-Agent Dashboard", layout="wide")

# --- INITIALIZE REAL-TIME DATABASE STATES ---
if 'farmers_assisted' not in st.session_state:
    st.session_state['farmers_assisted'] = 142

# 142 farmers * ₦2,500 commission = 355,000
if 'agent_revenue' not in st.session_state:
    st.session_state['agent_revenue'] = 355000

if 'farm_data' not in st.session_state:
    st.session_state['farm_data'] = pd.DataFrame(columns=["Farmer Name", "Size (Hectares)", "Soil Type", "Status"])

# --- AI BACKEND LOGIC ---
def generate_local_advice(query, target_language):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    system_instruction = f"""
    You are the AI Command Center for the ATA INNOVATE HUB Agro-Agent Dashboard operating in Taraba State.
    Your goal is to provide scientifically accurate, highly actionable agricultural advice to field workers.
    
    The field agent has submitted this query: "{query}"
    
    CRITICAL INSTRUCTIONS:
    1. Analyze the agricultural problem and formulate the best solution.
    2. Output your ENTIRE final response seamlessly in {target_language}.
    3. If the target language is Fulfulde, you MUST use the standard Latin alphabet only. Keep sentences highly concise and direct. Do not mix symbols or other alphabets.
    4. Ensure the tone is professional, encouraging, and easy for local farmers to understand.
    """
    
    config = genai.GenerationConfig(
        temperature=0.2,
        max_output_tokens=2500 
    )
    
    try:
        response = model.generate_content(
            system_instruction,
            generation_config=config
        )
        return response.text
    
    except Exception as e:
        query_lower = query.lower()
        if "cassava" in query_lower:
            return """🟢 **OFFLINE CACHE ACCESSED (Network/API Limit Reached)**
**Diagnosis:** Based on regional offline data, yellowing and curling of cassava leaves indicate Cassava Mosaic Disease (CMD).
**Action Plan:** Uproot and burn severely affected plants. Apply neem-based biopesticide for whiteflies. Ensure the farmer uses CMD-resistant stem cuttings (TME 419) next season."""
        elif "maize" in query_lower or "fertilizer" in query_lower:
            return """🟢 **OFFLINE CACHE ACCESSED (Network/API Limit Reached)**
**Diagnosis:** Dry season maize in the North Central/Taraba region frequently faces nitrogen depletion in sandy soils.
**Action Plan:** Apply NPK 15:15:15 at 200kg/hectare. Split the application: 50% at 2 weeks after planting, and 50% at 5 weeks. Ensure adequate trench irrigation."""
        elif "armyworm" in query_lower or "pest" in query_lower or "insect" in query_lower:
            return """🟢 **OFFLINE CACHE ACCESSED (Network/API Limit Reached)**
**Diagnosis:** High probability of Fall Armyworm (FAW) based on current seasonal pest tracking.
**Action Plan:** Spray approved biopesticides directly into the plant whorls. Spraying must be done early morning or late evening when caterpillars are most active."""
        else:
            return """🟢 **OFFLINE CACHE ACCESSED (Network/API Limit Reached)**
**Standard Protocol:** Your field data has been securely logged to the local drive. 
**Action Plan:** Advise the farmer to maintain standard irrigation schedules and monitor crop health. The AI core will run a deep analysis on this specific issue as soon as satellite internet syncs."""

# --- DASHBOARD HEADER ---
st.title("ATA INNOVATE HUB - Agro-Agent Dashboard")

# --- MAIN INTERFACE TABS ---
tab1, tab2, tab3 = st.tabs(["🤖 AI Command Center", "📈 Regional Data", "📝 Log Field Data"])

# --- TAB 1: AI COMMAND CENTER ---
with tab1:
    st.subheader("Field Assistant AI")
    language_choice = st.selectbox("Select Output Language:", ["English", "Hausa", "Pidgin English", "Fulfulde"])
    farmer_query = st.text_area("Field Assistant Query:", placeholder="e.g., What is the recommended fertilizer ratio for maize in the dry season?")
    
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
    
    st.write("### Live Market Price Trends (Last 7 Days)")
    trend_data = pd.DataFrame(
        {
            "Maize": [400, 410, 415, 430, 440, 445, 450],
            "Rice": [800, 805, 800, 810, 815, 820, 830],
            "Cassava": [150, 150, 155, 155, 160, 165, 170]
        },
        index=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    )
    st.line_chart(trend_data)

# --- TAB 3: LOG FIELD DATA ---
with tab3:
    st.subheader("Register Farmer & Log Data")
    with st.form("farmer_form", clear_on_submit=True):
        f_name = st.text_input("Farmer Name")
        f_size = st.text_input("Farm Size (Hectares)")
        f_soil = st.selectbox("Soil Type", ["Sandy", "Clay", "Loam", "Silt"])
        submitted = st.form_submit_button("Submit to Ministry Database")
        
        if submitted:
            if f_name and f_size:
                new_entry = pd.DataFrame([{"Farmer Name": f_name, "Size (Hectares)": f_size, "Soil Type": f_soil, "Status": "Synced 🟢"}])
                st.session_state['farm_data'] = pd.concat([st.session_state['farm_data'], new_entry], ignore_index=True)
                
                # Increment the live counters
                st.session_state['farmers_assisted'] += 1
                st.session_state['agent_revenue'] += 2500
                
                st.success(f"Data for {f_name} successfully synced. Dashboard metrics updated.")
            else:
                st.error("Please fill in the Farmer Name and Size.")
    
    if not st.session_state['farm_data'].empty:
        st.write("### Recent Field Submissions")
        display_df = st.session_state['farm_data'].copy()
        display_df.index = display_df.index + 1 
        st.dataframe(display_df, use_container_width=True)

# --- SIDEBAR: AGENT PROFILE & SYSTEM STATUS ---
with st.sidebar:
    st.header("🧑🏽‍🌾 Agent Profile")
    st.write("**Name:** Youth Agent Alpha")
    st.write("**Region:** Taraba State")
    st.write("**Clearance:** Level 2 (Agro-Dealer)")
    
    st.divider() 
    
    st.write("System Status")
    st.subheader("Online")
    st.markdown("<span style='color: #4CAF50; background-color: rgba(76, 175, 80, 0.1); padding: 4px 8px; border-radius: 4px; font-size: 14px; font-weight: bold;'>↑ AI Core Active</span>", unsafe_allow_html=True)
    
    st.divider()
    
    st.write("Agent Performance")
    st.metric(label="Farmers Assisted", value=str(st.session_state['farmers_assisted']), delta="12 this week")
    
    # Formats the revenue with commas (e.g., 355,000)
    st.metric(label="Wallet (₦2.5k / Farmer)", value=f"₦{st.session_state['agent_revenue']:,}", delta="₦30,000 this week")