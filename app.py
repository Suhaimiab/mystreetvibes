import streamlit as st
import dropbox
import json
import pandas as pd
from datetime import datetime, timedelta, timezone, time as dt_time
import time
import os
import matplotlib.pyplot as plt
from pandas.plotting import table
from io import BytesIO
from dropbox.exceptions import ApiError
import textwrap
from urllib.parse import quote
import base64

# --- 1. CONFIG & BRANDING ---
st.set_page_config(
    page_title="Malaysian Street Vibes", 
    page_icon="🍜", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

plt.switch_backend('Agg')

# --- TIMEZONE SETUP (OMAN UTC+4) ---
OMAN_TZ = timezone(timedelta(hours=4))

# --- HARDCODED WHATSAPP NUMBER ---
KITCHEN_HOTLINE = "+96879144711"

# --- IMAGE MAPPING ---
MENU_IMAGES = {
    "Nasi Lemak": "images/nasi_lemak.jpg",
    "Mee Goreng": "images/mee_goreng.jpg",
    "Teh Tarik": "images/teh_tarik.jpg",
    "Nasi Ayam Masak Merah": "images/nasi_ayam.jpg"
}

# CSS Styling
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
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
    .stButton>button[kind="primary"] {
        background-color: #5D4037 !important;
        color: white !important;
        border: none !important;
    }
    .stButton>button[kind="secondary"] {
        background-color: #EFEBE9 !important;
        color: #5D4037 !important;
        border: 1px solid #D7CCC8 !important;
    }
    .shop-info { background-color: #E8F5E9; color: #1B5E20; padding: 15px; border-radius: 10px; border: 2px solid #4CAF50; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .shop-closed { background-color: #FFEBEE; color: #B71C1C; padding: 15px; border-radius: 10px; border: 2px solid #F44336; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .welcome-container { text-align: center; margin-bottom: 15px; padding: 10px; background-color: #FAFAFA; border-radius: 10px; border-bottom: 2px solid #5D4037; }
    .welcome-title { color: #5D4037; font-size: 1.3em; font-weight: bold; margin-bottom: 5px; }
    .welcome-text { color: #555; font-size: 0.9em; margin-bottom: 8px; }
    .welcome-time { color: #1565C0; font-weight: bold; margin-bottom: 5px; }
    .welcome-loc { color: #E65100; font-weight: bold; font-size: 0.9em; }
    img.menu-img { border-radius: 10px; object-fit: cover; }
    
    /* Sold Out Badge Styling */
    .sold-out-badge {
        background-color: #ffebee;
        color: #c62828;
        border: 1px solid #c62828;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
        display: inline-block;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER LOGO ---
if os.path.exists("street_vibes.png"):
    try:
        with open("street_vibes.png", "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        st.markdown(f'<div style="display: flex; justify-content: center; margin-bottom: 20px;"><img src="data:image/png;base64,{img_b64}" width="220"></div>', unsafe_allow_html=True)
    except: st.markdown("<h1 style='text-align: center;'>🍜 Malaysian Street Vibes</h1>", unsafe_allow_html=True)
else: st.markdown("<h1 style='text-align: center;'>🍜 Malaysian Street Vibes</h1>", unsafe_allow_html=True)

# --- 2. DROPBOX CONNECTION ---
try:
    dbx = dropbox.Dropbox(
        app_key=st.secrets["dropbox"]["app_key"],
        app_secret=st.secrets["dropbox"]["app_secret"],
        oauth2_refresh_token=st.secrets["dropbox"]["refresh_token"]
    )
except: 
    st.error("System Offline.")
    st.stop()

# --- 3. HELPER FUNCTIONS ---
def load_data(filename, default):
    try:
        _, res = dbx.files_download(f"/{filename}")
        return json.loads(res.content)
    except: return default

def save_data(filename, data):
    json_bytes = json.dumps(data, indent=4).encode('utf-8')
    dbx.files_upload(json_bytes, f"/{filename}", mode=dropbox.files.WriteMode("overwrite"))

def delete_order(filename, order_id):
    data = load_data(filename, [])
    new_data = [d for d in data if d.get('id') != order_id]
    save_data(filename, new_data)

def mark_order_fulfilled(filename, order_id):
    data = load_data(filename, [])
    for d in data:
        if d.get('id') == order_id:
            d['status'] = 'Khalas'
    save_data(filename, data)

def delete_dropbox_file(filename):
    try: dbx.files_delete_v2(f"/{filename}"); return True
    except: return False

# --- CONFIG & TIME MANAGEMENT ---
def get_config():
    defaults = { "active_date": datetime.now(OMAN_TZ).strftime("%Y-%m-%d"), "open_time": "10:00 AM", "close_time": "08:00 PM", "status": "open" }
    return load_data("config.json", defaults)

def save_config(date_obj, start_t, end_t, status_str):
    config = { "active_date": date_obj.strftime("%Y-%m-%d"), "open_time": start_t.strftime("%I:%M %p"), "close_time": end_t.strftime("%I:%M %p"), "status": status_str }
    save_data("config.json", config)

def get_active_week_filename():
    config = get_config()
    date_obj = datetime.strptime(config["active_date"], "%Y-%m-%d")
    return f"orders_{date_obj.strftime('%Y')}_week{date_obj.strftime('%U')}.json"

def format_to_12hr(t_input):
    try:
        if isinstance(t_input, dt_time): return t_input.strftime("%I:%M %p")
        datetime.strptime(str(t_input), "%I:%M %p"); return str(t_input)
    except: return str(t_input)

def is_shop_open():
    # --- STRICT MANUAL CONTROL ---
    return get_config().get("status") == "open"

def get_file_metadata(filename):
    try: return dbx.files_get_metadata(f"/{filename}").server_modified
    except: return None

def list_dropbox_files():
    try: return [entry.name for entry in dbx.files_list_folder('').entries]
    except: return []

# --- WHATSAPP HELPER ---
def generate_whatsapp_link(number, order_data):
    if not number: return None
    clean_num = ''.join(filter(str.isdigit, number))
    items_list = "".join([f"• {item['qty']}x {item['item']}\n" for item in order_data['items']])
    msg = f"*New Order!* 🍜\nCustomer: *{order_data['customer']}*\nTime: {order_data['time']}\n\n*Items:*\n{items_list}*Total: OMR {order_data['total']:.3f}*"
    return f"https://api.whatsapp.com/send?phone={clean_num}&text={quote(msg)}"

# --- EXPORT FUNCTIONS ---
def generate_combined_html(df_cust, df_items, date_str):
    total = df_cust['Total'].str.replace('OMR ', '').astype(float).sum()
    return f"""<html><body><h1 style='color:#5D4037; text-align:center'>🍜 Sales Report: {date_str}</h1><h2>🔥 By Dish</h2>{df_items.to_html(index=False)}<h2>📋 Details</h2>{df_cust.to_html(index=False)}<h3 style='text-align:right'>Total: OMR {total:.3f}</h3></body></html>"""

def generate_png_image(df):
    plot_df = df.copy()
    plot_df['Items'] = plot_df['Items'].apply(lambda x: "\n".join(textwrap.wrap(str(x), 40)))
    h = max(4, len(plot_df) * 0.8 + 2)
    fig, ax = plt.subplots(figsize=(14, h)); ax.axis('off')
    tbl = table(ax, plot_df, loc='center', cellLoc='left')
    tbl.auto_set_font_size(False); tbl.set_fontsize(11); tbl.scale(1.2, 2.0)
    for (row, col), cell in tbl.get_celld().items():
        cell.set_facecolor('#5D4037' if row==0 else '#FFF8E1')
        if row==0: cell.set_text_props(weight='bold', color='white')
    plt.title("Transaction Log", fontsize=16, weight='bold', color='#5D4037'); buf = BytesIO(); plt.savefig(buf, format="png", bbox_inches='tight', dpi=150); plt.close(fig); return buf

# --- 4. NAVIGATION ---
st.sidebar.title("App Mode")
app_mode = st.sidebar.radio("Select Mode:", ["🍽️ Customer Menu", "🔐 Owner Login", "🔄 Device Sync"])

# ==========================================
# MODE 1: CUSTOMER MENU
# ==========================================
if app_mode == "🍽️ Customer Menu":
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'order_step' not in st.session_state: st.session_state.order_step = 'menu'
    if 'customer_meta' not in st.session_state: st.session_state.customer_meta = {}
    if 'last_order' not in st.session_state: st.session_state.last_order = None
    
    shop_open = is_shop_open()
    config = get_config()
    
    try: nice_date = datetime.strptime(config['active_date'], "%Y-%m-%d").strftime("%A, %d %b %Y")
    except: nice_date = config['active_date']
    
    disp_open = format_to_12hr(config.get('open_time', '10:00 AM'))
    disp_close = format_to_12hr(config.get('close_time', '08:00 PM'))

    st.markdown(f"""
    <div class="welcome-container">
        <div class="welcome-title">Welcome to Malaysian Street Vibes</div>
        <div class="welcome-text">We are serving you popular and mouth-watering Malaysian delicacies in the City of Muscat, Oman.<br>Enjoy Malaysian hospitality at its very best.</div>
        <div class="welcome-time">See you all on {nice_date}<br>from {disp_open} to {disp_close}</div>
        <div class="welcome-loc">📍 Location: Orange Pearl Tea, Azaiba</div>
    </div>
    """, unsafe_allow_html=True)

    if shop_open:
        st.markdown(f'<div class="shop-info">✅ <b>WE ARE OPEN!</b><br>Taking orders for: {nice_date}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="shop-closed">⛔ <b>WE ARE CURRENTLY CLOSED</b><br>Please check back later.</div>', unsafe_allow_html=True)

    if st.session_state.order_step == 'menu':
        with st.expander("ℹ️ How to Order / Cara Memesan"):
            st.markdown("1. **Select Food**\n2. **Check Cart**\n3. **Review**\n4. **Submit**")
        
        menu = load_data("menu.json", {"Nasi Lemak": 1.500})
        sold_out_items = load_data("sold_out.json", []) # Load sold out list
        
        col1, col2 = st.columns([1.5, 1])
        with col1:
            st.info("🍛 **Menu**")
            for item_name, item_price in menu.items():
                
                try: item_price = float(item_price)
                except: item_price = 0.0
                
                is_sold_out = item_name in sold_out_items # Check availability
                
                c_img, c_det, c_inp, c_btn = st.columns([1.2, 2, 1, 1])
                
                with c_img:
                    img_path = MENU_IMAGES.get(item_name)
                    if img_path and os.path.exists(img_path): st.image(img_path, use_container_width=True)
                    else: st.write("🍲")
                
                with c_det:
                    st.write(f"**{item_name}**")
                    st.caption(f"OMR {item_price:.3f}")
                
                with c_inp:
                    if not is_sold_out:
                        qty = st.number_input("Qty", min_value=1, value=1, key=f"qty_{item_name}", label_visibility="collapsed")
                    else:
                        st.write("") # Spacer
                
                with c_btn:
                    if is_sold_out:
                        st.markdown('<div class="sold-out-badge">SOLD OUT</div>', unsafe_allow_html=True)
                    else:
                        if st.button("Add", key=f"btn_{item_name}", disabled=not shop_open):
                            st.session_state.cart.append({"item": item_name, "qty": qty, "price": item_price * qty})
                            st.toast(f"✅ Added {qty}x {item_name}")
                st.write("---")
                
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
                if st.button("📝 REVIEW ORDER", type="primary", width="stretch", disabled=not shop_open):
                    if not c_name: st.error("Name Required!")
                    else:
                        st.session_state.customer_meta = {"name": c_name, "table": t_no, "total": total}
                        st.session_state.order_step = 'review'; st.rerun()
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
            if st.button("✅ CONFIRM", type="primary", width="stretch", disabled=not shop_open):
                with st.spinner("Sending..."):
                    fn = get_active_week_filename()
                    orders = load_data(fn, [])
                    summary = ", ".join([f"{x['qty']}x {x['item']}" for x in st.session_state.cart])
                    now_oman = datetime.now(OMAN_TZ)
                    new_order = {
                        "id": int(time.time()), 
                        "date": now_oman.strftime("%Y-%m-%d"),
                        "time": now_oman.strftime("%I:%M %p"), 
                        "customer": f"{meta['name']} ({meta['table']})",
                        "items": st.session_state.cart, 
                        "item_summary": summary, 
                        "total": meta['total'], 
                        "status": "New"
                    }
                    orders.append(new_order); save_data(fn, orders)
                    st.session_state.last_order = new_order
                    st.session_state.order_step = 'success'; st.rerun()

    elif st.session_state.order_step == 'success':
        st.balloons()
        st.title("✅ Order Received!")
        st.markdown("### Thank you for your order.")
        try: nice_date = datetime.strptime(config['active_date'], "%Y-%m-%d").strftime("%A, %d %b %Y")
        except: nice_date = config['active_date']
        st.markdown(f"We look forward to serving you at **Orange Pearl Tea** on **{nice_date}**!")
        st.info("Sent to Food Processing Team!")
        if st.session_state.last_order:
            wa_link = generate_whatsapp_link(KITCHEN_HOTLINE, st.session_state.last_order)
            if wa_link: st.write("---"); st.link_button("📲 Send Order to Kitchen Hotline", wa_link, type="primary", width="stretch")
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
        
        with st.expander("⚙️ Admin Settings (Status & Info)", expanded=True):
            st.info("Manually Open or Close the Shop. Set times for display only.")
            curr_config = get_config()
            curr_date = datetime.strptime(curr_config["active_date"], "%Y-%m-%d")
            
            def parse_time_config(t_str):
                try: return datetime.strptime(t_str, "%I:%M %p").time()
                except: return datetime.now().time()

            curr_open = parse_time_config(curr_config.get("open_time", "10:00 AM"))
            curr_close = parse_time_config(curr_config.get("close_time", "08:00 PM"))
            
            c1, c2 = st.columns(2)
            with c1: 
                st.write("#### Current Shop Status:")
                new_status = st.radio("Status:", ["open", "closed"], index=0 if curr_config.get("status")=="open" else 1, format_func=lambda x: "🟢 OPEN SHOP" if x=="open" else "🔴 CLOSE SHOP", horizontal=True)
            with c2: new_date = st.date_input("Active Date", value=curr_date)
            
            st.divider(); st.write("**Display Time (For Customer Info Only):**")
            t_col1, t_col2 = st.columns(2)
            with t_col1: new_open = st.time_input("Open Time", value=curr_open)
            with t_col2: new_close = st.time_input("Close Time", value=curr_close)

            if st.button("💾 Save Settings", type="primary", width="stretch"):
                save_config(new_date, new_open, new_close, new_status)
                st.success(f"Updated! Shop is now {new_status.upper()}")
                time.sleep(1); st.rerun()
            
            st.caption(f"📂 File: `orders_{new_date.strftime('%Y')}_week{new_date.strftime('%U')}.json` | Status: {'🟢 OPEN' if new_status == 'open' else '🔴 CLOSED'}")

        if st.button("🔄 Refresh Data"): st.rerun()
        s_date = st.date_input("View Reports For:", value=datetime.strptime(curr_config["active_date"], "%Y-%m-%d"))
        t_file_view = f"orders_{s_date.strftime('%Y')}_week{s_date.strftime('%U')}.json"
        orders = load_data(t_file_view, [])

        t1, t2, t3, t4 = st.tabs(["🔥 Kitchen Live", "💰 Sales", "🛠️ Menu", "📖 Panduan"])
        
        with t1:
            st.subheader("Incoming Orders")
            if orders:
                for o in reversed(orders):
                    # KHALAS LOGIC
                    is_khalas = o.get('status') == 'Khalas'
                    status_icon = "✅" if is_khalas else "🔥"
                    status_label = "(Fulfilled)" if is_khalas else ""
                    
                    with st.expander(f"{status_icon} {o['time']} - {o['customer']} {status_label}", expanded=not is_khalas):
                        st.write(f"**Items:** {o.get('item_summary', '')}")
                        
                        if is_khalas:
                            st.success("✅ Order Fulfilled (Khalas)")
                        else:
                            c_khalas, c_del = st.columns([2, 1])
                            with c_khalas:
                                if st.button("✅ Khalas", key=f"khalas_{o['id']}", type="primary", use_container_width=True):
                                    mark_order_fulfilled(t_file_view, o['id'])
                                    st.toast("Order Marked Khalas!")
                                    time.sleep(0.5); st.rerun()
                            with c_del:
                                if st.button("🗑️ Del", key=f"del_{o['id']}", type="secondary", use_container_width=True):
                                    delete_order(t_file_view, o['id']); st.error("Deleted!"); time.sleep(0.5); st.rerun()
            else: st.info("No orders found.")

        with t2:
            if orders:
                rev = sum(o['total'] for o in orders)
                c1, c2 = st.columns(2)
                c1.markdown(f"<div class='metric-card'><h3>💰 Total Revenue</h3><h1>OMR {rev:.3f}</h1></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-card'><h3>🧾 Total Orders</h3><h1>{len(orders)}</h1></div>", unsafe_allow_html=True)
                st.divider(); st.subheader("👥 By Customer")
                df_cust = pd.DataFrame([{"Customer": o['customer'], "Time": o['time'], "Items": o['item_summary'], "Total": f"{o['total']:.3f}"} for o in orders])
                st.dataframe(df_cust, width="stretch", hide_index=True)
                st.subheader("🔥 By Dish")
                stats = {}
                for o in orders:
                    for i in o['items']:
                        stats[i['item']] = stats.get(i['item'], {'qty':0,'rev':0})
                        stats[i['item']]['qty'] += i['qty']
                        stats[i['item']]['rev'] += i['price']
                if stats:
                    df_stats = pd.DataFrame([{"Item":k,"Qty":v['qty'],"Rev":f"{v['rev']:.3f}"} for k,v in stats.items()]).sort_values("Qty", ascending=False)
                    st.dataframe(df_stats, width="stretch", hide_index=True)
                else: df_stats = pd.DataFrame()
                st.divider(); st.subheader("Export")
                c1,c2,c3 = st.columns(3)
                with c1: st.download_button("⬇️ JSON", json.dumps(orders, indent=4), t_file_view, "application/json")
                with c2: st.download_button("📄 HTML", generate_combined_html(df_cust, df_stats, s_date.strftime('%Y-%m-%d')), "report.html", "text/html")
                with c3: st.download_button("🖼️ PNG", generate_png_image(df_cust), "report.png", "image/png")

        with t3:
            curr = load_data("menu.json", {"Nasi Lemak": 1.500})
            st.write("### ✏️ Edit / Add Items")
            df_menu = pd.DataFrame(list(curr.items()), columns=["Item", "Price (OMR)"])
            ed = st.data_editor(df_menu, num_rows="dynamic", width="stretch", key="menu_editor")
            if st.button("💾 Save Changes", type="primary", width="stretch"):
                try:
                    new_menu = {k: float(v) for k, v in dict(zip(ed["Item"], ed["Price (OMR)"])).items()}
                    save_data("menu.json", new_menu); st.success("Menu Updated!"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error saving: {e}")

            st.divider()
            
            # --- SOLD OUT MANAGEMENT ---
            st.write("### 🚫 Manage Sold Out Items")
            st.caption("Select items that are finished. Customers won't be able to order them.")
            sold_out_list = load_data("sold_out.json", [])
            updated_sold_out = st.multiselect("Select Sold Out Items:", list(curr.keys()), default=[i for i in sold_out_list if i in curr])
            
            if st.button("💾 Update Availability", type="primary"):
                save_data("sold_out.json", updated_sold_out)
                st.success("Availability Updated!")
                time.sleep(1); st.rerun()

            st.divider(); st.write("### ❌ Delete Items")
            to_delete = st.multiselect("Select items to remove from Menu:", list(curr.keys()))
            if to_delete and st.button(f"🗑️ Delete {len(to_delete)} Item(s)", type="secondary", width="stretch"):
                for item in to_delete: del curr[item]
                save_data("menu.json", curr); st.error(f"Deleted: {', '.join(to_delete)}"); time.sleep(1); st.rerun()
        
        with t4:
            st.markdown("### 📋 Panduan Pengguna Admin - Malaysian Street Vibes\n1. **Login:** Pilih 'Owner Login' dan masukkan password.\n2. **Status Kedai:** Gunakan butang 'OPEN' atau 'CLOSE' di bahagian atas untuk kawal kedai.\n3. **Khalas Button:** Di tab 'Kitchen Live', tekan butang hijau bila order dah siap.\n4. **Sold Out:** Di tab 'Menu', pilih item yang dah habis dalam kotak 'Manage Sold Out Items'.")

    else: st.info("Please Login.")

# ==========================================
# MODE 3: DEVICE SYNC
# ==========================================
elif app_mode == "🔄 Device Sync":
    if not st.session_state.get('authenticated', False):
        st.markdown("## 🔐 Security Check")
        st.info("Please enter the admin password to access Device Sync.")
        with st.form("sync_login_form"):
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Access"):
                if pwd == (st.secrets["admin"]["password"] if "admin" in st.secrets else "admin123"): st.session_state['authenticated'] = True; st.rerun()
                else: st.error("Wrong Password")
            
    if st.session_state.get('authenticated', False):
        st.markdown("## 📱 Sync Center"); st.info("Manage data flow between this device and Dropbox Cloud.")
        c1, c2 = st.columns(2)
        with c1:
            uploaded_file = st.file_uploader("Select JSON File", type=['json'])
            if uploaded_file and st.button("🚀 Push (Overwrite Cloud)", type="primary"):
                try: save_data(uploaded_file.name, json.load(uploaded_file)); st.success("Uploaded!"); time.sleep(1.5); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
        with c2:
            current_file = get_active_week_filename()
            if st.button(f"⬇️ Download {current_file}", type="secondary"):
                data = load_data(current_file, None)
                if data: st.download_button(f"💾 Save {current_file}", json.dumps(data, indent=4), current_file, "application/json")
                else: st.error("No data.")
