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
st.set_page_config(
    page_title="Malaysian Street Vibes", 
    page_icon="🍜", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

plt.switch_backend('Agg')

# CSS Styling
st.markdown("""
    <style>
    div[data-testid="stImage"] > img { display: block; margin-left: auto; margin-right: auto; }
    
    .metric-card {
        background-color: #FFF8E1;
        border: 2px solid #5D4037;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 3px 3px 0px #5D4037;
    }
    
    /* BIG BUTTONS FOR CUSTOMERS */
    .stButton>button {
        font-weight: bold;
        border: 2px solid #5D4037 !important;
        color: #5D4037 !important;
        height: 3em;
    }
    .stButton>button[kind="primary"] {
        background-color: #5D4037 !important;
        color: white !important;
        border: none !important;
    }
    .stButton>button[kind="secondary"] {
        background-color: #f0f2f6 !important;
        color: #31333F !important;
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
    st.error("System Offline. Please contact staff.")
    st.stop()

# --- 3. HELPER FUNCTIONS ---
def get_weekly_filename(date_obj=None):
    if date_obj is None: date_obj = datetime.now()
    year = date_obj.strftime("%Y")
    week = date_obj.strftime("%U")
    return f"orders_{year}_week{week}.json"

def load_data(filename, default):
    try:
        _, res = dbx.files_download(f"/{filename}")
        return json.loads(res.content)
    except:
        return default

def save_data(filename, data):
    json_bytes = json.dumps(data, indent=4).encode('utf-8')
    dbx.files_upload(json_bytes, f"/{filename}", mode=dropbox.files.WriteMode("overwrite"))

# Export Functions
def generate_html_report(df, date_str):
    total_revenue = df['Total'].str.replace('OMR ', '').astype(float).sum()
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #FFF8E1; padding: 20px; }}
            .header {{ text-align: center; color: #5D4037; border-bottom: 3px solid #5D4037; padding-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background-color: white; }}
            th {{ background-color: #5D4037; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            .footer {{ margin-top: 30px; text-align: right; font-size: 1.5em; font-weight: bold; color: #5D4037; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🍜 Malaysian Street Vibes</h1>
            <div>Weekly Report: {date_str}</div>
        </div>
        {df.to_html(index=False, border=0)}
        <div class="footer">Total Revenue: OMR {total_revenue:.3f}</div>
    </body>
    </html>
    """
    return html

def generate_png_image(df):
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
    plt.title("Malaysian Street Vibes - Report", fontsize=14, weight='bold', color='#5D4037', pad=20)
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', dpi=150)
    plt.close(fig)
    return buf

# --- 4. NAVIGATION ---
if os.path.exists("street_vibes.png"):
    st.sidebar.image("street_vibes.png", width=100)

st.sidebar.title("App Mode")
app_mode = st.sidebar.radio("Select Mode:", ["🍽️ Customer Menu", "🔐 Owner Login"])

# ==========================================
# MODE 1: CUSTOMER MENU (State-Based)
# ==========================================
if app_mode == "🍽️ Customer Menu":
    
    # Initialize Session States
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'order_step' not in st.session_state: st.session_state.order_step = 'menu'
    if 'customer_meta' not in st.session_state: st.session_state.customer_meta = {}

    # --- STEP 1: MENU SELECTION ---
    if st.session_state.order_step == 'menu':
        
        # --- NEW: CUSTOMER GUIDE ---
        with st.expander("ℹ️ How to Order / Cara Memesan"):
            st.markdown("""
            1. **Select Food:** Click the 'Add' button next to the items you want.
            2. **Check Cart:** Look at the 'Your Basket' section.
            3. **Review:** Click 'Review Order', enter your name, and choose Dine-in/Takeaway.
            4. **Submit:** Click 'Confirm & Send'.
            """)
        
        st.markdown("### 👋 Welcome! Please select your items.")
        
        menu = load_data("menu.json", {"Nasi Lemak": 1.500})
        col1, col2 = st.columns([1.5, 1])
        
        with col1:
            st.info("🍛 **Menu**")
            for item_name, item_price in menu.items():
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.write(f"**{item_name}**")
                    st.caption(f"OMR {item_price:.3f}")
                with c2:
                    qty = st.number_input("Qty", min_value=1, value=1, key=f"qty_{item_name}", label_visibility="collapsed")
                with c3:
                    # FIX 1: use_container_width -> width='stretch'
                    if st.button("Add", key=f"btn_{item_name}", width="stretch"):
                        st.session_state.cart.append({"item": item_name, "qty": qty, "price": item_price * qty})
                        st.toast(f"✅ Added {qty}x {item_name}")
                st.divider()

        with col2:
            st.warning("🛒 **Your Basket**")
            if st.session_state.cart:
                total = 0
                for i in st.session_state.cart:
                    st.text(f"{i['qty']}x {i['item']} (OMR {i['price']:.3f})")
                    total += i['price']
                st.divider()
                st.markdown(f"### Total: OMR {total:.3f}")
                
                c_name = st.text_input("Your Name / Nama", placeholder="Enter Name")
                t_no = st.selectbox("Order Type", ["Takeaway", "Dine-in"])
                
                # FIX 2: use_container_width -> width='stretch'
                if st.button("📝 REVIEW ORDER", type="primary", width="stretch"):
                    if not c_name:
                        st.error("Name is required!")
                    else:
                        st.session_state.customer_meta = {"name": c_name, "table": t_no, "total": total}
                        st.session_state.order_step = 'review'
                        st.rerun()
                
                if st.button("❌ Clear Cart"):
                    st.session_state.cart = []
                    st.rerun()
            else:
                st.info("Basket is empty.")

    # --- STEP 2: REVIEW ORDER ---
    elif st.session_state.order_step == 'review':
        st.markdown("### 🧐 Please Confirm Your Order")
        
        meta = st.session_state.customer_meta
        st.success(f"**Customer:** {meta['name']} | **Type:** {meta['table']}")
        
        review_data = [{"Qty": i['qty'], "Item": i['item'], "Price": f"{i['price']:.3f}"} for i in st.session_state.cart]
        st.table(pd.DataFrame(review_data))
        
        st.markdown(f"## Total Amount: OMR {meta['total']:.3f}")
        
        c1, c2 = st.columns(2)
        with c1:
            # FIX 3: use_container_width -> width='stretch'
            if st.button("⬅️ Back / Edit", width="stretch"):
                st.session_state.order_step = 'menu'
                st.rerun()
        with c2:
            # FIX 4: use_container_width -> width='stretch'
            if st.button("✅ CONFIRM & SEND", type="primary", width="stretch"):
                with st.spinner("Sending to Kitchen..."):
                    current_filename = get_weekly_filename()
                    orders = load_data(current_filename, [])
                    item_summary = ", ".join([f"{x['qty']}x {x['item']}" for x in st.session_state.cart])
                    
                    new_record = {
                        "id": int(time.time()),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "time": datetime.now().strftime("%H:%M"),
                        "customer": f"{meta['name']} ({meta['table']})",
                        "items": st.session_state.cart,
                        "item_summary": item_summary,
                        "total": meta['total'],
                        "status": "New"
                    }
                    orders.append(new_record)
                    save_data(current_filename, orders)
                    st.session_state.order_step = 'success'
                    st.rerun()

    # --- STEP 3: SUCCESS ---
    elif st.session_state.order_step == 'success':
        st.balloons()
        st.title("✅ Order Received!")
        st.write("---")
        st.markdown("### Thank you for your order.")
        st.markdown("See you at **Orange Pearl Tea** on **Friday from 1.30pm onwards**!!")
        st.info("Your Order ID has been sent to the kitchen.")
        
        st.write("")
        st.write("")
        # FIX 5: use_container_width -> width='stretch'
        if st.button("🏠 Start New Order", type="primary", width="stretch"):
            st.session_state.cart = []
            st.session_state.order_step = 'menu'
            st.session_state.customer_meta = {}
            st.rerun()

# ==========================================
# MODE 2: OWNER LOGIN
# ==========================================
elif app_mode == "🔐 Owner Login":
    
    with st.sidebar.form("login_form"):
        pwd = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Login")
    
    correct_pwd = st.secrets["admin"]["password"] if "admin" in st.secrets else "admin123"
    
    if submit_btn and pwd == correct_pwd:
        st.session_state['authenticated'] = True
    elif submit_btn and pwd != correct_pwd:
        st.sidebar.error("Wrong Password")

    if st.session_state.get('authenticated', False):
        st.title("📊 Towkay Dashboard")
        if st.button("🔄 Refresh Data"): st.rerun()
            
        selected_date = st.date_input("Select Week:", value=datetime.now())
        target_filename = get_weekly_filename(datetime.combine(selected_date, datetime.min.time()))
        st.caption(f"Reading: `{target_filename}`")
        orders = load_data(target_filename, [])

        tab1, tab2, tab3 = st.tabs(["🔥 Kitchen Live", "💰 Sales & Reports", "🛠️ Edit Menu"])

        # TAB 1: KITCHEN LIVE
        with tab1:
            st.subheader("Incoming Orders")
            if orders:
                for o in reversed(orders):
                    with st.expander(f"🕒 {o['time']} - {o['customer']} (OMR {o['total']:.3f})", expanded=True):
                        st.write(f"**Items:** {o.get('item_summary', '')}")
            else:
                st.info("No orders yet.")

        # TAB 2: SALES REPORTS
        with tab2:
            if orders:
                total_rev = sum(o['total'] for o in orders)
                c1, c2 = st.columns(2)
                c1.markdown(f"<div class='metric-card'><h3>💰 Total Revenue</h3><h1>OMR {total_rev:.3f}</h1></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-card'><h3>🧾 Total Orders</h3><h1>{len(orders)}</h1></div>", unsafe_allow_html=True)
                st.divider()

                st.subheader("👥 Orders by Customer Name")
                cust_data = []
                for o in orders:
                    cust_data.append({
                        "Customer": o['customer'],
                        "Time": o['time'],
                        "Items": o['item_summary'],
                        "Total (OMR)": f"{o['total']:.3f}"
                    })
                df_cust = pd.DataFrame(cust_data).sort_values(by="Customer")
                st.dataframe(df_cust, use_container_width=True, hide_index=True)

                st.divider()

                st.subheader("🔥 Dish Performance")
                item_stats = {}
                for order in orders:
                    for item_obj in order['items']:
                        name = item_obj['item']
                        qty = item_obj['qty']
                        price = item_obj['price']
                        if name not in item_stats: item_stats[name] = {'qty': 0, 'revenue': 0.0}
                        item_stats[name]['qty'] += qty
                        item_stats[name]['revenue'] += price

                if item_stats:
                    stats_data = [{"Menu Item": k, "Qty Sold": v['qty'], "Total Revenue (OMR)": f"{v['revenue']:.3f}"} for k, v in item_stats.items()]
                    st.dataframe(pd.DataFrame(stats_data).sort_values("Qty Sold", ascending=False), use_container_width=True, hide_index=True)

                st.divider()
                st.subheader("Export")
                
                export_data = []
                for o in reversed(orders):
                    export_data.append({
                        "Date": o['date'], 
                        "Time": o['time'], 
                        "Customer": o['customer'], 
                        "Items": o.get('item_summary', ''), 
                        "Total": f"OMR {o['total']:.3f}"
                    })
                df_export = pd.DataFrame(export_data)
                
                c1, c2, c3 = st.columns(3)
                with c1: 
                    st.download_button("⬇️ JSON", json.dumps(orders, indent=4), target_filename, "application/json")
                with c2: 
                    st.download_button("📄 HTML", generate_html_report(df_export, selected_date.strftime('%Y-%m-%d')), "report.html", "text/html")
                with c3: 
                    st.download_button("🖼️ PNG", generate_png_image(df_export), "report.png", "image/png")
    
        # TAB 3: MENU
        with tab3:
            current = load_data("menu.json", {"Nasi Lemak": 1.500})
            edited = st.data_editor(pd.DataFrame(list(current.items()), columns=["Item", "Price (OMR)"]), num_rows="dynamic", use_container_width=True)
            if st.button("💾 Save Menu"):
                save_data("menu.json", dict(zip(edited["Item"], edited["Price (OMR)"])))
                st.success("Menu Updated!")

    else:
        st.info("Please log in to view data.")

else:
    st.write("Please select a mode.")