import streamlit as st
import dropbox
import json
import pandas as pd
from datetime import datetime
import time
import os
import matplotlib.pyplot as plt
from pandas.plotting import table
from io import BytesIO

# --- 1. CONFIG & BRANDING ---
# Set page to wide mode and collapse sidebar for mobile users
st.set_page_config(
    page_title="Malaysian Street Vibes", 
    page_icon="🍜", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Set Matplotlib to non-GUI mode (prevents server crashes)
plt.switch_backend('Agg')

# CSS Styling
st.markdown("""
    <style>
    /* Center images */
    div[data-testid="stImage"] > img { display: block; margin-left: auto; margin-right: auto; }
    
    /* Metric Cards */
    .metric-card {
        background-color: #FFF8E1;
        border: 2px solid #5D4037;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 3px 3px 0px #5D4037;
    }
    
    /* Buttons */
    .stButton>button {
        font-weight: bold;
        border: 2px solid #5D4037 !important;
        color: #5D4037 !important;
    }
    .stButton>button[kind="primary"] {
        background-color: #5D4037 !important;
        color: white !important;
        border: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER LOGO ---
if os.path.exists("street_vibes.png"):
    st.image("street_vibes.png", width=250)
else:
    st.markdown("<h1 style='text-align: center;'>🍜 Malaysian Street Vibes</h1>", unsafe_allow_html=True)

st.write("---")

# --- 2. DROPBOX CONNECTION ---
try:
    dbx = dropbox.Dropbox(
        app_key=st.secrets["dropbox"]["app_key"],
        app_secret=st.secrets["dropbox"]["app_secret"],
        oauth2_refresh_token=st.secrets["dropbox"]["refresh_token"]
    )
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

# --- 3. HELPER FUNCTIONS ---

def get_weekly_filename(date_obj=None):
    """Generates filename like orders_2025_week05.json"""
    if date_obj is None: 
        date_obj = datetime.now()
    year = date_obj.strftime("%Y")
    week = date_obj.strftime("%U")
    return f"orders_{year}_week{week}.json"

def load_data(filename, default):
    """Downloads JSON from Dropbox"""
    try:
        _, res = dbx.files_download(f"/{filename}")
        return json.loads(res.content)
    except:
        return default

def save_data(filename, data):
    """Uploads JSON to Dropbox"""
    json_bytes = json.dumps(data, indent=4).encode('utf-8')
    dbx.files_upload(json_bytes, f"/{filename}", mode=dropbox.files.WriteMode("overwrite"))

def generate_html_report(df, date_str):
    """Creates a branded HTML file for printing"""
    total_revenue = df['Total'].str.replace('$', '').astype(float).sum()
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #FFF8E1; padding: 20px; }}
            .header {{ text-align: center; color: #5D4037; border-bottom: 3px solid #5D4037; padding-bottom: 10px; }}
            h1 {{ margin: 0; }}
            .info {{ margin-top: 10px; font-style: italic; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background-color: white; }}
            th {{ background-color: #5D4037; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #ddd; color: #333; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .footer {{ margin-top: 30px; text-align: right; font-size: 1.5em; font-weight: bold; color: #5D4037; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🍜 Malaysian Street Vibes</h1>
            <div class="info">Sales Report: Week of {date_str}</div>
        </div>
        {df.to_html(index=False, border=0)}
        <div class="footer">Total Revenue: ${total_revenue:.2f}</div>
    </body>
    </html>
    """
    return html

def generate_png_image(df):
    """Converts DataFrame to a PNG image"""
    rows = len(df)
    h = max(3, rows * 0.5 + 2) 
    fig, ax = plt.subplots(figsize=(10, h)) 
    ax.axis('off')
    tbl = table(ax, df, loc='center', cellLoc='left')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.2, 1.2)
    
    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#5D4037')
        else:
            cell.set_facecolor('#FFF8E1')
    
    plt.title("Malaysian Street Vibes - Order Report", fontsize=14, weight='bold', color='#5D4037', pad=20)
    
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', dpi=150)
    plt.close(fig) # Close to free memory
    return buf

# --- 4. NAVIGATION & SIDEBAR ---

# Correctly check for sidebar image
if os.path.exists("street_vibes.png"):
    st.sidebar.image("street_vibes.png", width=100)

st.sidebar.title("Navigation")
view_mode = st.sidebar.radio("Go to:", ["📝 Take Orders", "📊 Towkay Dashboard"], label_visibility="collapsed")

# ==========================================
# VIEW 1: TAKE ORDERS
# ==========================================
if view_mode == "📝 Take Orders":
    st.subheader("New Order Entry")
    
    current_filename = get_weekly_filename()
    st.caption(f"📂 Saving to: {current_filename}")
    
    menu = load_data("menu.json", {"Nasi Lemak": 5.0})
    if 'cart' not in st.session_state: st.session_state.cart = []

    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.info("👇 **Select Items**")
        item = st.selectbox("Menu Item", list(menu.keys()), label_visibility="collapsed")
        qty = st.number_input("Quantity", min_value=1, value=1, label_visibility="collapsed")
        
        if st.button("➕ Add", use_container_width=True):
            price = menu[item]
            st.session_state.cart.append({"item": item, "qty": qty, "price": price * qty})
            st.toast(f"Added {qty}x {item}")

    with col2:
        st.warning("🛒 **Cart**")
        if st.session_state.cart:
            total = 0
            for i in st.session_state.cart:
                st.text(f"{i['qty']}x {i['item']} (${i['price']:.2f})")
                total += i['price']
            st.divider()
            st.markdown(f"#### Total: ${total:.2f}")
            
            c_name = st.text_input("Customer Name", placeholder="e.g., Uncle Lim")
            
            if st.button("✅ CONFIRM", type="primary", use_container_width=True):
                if not c_name:
                    st.error("Name Required!")
                else:
                    with st.spinner("Saving..."):
                        orders = load_data(current_filename, [])
                        item_summary = ", ".join([f"{x['qty']}x {x['item']}" for x in st.session_state.cart])
                        
                        new_record = {
                            "id": int(time.time()),
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "time": datetime.now().strftime("%H:%M"),
                            "customer": c_name,
                            "items": st.session_state.cart,
                            "item_summary": item_summary,
                            "total": total,
                            "status": "New"
                        }
                        orders.append(new_record)
                        save_data(current_filename, orders)
                        st.session_state.cart = []
                        st.success("Sent! 🎉")
                        time.sleep(1)
                        st.rerun()
            if st.button("🗑️ Clear"):
                st.session_state.cart = []
                st.rerun()

# ==========================================
# VIEW 2: TOWKAY DASHBOARD
# ==========================================
elif view_mode == "📊 Towkay Dashboard":
    st.title("Towkay Dashboard")
    
    selected_date = st.date_input("Select Week to View:", value=datetime.now())
    target_filename = get_weekly_filename(datetime.combine(selected_date, datetime.min.time()))
    st.caption(f"Viewing File: `{target_filename}`")
    
    orders = load_data(target_filename, [])

    tab1, tab2, tab3 = st.tabs(["📈 Sales", "💾 Downloads", "🛠️ Menu"])

    # --- TAB 1: METRICS ---
    with tab1:
        if orders:
            total_rev = sum(o['total'] for o in orders)
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='metric-card'><h3>💰 Revenue</h3><h1>${total_rev:.2f}</h1></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'><h3>🧾 Orders</h3><h1>{len(orders)}</h1></div>", unsafe_allow_html=True)
            st.divider()

            # Kitchen Totals
            st.subheader("👨‍🍳 Kitchen Summary")
            item_totals = {}
            for order in orders:
                for item_obj in order['items']:
                    name = item_obj['item']
                    qty = item_obj['qty']
                    item_totals[name] = item_totals.get(name, 0) + qty
            
            if item_totals:
                totals_df = pd.DataFrame(list(item_totals.items()), columns=["Item", "To Cook"]).sort_values("To Cook", ascending=False)
                st.dataframe(totals_df, use_container_width=True, hide_index=True)

            # Raw Table
            st.subheader("📋 Transaction List")
            display_data = []
            for o in reversed(orders):
                display_data.append({
                    "Date": o['date'], "Time": o['time'], "Customer": o['customer'],
                    "Items": o.get('item_summary', ''), "Total": f"${o['total']:.2f}"
                })
            st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
        else:
            st.info("No orders found for this week.")

    # --- TAB 2: DOWNLOADS ---
    with tab2:
        st.header("Export Options")
        if orders:
            # Prepare clean DF
            export_data = []
            for o in reversed(orders):
                export_data.append({
                    "Date": o['date'], "Time": o['time'], "Customer": o['customer'],
                    "Items": o.get('item_summary', ''), "Total": f"${o['total']:.2f}"
                })
            df_export = pd.DataFrame(export_data)

            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button("⬇️ JSON (Backup)", data=json.dumps(orders, indent=4), file_name=target_filename, mime="application/json")
            
            with col2:
                html_file = generate_html_report(df_export, selected_date.strftime('%Y-%m-%d'))
                st.download_button("📄 HTML (Print)", data=html_file, file_name=f"report_{selected_date.strftime('%Y_wk%U')}.html", mime="text/html")
            
            with col3:
                png_buffer = generate_png_image(df_export)
                st.download_button("🖼️ PNG (Image)", data=png_buffer, file_name=f"sales_{selected_date.strftime('%Y_wk%U')}.png", mime="image/png")
        else:
            st.warning("No data to download.")

    # --- TAB 3: MENU ---
    with tab3:
        current = load_data("menu.json", {"Nasi Lemak": 5.0})
        edited = st.data_editor(pd.DataFrame(list(current.items()), columns=["Item", "Price"]), num_rows="dynamic", use_container_width=True)
        if st.button("💾 Save Menu"):
            save_data("menu.json", dict(zip(edited["Item"], edited["Price"])))
            st.success("Menu Updated!")