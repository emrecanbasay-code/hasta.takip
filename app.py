import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pandas as pd

# ==========================================
# 1. AYARLAR VE MOBİL STİL
# ==========================================
st.set_page_config(
    page_title="Pro Hasta Takip v14 - Mobil", 
    layout="centered", 
    page_icon="🏥",
    initial_sidebar_state="collapsed"
)

# MOBİL OPTİMİZE CSS
st.markdown("""
<style>
    /* Genel */
    .stApp { max-width: 100%; }
    .stMarkdown { margin-bottom: -5px; }
    
    /* Büyük Dokunmatik Checkbox */
    div[data-testid="stCheckbox"] {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 12px 15px;
        margin: 3px 0;
        border: 2px solid #e0e0e0;
        min-height: 50px;
    }
    div[data-testid="stCheckbox"]:hover {
        border-color: #0044cc;
        background: #f0f4ff;
    }
    div[data-testid="stCheckbox"] label {
        font-size: 16px !important;
        font-weight: 500;
    }
    
    /* Büyük Butonlar */
    .stButton>button {
        border-radius: 12px;
        font-weight: bold;
        font-size: 16px;
        padding: 15px 20px;
        min-height: 55px;
    }
    
    /* Expander Başlıkları */
    .streamlit-expanderHeader {
        font-size: 18px !important;
        font-weight: bold;
        background: #f0f4ff;
        border-radius: 10px;
        padding: 15px;
    }
    
    /* Input Alanları */
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        font-size: 16px !important;
        padding: 12px !important;
        border-radius: 8px;
    }
    
    /* Etiketler */
    .etiket {
        font-weight: bold;
        font-size: 15px;
        color: #333;
        margin-bottom: 5px;
    }
    
    /* Hızlı Buton Stili */
    .hizli-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px;
        font-size: 14px;
        font-weight: bold;
    }
    
    /* Selectbox */
    div[data-baseweb="select"] > div {
        font-size: 16px !important;
        min-height: 50px;
    }
    
    /* Info Box */
    div[data-testid="stInfo"] {
        background: #e8f4fd;
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LİSTE TANIMLARI
# ==========================================

# --- A. CHECKBOX OLACAKLAR (EVET/HAYIR) ---
CHECKBOX_LIST = [
    "1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü", "Servis",
    "HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER",
    "Entübasyon", "İnotrop", 
    "Mükerrer tetkik Ya da tedavi istemi", 
    "Kesin tanı koyulamaması", "8 saati aşıp yatmaması", "Birden fazla kliniği ilgilendirmesi",
    "KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı",  
    "Cr", "Ct", "Mr", "Usg",
    "Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb", "Plastik", "Göz", 
    "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji", "Göğüs H.", "Enfeksiyon H.", 
    "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji",
    "08.00-16.00", "16.00-24.00", "00.00-08.00",
    "DEVİR", "Taburcu", "Ölüm", "T. RED"
]

# --- B. OTOMATİK "0" GELECEK OLANLAR ---
SIFIR_LIST = [
    "Sıra Numarası", 
    "1Servis", 
    "Ybü", 
    "Toplam", 
    "Yapılan Kolsültasyon sayısı", 
    "1Dahilye", "1Göğüs Hast", "1Genel Cerrahi", "1Nrş", "1KVC", 
    "1Kbb", "1Plastik", "1Göz", "1Üroloji", "1Göğüs C.", 
    "1Kardiyoloji", "1Nöroloji", "1Orto", "1Enfeksiyon H.", 
    "1Psikiyatri", "1Cildiye", "1Anestezi", "1Radyoloji"
]

# --- C. SABİT DEĞERLER ---
SABIT_DEGERLER = {
    "ateş": 36.5,
    "sistolik tansiyon": 120,
    "diyastolik tansiyon": 80,
    "nabız": 80,
    "spo2": 98,
    "gks": 15
}

# --- D. GRUPLAR ---
KRONIK_HASTALIKLAR = ["HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER"]
YATIS_TURLERI = ["1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü", "Servis"]
TETKIKLER = ["KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı", "Cr", "Ct", "Mr", "Usg"]
KLINIK_DURUM = ["Entübasyon", "İnotrop", "Mükerrer tetkik Ya da tedavi istemi", 
                "Kesin tanı koyulamaması", "8 saati aşıp yatmaması", "Birden fazla kliniği ilgilendirmesi"]

# Konsültasyon Grupları
KONSULTASYON_DAHILI = ["Dahilye", "Kardiyoloji", "Nöroloji", "Enfeksiyon H.", "Göğüs Hast", "Göğüs H."]
KONSULTASYON_CERRAHI = ["Genel Cerrahi", "KVC", "Göğüs C.", "Üroloji", "Kbb", "Plastik", "Göz"]
KONSULTASYON_DIGER = ["Nrş", "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji"]

VARDIYALAR = ["08.00-16.00", "16.00-24.00", "00.00-08.00"]
SONUCLAR = ["DEVİR", "Taburcu", "Ölüm", "T. RED"]

# ==========================================
# 3. BAĞLANTI
# ==========================================
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds)

def verileri_hazirla():
    client = get_connection()
    sh = client.open("Hasta_Takip_Sistemi")
    w_veri = sh.worksheet("Veri")
    w_liste = sh.worksheet("Liste")
    w_atlanan = sh.worksheet("Atlananlar")
    
    raw_headers = w_veri.get_all_values()
    row1 = raw_headers[0]
    row2 = raw_headers[1]
    
    headers = []
    max_len = max(len(row1), len(row2))
    
    for i in range(max_len):
        v1 = row1[i].strip() if i < len(row1) else ""
        v2 = row2[i].strip() if i < len(row2) else ""
        final_header = v2 if v2 else v1
        headers.append(final_header.replace("\n", " ").strip())
        
    return w_veri, w_atlanan, headers, w_liste.get_all_values()

try:
    w_veri, w_atlanan, headers, liste_rows = verileri_hazirla()
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}"); st.stop()

# ==========================================
# 4. OTOMATİK VARDİYA FONKSİYONU
# ==========================================
def get_otomatik_vardiya():
    """Saate göre otomatik vardiya belirle"""
    saat = datetime.now().hour
    if 8 <= saat < 16:
        return "08.00-16.00"
    elif 16 <= saat < 24:
        return "16.00-24.00"
    else:
        return "00.00-08.00"

# ==========================================
# 5. SIDEBAR: GERİ AL (KÜÇÜK)
# ==========================================
with st.sidebar:
    st.header("⚙️ İşlemler")
    if st.button("⏪ SON KAYDI SİL", type="primary", use_container_width=True):
        mevcut = w_veri.get_all_values()
        if len(mevcut) > 2:
            w_veri.delete_rows(len(mevcut))
            st.success("✅ Silindi.")
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Veri yok.")
    st.markdown("---")
    st.caption("v14 - Mobil Uyumlu")

# ==========================================
# 6. HASTA SEÇİMİ
# ==========================================
st.title("🏥 Hasta Takip - Mobil")

# Liste hazırla
yapilacaklar = []
for row in liste_rows[3:]:
    if len(row) > 10:
        p_isim = str(row[4]).strip()
        if p_isim and "isim" not in p_isim.lower():
            yapilacaklar.append({
                "isim": p_isim,
                "tarih": str(row[6]).strip(),
                "saat": str(row[8]).strip() if len(row) > 8 else "-",
                "karar": str(row[10]).strip(),
                "transfer": str(row[11]).strip()
            })

if not yapilacaklar:
    st.success("🎉 Liste Bitti!")
    st.stop()

# Hasta seçimi
st.info(f"📋 Kalan Hasta: **{len(yapilacaklar)}**")
secenekler = [f"{x['isim']} | {x['tarih']}" for x in yapilacaklar]
secilen_str = st.selectbox("👇 Sıradaki Hasta:", secenekler, label_visibility="visible")
secilen_ad = secilen_str.split(" | ")[0]
secilen_veri = next((x for x in yapilacaklar if x['isim'] == secilen_ad), None)

# Yatış saati ve buton
col_saat, col_btn = st.columns([2, 1])
col_saat.warning(f"⏰ **Yatış Saati:** {secilen_veri['saat']}")

if col_btn.button("⬇️ BİLGİLERİ GETİR", type="primary", use_container_width=True):
    t_obj = datetime.now()
    try:
        d_str = secilen_veri['tarih'].split(" ")[0]
        t_obj = datetime.strptime(d_str, "%Y-%m-%d")
    except:
        try: t_obj = datetime.strptime(d_str, "%d.%m.%Y")
        except: pass

    for idx, h in enumerate(headers):
        h_cl = h.lower().replace("İ", "i").replace("I", "ı")
        key_id = f"input_{idx}"
        
        if "isim" in h_cl or "adı soyadı" in h_cl:
            st.session_state[key_id] = secilen_veri['isim']
        elif "tarih" in h_cl:
            st.session_state[key_id] = t_obj
        elif "karar" in h_cl and "süre" in h_cl:
            st.session_state[key_id] = secilen_veri['karar']
        elif ("transfer" in h_cl or "transver" in h_cl) and "süre" in h_cl:
            st.session_state[key_id] = secilen_veri['transfer']
    
    # Otomatik vardiya seç
    oto_vardiya = get_otomatik_vardiya()
    for idx, h in enumerate(headers):
        if h in VARDIYALAR:
            st.session_state[f"input_{idx}"] = (h == oto_vardiya)
    
    st.toast(f"✅ Bilgiler çekildi! Vardiya: {oto_vardiya}", icon="✅")

st.markdown("---")

# ==========================================
# 7. HIZLI BUTONLAR
# ==========================================
st.markdown("### ⚡ Hızlı İşlemler")
col_h1, col_h2, col_h3 = st.columns(3)

with col_h1:
    if st.button("🌡️ Normal Vital", use_container_width=True):
        for idx, h in enumerate(headers):
            h_lower = h.lower().replace("İ", "i").replace("I", "ı")
            if h_lower in SABIT_DEGERLER:
                st.session_state[f"input_{idx}"] = SABIT_DEGERLER[h_lower]
        st.toast("✅ Vital değerler ayarlandı!", icon="🌡️")

with col_h2:
    if st.button("🕐 Otomatik Vardiya", use_container_width=True):
        oto_vardiya = get_otomatik_vardiya()
        for idx, h in enumerate(headers):
            if h in VARDIYALAR:
                st.session_state[f"input_{idx}"] = (h == oto_vardiya)
        st.toast(f"✅ Vardiya: {oto_vardiya}", icon="🕐")

with col_h3:
    if st.button("🔄 Temizle", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("input_"):
                del st.session_state[key]
        st.toast("✅ Form temizlendi!", icon="🔄")

st.markdown("---")

# ==========================================
# 8. FORM - EXPANDER GRUPLAR
# ==========================================
input_values = {}

# Expander'lar için takip
expander_states = {}

# ===============================
# EXPANDER 1: HASTA BİLGİLERİ (Açık)
# ===============================
with st.expander("📋 HASTA BİLGİLERİ", expanded=True):
    for i, baslik in enumerate(headers):
        if not baslik.strip(): continue
        
        key_id = f"input_{i}"
        b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
        
        # Sadece hasta bilgileri alanları
        if any(x in b_lower for x in ['isim', 'adı soyadı', 'tarih', 'yaş', 'cinsiyet']):
            
            # State başlatma
            if key_id not in st.session_state:
                if "tarih" in b_lower: 
                    st.session_state[key_id] = datetime.now()
                else: 
                    st.session_state[key_id] = ""
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown(f"<div class='etiket'>{baslik}</div>", unsafe_allow_html=True)
            
            with col2:
                if "isim" in b_lower or "adı soyadı" in b_lower:
                    input_values[baslik] = st.text_input("İsim", key=key_id, label_visibility="collapsed")
                elif "tarih" in b_lower:
                    val_t = st.session_state[key_id] if st.session_state[key_id] else datetime.now()
                    input_values[baslik] = st.date_input("Tarih", value=val_t, key=key_id, format="DD.MM.YYYY", label_visibility="collapsed")
                elif "cinsiyet" in b_lower:
                    input_values[baslik] = st.selectbox("Cinsiyet", ["", "E", "K"], key=key_id, label_visibility="collapsed")
                elif "yaş" in b_lower:
                    try: m_val = int(st.session_state[key_id]) if st.session_state[key_id] else 0
                    except: m_val = 0
                    input_values[baslik] = st.number_input("Yaş", value=m_val, step=1, format="%d", key=key_id, label_visibility="collapsed")

# ===============================
# EXPANDER 2: VİTAL BULGULAR (Açık)
# ===============================
with st.expander("💉 VİTAL BULGULAR", expanded=True):
    # 3 sütunlu grid
    vitals_found = []
    for i, baslik in enumerate(headers):
        b_lower = baslik.lower().replace("İ", "i").replace("I", "ı")
        if b_lower in SABIT_DEGERLER or any(x in b_lower for x in ['ateş', 'tansiyon', 'nabız', 'spo2', 'gks']):
            if baslik not in vitals_found:
                vitals_found.append((i, baslik, b_lower))
    
    # 3'erli göster
    for j in range(0, len(vitals_found), 2):
        cols = st.columns(2)
        for k, col in enumerate(cols):
            if j + k < len(vitals_found):
                i, baslik, b_lower = vitals_found[j + k]
                key_id = f"input_{i}"
                
                if key_id not in st.session_state:
                    if b_lower in SABIT_DEGERLER:
                        st.session_state[key_id] = SABIT_DEGERLER[b_lower]
                    else:
                        st.session_state[key_id] = 0
                
                with col:
                    st.markdown(f"<div class='etiket'>{baslik}</div>", unsafe_allow_html=True)
                    try: val = float(st.session_state[key_id]) if st.session_state[key_id] else 0.0
                    except: val = 0.0
                    
                    if "ateş" in b_lower:
                        input_values[baslik] = st.number_input("Değer", value=val, step=0.1, format="%.1f", key=key_id, label_visibility="collapsed")
                    else:
                        input_values[baslik] = st.number_input("Değer", value=int(val), step=1, format="%d", key=key_id, label_visibility="collapsed")

# ===============================
# EXPANDER 3: YATIŞ & KRONİK
# ===============================
with st.expander("🏥 YATIŞ & KRONİK HASTALIKLAR", expanded=False):
    
    # Yatış Türleri
    st.markdown("**📍 Yatış Türü:**")
    yatis_cols = st.columns(2)
    for idx, baslik in enumerate(headers):
        if baslik in YATIS_TURLERI:
            col_idx = YATIS_TURLERI.index(baslik) % 2
            key_id = f"input_{idx}"
            
            if key_id not in st.session_state:
                st.session_state[key_id] = False
            
            with yatis_cols[col_idx]:
                val = st.checkbox(baslik, key=key_id)
                input_values[baslik] = 1 if val else 0
    
    st.markdown("---")
    
    # Kronik Hastalıklar
    st.markdown("**💊 Kronik Hastalıklar:**")
    kronik_cols = st.columns(2)
    for idx, baslik in enumerate(headers):
        if baslik in KRONIK_HASTALIKLAR:
            col_idx = KRONIK_HASTALIKLAR.index(baslik) % 2
            key_id = f"input_{idx}"
            
            if key_id not in st.session_state:
                st.session_state[key_id] = False
            
            with kronik_cols[col_idx]:
                val = st.checkbox(baslik, key=key_id)
                input_values[baslik] = 1 if val else 0
    
    st.markdown("---")
    
    # Klinik Durum
    st.markdown("**⚠️ Klinik Durum:**")
    durum_cols = st.columns(2)
    for idx, baslik in enumerate(headers):
        if baslik in KLINIK_DURUM:
            col_idx = KLINIK_DURUM.index(baslik) % 2
            key_id = f"input_{idx}"
            
            if key_id not in st.session_state:
                st.session_state[key_id] = False
            
            with durum_cols[col_idx]:
                val = st.checkbox(baslik, key=key_id)
                input_values[baslik] = 1 if val else 0

# ===============================
# EXPANDER 4: TETKİKLER
# ===============================
with st.expander("🔬 TETKİKLER", expanded=False):
    tetkik_cols = st.columns(2)
    for idx, baslik in enumerate(headers):
        if baslik in TETKIKLER:
            col_idx = TETKIKLER.index(baslik) % 2
            key_id = f"input_{idx}"
            
            if key_id not in st.session_state:
                st.session_state[key_id] = False
            
            with tetkik_cols[col_idx]:
                val = st.checkbox(baslik, key=key_id)
                input_values[baslik] = 1 if val else 0

# ===============================
# EXPANDER 5: KONSÜLTASYONLAR
# ===============================
with st.expander("📞 KONSÜLTASYONLAR", expanded=False):
    
    # Dahili Branşlar
    st.markdown("**🩺 Dahili Branşlar:**")
    dahili_cols = st.columns(2)
    for idx, baslik in enumerate(headers):
        if baslik in KONSULTASYON_DAHILI:
            col_idx = KONSULTASYON_DAHILI.index(baslik) % 2
            key_id = f"input_{idx}"
            
            if key_id not in st.session_state:
                st.session_state[key_id] = False
            
            with dahili_cols[col_idx]:
                val = st.checkbox(baslik, key=key_id)
                input_values[baslik] = 1 if val else 0
    
    st.markdown("---")
    
    # Cerrahi Branşlar
    st.markdown("**🔪 Cerrahi Branşlar:**")
    cerrahi_cols = st.columns(2)
    for idx, baslik in enumerate(headers):
        if baslik in KONSULTASYON_CERRAHI:
            col_idx = KONSULTASYON_CERRAHI.index(baslik) % 2
            key_id = f"input_{idx}"
            
            if key_id not in st.session_state:
                st.session_state[key_id] = False
            
            with cerrahi_cols[col_idx]:
                val = st.checkbox(baslik, key=key_id)
                input_values[baslik] = 1 if val else 0
    
    st.markdown("---")
    
    # Diğer Branşlar
    st.markdown("**📋 Diğer Branşlar:**")
    diger_cols = st.columns(2)
    for idx, baslik in enumerate(headers):
        if baslik in KONSULTASYON_DIGER:
            col_idx = KONSULTASYON_DIGER.index(baslik) % 2
            key_id = f"input_{idx}"
            
            if key_id not in st.session_state:
                st.session_state[key_id] = False
            
            with diger_cols[col_idx]:
                val = st.checkbox(baslik, key=key_id)
                input_values[baslik] = 1 if val else 0

# ===============================
# EXPANDER 6: SONUÇ & VARDİYA
# ===============================
with st.expander("📊 SONUÇ & VARDİYA", expanded=False):
    
    # Vardiya
    st.markdown("**🕐 Vardiya:**")
    vard_cols = st.columns(3)
    for idx, baslik in enumerate(headers):
        if baslik in VARDIYALAR:
            col_idx = VARDIYALAR.index(baslik) % 3
            key_id = f"input_{idx}"
            
            # Otomatik vardiya başlangıç
            if key_id not in st.session_state:
                oto = get_otomatik_vardiya()
                st.session_state[key_id] = (baslik == oto)
            
            with vard_cols[col_idx]:
                val = st.checkbox(baslik, key=key_id)
                input_values[baslik] = 1 if val else 0
    
    st.markdown("---")
    
    # Sonuç
    st.markdown("**📋 Sonuç:**")
    sonuc_cols = st.columns(2)
    for idx, baslik in enumerate(headers):
        if baslik in SONUCLAR:
            col_idx = SONUCLAR.index(baslik) % 2
            key_id = f"input_{idx}"
            
            if key_id not in st.session_state:
                st.session_state[key_id] = False
            
            with sonuc_cols[col_idx]:
                val = st.checkbox(baslik, key=key_id)
                input_values[baslik] = 1 if val else 0
    
    st.markdown("---")
    
    # Süreler
    st.markdown("**⏱️ Süreler:**")
    for i, baslik in enumerate(headers):
        b_lower = baslik.lower().replace("İ", "i").replace("I", "ı")
        
        if "süre" in b_lower and ("karar" in b_lower or "transfer" in b_lower or "transver" in b_lower):
            key_id = f"input_{i}"
            
            if key_id not in st.session_state:
                st.session_state[key_id] = ""
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown(f"<div class='etiket'>{baslik}</div>", unsafe_allow_html=True)
            with col2:
                input_values[baslik] = st.text_input("Süre", key=key_id, label_visibility="collapsed")

# ===============================
# DİĞER ALANLAR (Sıfır listesi ve kalanlar)
# ===============================
with st.expander("📝 DİĞER BİLGİLER", expanded=False):
    for i, baslik in enumerate(headers):
        if not baslik.strip(): continue
        if baslik in input_values: continue  # Zaten işlendi
        
        key_id = f"input_{i}"
        b_lower = baslik.lower().replace("İ", "i").replace("I", "ı")
        
        # State başlatma
        if key_id not in st.session_state:
            if baslik in SIFIR_LIST:
                st.session_state[key_id] = 0
            elif baslik in CHECKBOX_LIST:
                st.session_state[key_id] = False
            else:
                st.session_state[key_id] = ""
        
        # Sadece SIFIR listesi veya açıklama/not alanları
        if baslik in SIFIR_LIST:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown(f"<div class='etiket'>{baslik}</div>", unsafe_allow_html=True)
            with col2:
                try: val = int(st.session_state[key_id]) if st.session_state[key_id] else 0
                except: val = 0
                input_values[baslik] = st.number_input("Sayı", value=val, step=1, format="%d", key=key_id, label_visibility="collapsed")
        
        elif any(x in b_lower for x in ['açıklama', 'not']):
            st.markdown(f"<div class='etiket'>{baslik}</div>", unsafe_allow_html=True)
            input_values[baslik] = st.text_area("Not", key=key_id, height=70, label_visibility="collapsed")
        
        elif baslik in CHECKBOX_LIST and baslik not in YATIS_TURLERI and baslik not in KRONIK_HASTALIKLAR and baslik not in TETKIKLER and baslik not in KLINIK_DURUM and baslik not in VARDIYALAR and baslik not in SONUCLAR and baslik not in KONSULTASYON_DAHILI and baslik not in KONSULTASYON_CERRAHI and baslik not in KONSULTASYON_DIGER:
            # Kalan checkbox'lar
            val = st.checkbox(baslik, key=key_id)
            input_values[baslik] = 1 if val else 0

st.markdown("---")

# ==========================================
# 9. KAYDET VE PAS GEÇ BUTONLARI
# ==========================================
col_kaydet, col_pas = st.columns([2, 1])

with col_kaydet:
    kaydet_btn = st.button("✅ KAYDET", type="primary", use_container_width=True)

with col_pas:
    pas_gec_btn = st.button("🚫 PAS GEÇ", use_container_width=True)

# ==========================================
# 10. KAYIT İŞLEMLERİ
# ==========================================
if kaydet_btn:
    try:
        yeni_satir = []
        for baslik in headers:
            if not baslik.strip():
                yeni_satir.append("")
            else:
                val = input_values.get(baslik, "")
                if hasattr(val, 'strftime'):
                    val = val.strftime("%d.%m.%Y")
                yeni_satir.append(str(val))
        
        w_veri.append_row(yeni_satir)
        st.success("✅ Kaydedildi!")
        
        # Session state temizle
        for key in list(st.session_state.keys()):
            if key.startswith("input_"):
                del st.session_state[key]
        
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error(f"Kayıt Hatası: {e}")

if pas_gec_btn:
    try:
        w_atlanan.append_row([secilen_ad, datetime.now().strftime("%Y-%m-%d")])
        st.warning(f"⏩ {secilen_ad} atlandı.")
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")
