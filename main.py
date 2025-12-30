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
from dropbox.exceptions import ApiError

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
    
    .stButton>button {
        font-weight: bold;
        height: 3em;
        transition: all 0.2s ease-in-out;
    }
    
    /* Primary (Red/Brown) */
    .stButton>button[kind="primary"] {
        background-color: #5D4037 !important;
        color: white !important;
        border: none !important;
    }
    .stButton>button[kind="primary"]:active {
        background-color: #3E2723 !important;
    }

    /* Secondary (Light) */
    .stButton>button[kind="secondary"] {
        background-color: #EFEBE9 !important;
        color: #5D4037 !important;
        border: 1px solid #D7CCC8 !important;
    }
    .stButton>button[kind="secondary"]:active {
        background-color: #A1887F !important;
        color: white !important;
    }
    
    /* SYNC STATUS BOX */
    .sync-box {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 5px solid #ccc;
    }
    .sync-online { background-color: #E8F5E9; border-color: #4CAF50; color: #1B5E20; }
    .sync-offline { background-color: #FFEBEE; border-color: #F44336; color: #B71C1C; }
    
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

def get_file_metadata(filename):
    """Checks when the file was last modified in Dropbox"""
    try:
        md = dbx.files_get_metadata(f"/{filename}")
        return md.server_modified
    except:
        return None

def load_data(filename, default):
    try:
        _, res = dbx.files_download(f"/{filename}")
        return json.loads(res.content)
    except:
        return default

def save_data(filename, data):
    json_bytes = json.dumps(data, indent=4).encode('utf-8')
    dbx.files_upload(json_bytes, f"/{filename}", mode=dropbox.files.WriteMode("overwrite"))

def list_dropbox_files():
    try:
        res = dbx.files_list_folder('')
        return [entry.name for entry in res.entries]
    except:
        return []

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
app_mode = st.sidebar.radio("Select Mode:", ["🍽️ Customer Menu", "🔐 Owner Login", "🔄 Device Sync"])

# ==========================================
# MODE 1: CUSTOMER MENU
# ==========================================
if app_mode == "🍽️ Customer Menu":
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'order_step' not in st.session_state: st.session_state.order_step = 'menu'
    if 'customer_meta' not in st.session_state: st.session_state.customer_meta = {}

    if st.session_state.order_step == 'menu':
        with st.expander("ℹ️ How to Order / Cara Memesan"):
            st.markdown("""
            1. **Select Food:** Click 'Add'.
            2. **Check Cart:** See 'Your Basket'.
            3. **Review:** Click 'Review Order'.
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
                    if st.button("Add", key=f"btn_{item_name}", width="stretch"):
                        st.session_state.cart.append({"item": item_name, "qty": qty, "price": item_price * qty})
                        st.toast(f"✅ Added {qty}x {item_name}")
                st.divider()
        with col2:
            st.warning("🛒 **Your Basket**")
            if st.session_state.cart:
                total = sum(i['price'] for i in st.session_state.cart)
                for i in st.session_state.cart:
                    st.text(f"{i['qty']}x {i['item']} (OMR {i['price']:.3f})")
                st.divider()
                st.markdown(f"### Total: OMR {total:.3f}")
                c_name = st.text_input("Name", placeholder="Enter Name")
                t_no = st.selectbox("Type", ["Takeaway", "Dine-in"])
                if st.button("📝 REVIEW ORDER", type="primary", width="stretch"):
                    if not c_name: st.error("Name Required!")
                    else:
                        st.session_state.customer_meta = {"name": c_name, "table": t_no, "total": total}
                        st.session_state.order_step = 'review'
                        st.rerun()
                if st.button("❌ Clear"): st.session_state.cart = []; st.rerun()
            else: st.info("Basket is empty.")

    elif st.session_state.order_step == 'review':
        meta = st.session_state.customer_meta
        st.success(f"**Customer:** {meta['name']} | **Type:** {meta['table']}")
        st.table(pd.DataFrame([{"Qty":i['qty'],"Item":i['item'],"Price":f"{i['price']:.3f}"} for i in st.session_state.cart]))
        st.markdown(f"## Total: OMR {meta['total']:.3f}")
        c1, c2 = st.columns(2)
        with c1: 
            if st.button("⬅️ Back", width="stretch"): st.session_state.order_step = 'menu'; st.rerun()
        with c2:
            if st.button("✅ CONFIRM", type="primary", width="stretch"):
                with st.spinner("Sending..."):
                    fn = get_weekly_filename()
                    orders = load_data(fn, [])
                    summary = ", ".join([f"{x['qty']}x {x['item']}" for x in st.session_state.cart])
                    orders.append({
                        "id": int(time.time()), "date": datetime.now().strftime("%Y-%m-%d"),
                        "time": datetime.now().strftime("%H:%M"), "customer": f"{meta['name']} ({meta['table']})",
                        "items": st.session_state.cart, "item_summary": summary, "total": meta['total'], "status": "New"
                    })
                    save_data(fn, orders)
                    st.session_state.order_step = 'success'; st.rerun()

    elif st.session_state.order_step == 'success':
        st.balloons()
        st.title("✅ Order Received!")
        st.markdown("### Thank you for your order.")
        st.markdown("See you at **Orange Pearl Tea** on **Friday from 1.30pm onwards**!!")
        
        # --- CHANGED HERE ---
        st.info("Sent to Food Processing Team!")
        # --------------------
        
        st.write(""); st.write("")
        if st.button("🏠 New Order", type="primary", width="stretch"):
            st.session_state.cart = []; st.session_state.order_step = 'menu'; st.rerun()

# ==========================================
# MODE 2: OWNER LOGIN
# ==========================================
elif app_mode == "🔐 Owner Login":
    with st.sidebar.form("login_form"):
        pwd = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Login")
    
    correct_pwd = st.secrets["admin"]["password"] if "admin" in st.secrets else "admin123"
    
    if submit_btn and pwd == correct_pwd: st.session_state['authenticated'] = True
    elif submit_btn: st.sidebar.error("Wrong Password")

    if st.session_state.get('authenticated', False):
        st.title("📊 Towkay Dashboard")
        if st.button("🔄 Refresh Data"): st.rerun()
        
        s_date = st.date_input("Week:", value=datetime.now())
        t_file = get_weekly_filename(datetime.combine(s_date, datetime.min.time()))
        st.caption(f"File: `{t_file}`")
        orders = load_data(t_file, [])

        t1, t2, t3 = st.tabs(["🔥 Kitchen", "💰 Sales", "🛠️ Menu"])
        with t1:
            st.subheader("Incoming Orders")
            if orders:
                for o in reversed(orders):
                    with st.expander(f"🕒 {o['time']} - {o['customer']} (OMR {o['total']:.3f})", expanded=True):
                        st.write(f"**Items:** {o.get('item_summary', '')}")
            else: st.info("No orders.")

        with t2:
            if orders:
                rev = sum(o['total'] for o in orders)
                c1, c2 = st.columns(2)
                c1.markdown(f"<div class='metric-card'><h3>💰 Total Revenue</h3><h1>OMR {rev:.3f}</h1></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-card'><h3>🧾 Total Orders</h3><h1>{len(orders)}</h1></div>", unsafe_allow_html=True)
                st.divider()
                
                # Customer Table
                st.subheader("👥 By Customer")
                df_cust = pd.DataFrame([{"Customer": o['customer'], "Time": o['time'], "Items": o['item_summary'], "Total": f"{o['total']:.3f}"} for o in orders])
                st.dataframe(df_cust.sort_values("Customer"), width='stretch', hide_index=True)
                
                # Dish Performance
                st.subheader("🔥 By Dish")
                stats = {}
                for o in orders:
                    for i in o['items']:
                        stats[i['item']] = stats.get(i['item'], {'qty':0,'rev':0})
                        stats[i['item']]['qty'] += i['qty']
                        stats[i['item']]['rev'] += i['price']
                if stats:
                    df_stats = pd.DataFrame([{"Item":k,"Qty":v['qty'],"Rev":f"{v['rev']:.3f}"} for k,v in stats.items()])
                    st.dataframe(df_stats.sort_values("Qty", ascending=False), width='stretch', hide_index=True)
                
                # Exports
                st.divider(); st.subheader("Export")
                export_data = pd.DataFrame([{"Date":o['date'],"Time":o['time'],"Customer":o['customer'],"Items":o['item_summary'],"Total":f"{o['total']:.3f}"} for o in reversed(orders)])
                c1,c2,c3 = st.columns(3)
                with c1: st.download_button("⬇️ JSON", json.dumps(orders, indent=4), t_file, "application/json")
                with c2: st.download_button("📄 HTML", generate_html_report(export_data, s_date.strftime('%Y-%m-%d')), "report.html", "text/html")
                with c3: st.download_button("🖼️ PNG", generate_png_image(export_data), "report.png", "image/png")

        with t3:
            curr = load_data("menu.json", {"Nasi Lemak": 1.500})
            ed = st.data_editor(pd.DataFrame(list(curr.items()), columns=["Item", "Price (OMR)"]), num_rows="dynamic", width='stretch')
            if st.button("💾 Save Menu"):
                save_data("menu.json", dict(zip(ed["Item"], ed["Price (OMR)"])))
                st.success("Updated!")
    else: st.info("Please Login.")

# ==========================================
# MODE 3: DEVICE SYNC (CLOUD & DESKTOP)
# ==========================================
elif app_mode == "🔄 Device Sync":
    st.markdown("## 📱 Sync Center")
    st.markdown("Manage data flow between this device and Dropbox Cloud.")
    
    # 1. Check Connection
    try:
        dbx.users_get_current_account()
        st.markdown('<div class="sync-box sync-online">✅ <b>Status: Online</b><br>Connected to Dropbox</div>', unsafe_allow_html=True)
    except:
        st.markdown('<div class="sync-box sync-offline">❌ <b>Status: Offline</b><br>Check secrets.toml</div>', unsafe_allow_html=True)
        st.stop()

    current_file = get_weekly_filename()
    
    # 2. File Status
    st.subheader(f"📄 Current Active File: `{current_file}`")
    last_mod = get_file_metadata(current_file)
    
    if last_mod:
        st.info(f"☁️ **Cloud Last Updated:** {last_mod}")
    else:
        st.warning("⚠️ File not found in Cloud (New Week?)")

    st.divider()

    col1, col2 = st.columns(2)
    
    # PUSH (Upload Local -> Cloud)
    with col1:
        st.subheader("⬆️ Upload to Cloud")
        st.markdown("Overwrite cloud data with a file from this device.")
        uploaded_file = st.file_uploader("Select JSON File", type=['json'])
        if uploaded_file:
            if st.button("🚀 Push (Overwrite Cloud)", type="primary", width="stretch"):
                try:
                    data = json.load(uploaded_file)
                    save_data(uploaded_file.name, data)
                    st.success(f"Uploaded {uploaded_file.name} to Cloud!")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # PULL (Download Cloud -> Local)
    with col2:
        st.subheader("⬇️ Download from Cloud")
        st.markdown("Save the latest cloud data to this device.")
        
        cloud_data = load_data(current_file, None)
        
        if cloud_data is not None:
            st.success("Data Ready.")
            st.download_button(
                label=f"💾 Save {current_file}",
                data=json.dumps(cloud_data, indent=4),
                file_name=current_file,
                mime="application/json",
                width="stretch"
            )
        else:
            st.error("No data available to download.")
            
    st.divider()
    
    with st.expander("📂 View All Cloud Files"):
        files = list_dropbox_files()
        if files:
            for f in files:
                st.write(f"📄 {f}")
        else:
            st.write("Folder is empty.")