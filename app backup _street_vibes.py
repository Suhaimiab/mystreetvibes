import streamlit as st
from google import genai
import json
import pandas as pd
import os

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="Malaysian Kitchen AI", layout="wide")
DATA_FILE = "menu_data.json"

# YOUR WORKING KEY
RAW_KEY = "AIzaSyCG-jd3F3Ucw9I1g50HDTolSxPajezQW_Y"
API_KEY = RAW_KEY.strip()

# --- 2. DATA PERSISTENCE ---
def load_menu():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return pd.DataFrame(json.load(f))
    else:
        return pd.DataFrame([
            {"Category": "Main", "Item": "Itik Salai Masak Lemak", "Price": 3.8, "Description": "Rice, Sambal, Timun + Hot Drink", "Keywords": "itik, duck"},
            {"Category": "Main", "Item": "Ayam Masak Lemak", "Price": 3.5, "Description": "Rice, Sambal, Timun + Hot Drink", "Keywords": "ayam masak"},
            {"Category": "Combo", "Item": "Family Set A", "Price": 12.0, "Description": "4x Nasi Ayam Madu + 4x Teh O Ice", "Keywords": "family set"},
            {"Category": "Drink", "Item": "Teh Tarik", "Price": 0.5, "Description": "Hot Milk Tea", "Keywords": "teh, tea"}
        ])

def save_menu(df):
    df.to_json(DATA_FILE, orient="records", indent=2)

if 'menu_data' not in st.session_state:
    st.session_state.menu_data = load_menu()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    st.success(f"Connected to Gemini Flash Latest")
    st.divider()
    
    st.header("📋 Menu Editor")
    edited_menu = st.data_editor(
        st.session_state.menu_data,
        num_rows="dynamic",
        width='stretch',
        column_config={
            "Price": st.column_config.NumberColumn(format="%.2f OMR"),
            "Category": st.column_config.SelectboxColumn(options=["Main", "Combo", "Drink", "Side"])
        }
    )
    
    if not edited_menu.equals(st.session_state.menu_data):
        st.session_state.menu_data = edited_menu
        save_menu(edited_menu)

# --- 4. MAIN AI LOGIC ---
st.title("🍜 AI Order Manager")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📥 Paste WhatsApp Message")
    msg = st.text_area("Customer Text:", height=150)
    run = st.button("Process Order", type="primary", width='stretch')

with col2:
    st.subheader("🧑‍🍳 Kitchen Ticket")
    
    if run and msg:
        try:
            client = genai.Client(api_key=API_KEY)
            
            menu_str = st.session_state.menu_data.to_string(index=False)
            
            prompt = f"""
            Act as a POS system. Map the input to the menu below.
            MENU: {menu_str}
            RULES: 
            1. Handle combos based on 'Description'.
            2. Return JSON: {{ "items": [{{"name": str, "qty": int, "price": float, "notes": str}}], "total": float }}
            INPUT: {msg}
            """
            
            # --- THE FIX ---
            # We use 'gemini-flash-latest' which was in your available list
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            
            data = json.loads(response.text)
            
            st.success(f"Total: {data['total']} OMR")
            st.dataframe(pd.DataFrame(data['items']), width='stretch')
            
        except Exception as e:
            st.error(f"Error: {e}")
            
            # Backup option if 'latest' is also busy
            if "429" in str(e):
                st.warning("Quota full? Try using 'gemini-2.0-flash-lite-preview-02-05' in line 88 instead.")