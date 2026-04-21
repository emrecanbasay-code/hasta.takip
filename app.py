import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pandas as pd

# ==========================================
# 1. AYARLAR VE MOBİL STİL
# ==========================================
st.set_page_config(page_title="Pro Hasta Takip v15 Mobil", layout="centered", page_icon="🏥")

st.markdown("""
<style>
    /* --- GENEL MOBİL OPTİMİZASYON --- */
    .stMarkdown { margin-bottom: -10px; }
    
    .etiket-box {
        font-weight: bold; font-size: 14px; color: #0044cc;
        padding: 4px 0; width: 100%;
    }
    
    /* --- BÜYÜK BUTONLAR --- */
    .stButton > button {
        border-radius: 10px; font-weight: bold;
        min-height: 56px; font-size: 16px;
    }
    div[data-testid="stFormSubmitButton"] > button {
        min-height: 60px; font-size: 18px;
        border-radius: 12px; font-weight: 800;
    }
    
    /* --- DOKUNMATİK DOSTU CHECKBOX --- */
    div[data-testid="stCheckbox"] {
        display: flex; align-items: center;
    }
    div[data-testid="stCheckbox"] label {
        font-size: 15px !important;
        padding: 8px 4px !important;
        min-height: 44px !important;
        display: flex; align-items: center;
    }
    div[data-testid="stCheckbox"] label span[data-testid="stCheckboxLabel"] {
        font-size: 15px !important;
    }
    
    /* --- SLIDER MOBİL UYUM --- */
    div[data-testid="stSlider"] {
        padding-top: 4px; padding-bottom: 4px;
    }
    div[data-testid="stSlider"] div[data-testid="stThumbValue"] {
        font-size: 16px !important; font-weight: bold;
    }
    
    /* --- TABS MOBİL UYUM --- */
    button[data-baseweb="tab"] {
        font-size: 13px !important;
        padding: 10px 8px !important;
    }
    
    /* --- SATIR AYIRICI --- */
    .row-container { padding: 4px 0; border-bottom: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

st.title("🏥 Mobil Hızlı Veri Girişi (v15)")

# ==========================================
# 2. SABİTLER VE LİSTELER
# ==========================================

# --- A. CHECKBOX OLACAKLAR (EVET/HAYIR) ---
CHECKBOX_LIST = [
    "1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü", "Servis",
    "HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER",
    "Entübasyon", "İnotrop", "Mükerrer tetkik Ya da tedavi istemi", 
    "Kesin tanı koyulamaması", "8 saati aşıp yatmaması", "Birden fazla kliniği ilgilendirmesi",
    "KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı",  
    "Cr", "Ct", "Mr", "Usg",
    "Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb", "Plastik", "Göz", 
    "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji", "Göğüs H.", "Enfeksiyon H.", 
    "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji",
    "08.00-16.00", "16.00-24.00", "00.00-08.00",
    "DEVİR", "Taburcu", "Ölüm", "T. RED"
]

# --- B. OTOMATİK "0" GELECEK OLANLAR (SAYI GİRİŞİ) ---
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

# --- C. VARSAYILAN SABİT DEĞERLER ---
SABIT_DEGERLER = {
    "ateş": 36.5,
    "sistolik tansiyon": 120,
    "diyastolik tansiyon": 80,
    "nabız": 80,
    "spo2": 98,
    "gks": 15
}

# --- D. GRUPLANDIRMA ---
KOMORBIDITE_CHECKBOXES = ["HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER"]
YATIS_YERI_CHECKBOXES = ["1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü", "Servis"]
MUDAHALE_CHECKBOXES = ["Entübasyon", "İnotrop"]
SORUN_CHECKBOXES = ["Mükerrer tetkik Ya da tedavi istemi", "Kesin tanı koyulamaması", 
                     "8 saati aşıp yatmaması", "Birden fazla kliniği ilgilendirmesi"]
TETKIK_CHECKBOXES = ["KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı", "Cr", "Ct", "Mr", "Usg"]
KONSULTASYON_CHECKBOXES = ["Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb", "Plastik", "Göz", 
                           "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji", "Göğüs H.", "Enfeksiyon H.", 
                           "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji"]
KONSULTASYON_SAYI_LIST = ["1Dahilye", "1Göğüs Hast", "1Genel Cerrahi", "1Nrş", "1KVC", 
                          "1Kbb", "1Plastik", "1Göz", "1Üroloji", "1Göğüs C.", 
                          "1Kardiyoloji", "1Nöroloji", "1Orto", "1Enfeksiyon H.", 
                          "1Psikiyatri", "1Cildiye", "1Anestezi", "1Radyoloji"]
MESAI_CHECKBOXES = ["08.00-16.00", "16.00-24.00", "00.00-08.00"]
SONUC_CHECKBOXES = ["DEVİR", "Taburcu", "Ölüm", "T. RED"]

# --- E. SLIDER ARALIKLARI ---
SLIDER_AYARLARI = {
    "ateş":               {"min": 35.0, "max": 42.0, "step": 0.1, "default": 36.5, "format": "%.1f"},
    "nabız":              {"min": 30,   "max": 220,  "step": 1,   "default": 80,   "format": "%d"},
    "sistolik tansiyon":  {"min": 50,   "max": 300,  "step": 5,   "default": 120,  "format": "%d"},
    "diyastolik tansiyon":{"min": 20,   "max": 200,  "step": 5,   "default": 80,   "format": "%d"},
    "spo2":               {"min": 50,   "max": 100,  "step": 1,   "default": 98,   "format": "%d"},
    "gks":                {"min": 3,    "max": 15,   "step": 1,   "default": 15,   "format": "%d"},
}

# Otomatik hesaplanan alanlar (form'da widget gösterilmeyecek)
OTOMATIK_HESAPLANAN = ["Toplam", "Yapılan Kolsültasyon sayısı"]

# --- F. SEKME DAĞILIMI FONKSİYONU ---
def baslik_sekme_belirle(baslik):
    """Her başlığın hangi sekmeye ait olduğunu belirler (4 sekme)."""
    b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
    
    # Sekme 1: Hasta Bilgileri
    if baslik in YATIS_YERI_CHECKBOXES:
        return "hasta"
    if "isim" in b_lower or "adı soyadı" in b_lower or "cinsiyet" in b_lower or "tarih" in b_lower:
        return "hasta"
    if "yaş" in b_lower:
        return "hasta"
    if baslik in KOMORBIDITE_CHECKBOXES:
        return "hasta"
    if "süre" in b_lower and ("karar" in b_lower or "transfer" in b_lower or "transver" in b_lower):
        return "hasta"
    if baslik in ["Sıra Numarası", "1Servis", "Ybü"]:
        return "hasta"
    
    # Sekme 2: Vital Bulgular
    if any(v in b_lower for v in ["ateş", "nabız", "sistolik tansiyon", "diyastolik tansiyon", "spo2", "gks"]):
        return "vital"
    if baslik in MUDAHALE_CHECKBOXES:
        return "vital"
    
    # Sekme 3: Laboratuvar/Tetkik
    if baslik in TETKIK_CHECKBOXES:
        return "lab"
    if baslik in SORUN_CHECKBOXES:
        return "lab"
    
    # Sekme 4: Sonuç/Konsültasyon
    if baslik in KONSULTASYON_CHECKBOXES or baslik in KONSULTASYON_SAYI_LIST:
        return "sonuc"
    if baslik in MESAI_CHECKBOXES:
        return "sonuc"
    if baslik in SONUC_CHECKBOXES:
        return "sonuc"
    if any(x in b_lower for x in ['açıklama', 'not']):
        return "sonuc"
    
    return "hasta"


def mesai_saati_belirle(saat_str):
    """Yatış saatine göre hangi mesai diliminin seçilmesi gerektiğini belirler."""
    try:
        saat_str = saat_str.strip()
        for fmt in ["%H:%M", "%H.%M", "%H:%M:%S"]:
            try:
                t = datetime.strptime(saat_str, fmt)
                saat = t.hour
                if 8 <= saat < 16:
                    return "08.00-16.00"
                elif 16 <= saat < 24:
                    return "16.00-24.00"
                else:
                    return "00.00-08.00"
            except ValueError:
                continue
    except:
        pass
    return None


# ==========================================
# 3. BAĞLANTI VE VERİ HAZIRLIĞI
# ==========================================
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=120)
def verileri_hazirla():
    client = get_connection()
    sh = client.open("Hasta_Takip_Sistemi")
    w_veri = sh.worksheet("Veri")
    w_liste = sh.worksheet("Liste")
    
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
        
    return headers, w_liste.get_all_values()

def get_worksheets():
    """Yazma işlemleri için cache'siz worksheet referansları döndürür."""
    client = get_connection()
    sh = client.open("Hasta_Takip_Sistemi")
    return sh.worksheet("Veri"), sh.worksheet("Atlananlar")

try:
    headers, liste_rows = verileri_hazirla()
    w_veri, w_atlanan = get_worksheets()
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

# ==========================================
# 4. SIDEBAR: GERİ AL
# ==========================================
with st.sidebar:
    st.header("⚙️ İşlemler")
    st.write("Son satırı silmek için:")
    if st.button("⏪ SON KAYDI SİL", type="primary", use_container_width=True):
        mevcut = w_veri.get_all_values()
        if len(mevcut) > 2:
            w_veri.delete_rows(len(mevcut))
            st.success("✅ Silindi.")
            st.cache_data.clear()
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Veri yok.")

# ==========================================
# 5. HASTA SEÇİMİ
# ==========================================
with st.container():
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

    st.info(f"Kalan Hasta: **{len(yapilacaklar)}**")
    
    # --- Hasta Arama Filtresi ---
    arama_metni = st.text_input("🔍 Hasta Ara (isim veya tarih):", "", key="hasta_arama")
    
    if arama_metni.strip():
        filtreli = [x for x in yapilacaklar 
                    if arama_metni.lower() in x['isim'].lower() 
                    or arama_metni in x['tarih']]
    else:
        filtreli = yapilacaklar
    
    if not filtreli:
        st.warning("Aramayla eşleşen hasta bulunamadı.")
        st.stop()
    
    secenekler = [f"{x['isim']} | {x['tarih']}" for x in filtreli]
    secilen_str = st.selectbox("👇 Sıradaki Hasta:", secenekler)
    secilen_ad = secilen_str.split(" | ")[0]
    secilen_veri = next((x for x in filtreli if x['isim'] == secilen_ad), None)
    
    col_info, col_btn = st.columns([2, 1])
    col_info.warning(f"⏰ **Yatış Saati:** {secilen_veri['saat']}")
    
    getir_btn = col_btn.button("⬇️ BİLGİLERİ DOLDUR", type="primary", use_container_width=True)

    if getir_btn and secilen_veri:
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

        # --- Mesai Saati Otomatik Seçimi ---
        otomatik_mesai = mesai_saati_belirle(secilen_veri['saat'])
        if otomatik_mesai:
            for idx, h in enumerate(headers):
                if h in MESAI_CHECKBOXES:
                    key_id = f"input_{idx}"
                    st.session_state[key_id] = (h == otomatik_mesai)

        st.rerun()

# ==========================================
# 6. "HEPSİNİ NORMAL GETİR" BUTONU (FORM DIŞI)
# ==========================================
st.markdown("---")

def normal_vital_doldur():
    """Vital bulguları normal değerlerle doldurur (callback)."""
    for idx, h in enumerate(headers):
        b_lower = h.lower().replace("İ", "i").replace("I", "ı").strip()
        if b_lower in SABIT_DEGERLER:
            st.session_state[f"input_{idx}"] = SABIT_DEGERLER[b_lower]

st.button("💚 Vitalleri Normal Getir", on_click=normal_vital_doldur, 
          type="secondary", use_container_width=True)

# ==========================================
# 7. FORM OLUŞTURMA (4 SEKME + MOBİL SLİDER)
# ==========================================
input_values = {}

# Başlıkları sekmelere ayır
sekme_basliklar = {"hasta": [], "vital": [], "lab": [], "sonuc": []}

for i, baslik in enumerate(headers):
    if not baslik.strip():
        continue
    if baslik in OTOMATIK_HESAPLANAN:
        continue
    sekme = baslik_sekme_belirle(baslik)
    sekme_basliklar[sekme].append((i, baslik))

# Session state başlatma (form dışında, tüm alanlar için)
for i, baslik in enumerate(headers):
    if not baslik.strip():
        continue
    if baslik in OTOMATIK_HESAPLANAN:
        continue
    key_id = f"input_{i}"
    b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
    
    if key_id not in st.session_state:
        if b_lower in SABIT_DEGERLER:
            st.session_state[key_id] = SABIT_DEGERLER[b_lower]
        elif baslik in SIFIR_LIST:
            st.session_state[key_id] = 0
        elif "tarih" in b_lower:
            st.session_state[key_id] = datetime.now()
        elif baslik in CHECKBOX_LIST:
            st.session_state[key_id] = False
        else:
            st.session_state[key_id] = ""


# --- YARDIMCI RENDER FONKSİYONLARI ---

def render_slider_vital(i, baslik):
    """Vital bulgu alanını select_slider olarak render eder."""
    key_id = f"input_{i}"
    b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
    
    ayar = SLIDER_AYARLARI.get(b_lower)
    if not ayar:
        return render_alan_standart(i, baslik)
    
    # Slider seçeneklerini oluştur
    if ayar["step"] == 0.1:
        options = [round(ayar["min"] + x * 0.1, 1) for x in range(int((ayar["max"] - ayar["min"]) / 0.1) + 1)]
    else:
        options = list(range(int(ayar["min"]), int(ayar["max"]) + 1, int(ayar["step"])))
    
    # Mevcut değeri al
    try:
        current_val = st.session_state.get(key_id, ayar["default"])
        if ayar["step"] == 0.1:
            current_val = round(float(current_val), 1)
        else:
            current_val = int(float(current_val))
        if current_val not in options:
            current_val = ayar["default"]
    except:
        current_val = ayar["default"]
    
    st.markdown(f"**{baslik}**")
    val = st.select_slider(
        baslik,
        options=options,
        value=current_val,
        format_func=lambda x: ayar["format"] % x,
        key=key_id,
        label_visibility="collapsed"
    )
    return val


def render_yas_slider(i, baslik):
    """Yaş alanını select_slider olarak render eder."""
    key_id = f"input_{i}"
    options = list(range(0, 121))
    
    try:
        current_val = int(float(st.session_state.get(key_id, 0)))
        if current_val < 0 or current_val > 120:
            current_val = 0
    except:
        current_val = 0
    
    st.markdown(f"**{baslik}**")
    val = st.select_slider(
        baslik,
        options=options,
        value=current_val,
        key=key_id,
        label_visibility="collapsed"
    )
    return val


def render_checkbox_grubu(items, kolon_sayisi=3):
    """Checkbox grubunu yan yana kolonlarda render eder (mobil: 3 kolon)."""
    results = {}
    for satir_baslangic in range(0, len(items), kolon_sayisi):
        satir_items = items[satir_baslangic:satir_baslangic + kolon_sayisi]
        cols = st.columns(kolon_sayisi)
        for col_idx, (i, baslik) in enumerate(satir_items):
            key_id = f"input_{i}"
            with cols[col_idx]:
                val = st.checkbox(baslik, key=key_id)
                results[baslik] = 1 if val else 0
    return results


def render_alan_standart(i, baslik):
    """Standart alan render (number_input, text_input vb.)."""
    key_id = f"input_{i}"
    b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
    
    # SAYI ALANLARI (SIFIR_LIST)
    if baslik in SIFIR_LIST:
        try:
            val = int(float(st.session_state[key_id])) if st.session_state[key_id] else 0
        except:
            val = 0
        st.markdown(f"**{baslik}**")
        return st.number_input(baslik, value=val, step=1, format="%d", key=key_id, label_visibility="collapsed")
    
    # İSİM
    if "isim" in b_lower or "adı soyadı" in b_lower:
        st.markdown(f"**{baslik}**")
        return st.text_input(baslik, key=key_id, label_visibility="collapsed")
    
    # TARİH
    if "tarih" in b_lower:
        val_t = st.session_state.get(key_id, datetime.now())
        if not val_t:
            val_t = datetime.now()
        st.markdown(f"**{baslik}**")
        return st.date_input(baslik, value=val_t, key=key_id, format="DD.MM.YYYY", label_visibility="collapsed")
    
    # CİNSİYET
    if "cinsiyet" in b_lower:
        st.markdown(f"**{baslik}**")
        return st.selectbox(baslik, ["", "E", "K"], key=key_id, label_visibility="collapsed")
    
    # SÜRELER
    if "süre" in b_lower and ("karar" in b_lower or "transfer" in b_lower or "transver" in b_lower):
        st.markdown(f"**{baslik}**")
        return st.text_input(baslik, key=key_id, label_visibility="collapsed")
    
    # NOT ALANLARI
    if any(x in b_lower for x in ['açıklama', 'not']):
        st.markdown(f"**{baslik}**")
        return st.text_area(baslik, key=key_id, height=80, label_visibility="collapsed")
    
    # DİĞER
    st.markdown(f"**{baslik}**")
    return st.text_input(baslik, key=key_id, label_visibility="collapsed")


# ==========================================
# 8. ANA FORM
# ==========================================
with st.form("veri_giris", clear_on_submit=False):
    
    tab_hasta, tab_vital, tab_lab, tab_sonuc = st.tabs([
        "👤 Hasta Bilgileri", "💓 Vital Bulgular", "🔬 Lab / Tetkik", "📋 Sonuç / Konsültasyon"
    ])
    
    # ======================================
    # SEKME 1: HASTA BİLGİLERİ
    # ======================================
    with tab_hasta:
        # --- Kimlik alanları ---
        for i, baslik in sekme_basliklar["hasta"]:
            b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
            
            # Yaş → slider
            if "yaş" in b_lower:
                input_values[baslik] = render_yas_slider(i, baslik)
            # Checkbox grupları
            elif baslik in YATIS_YERI_CHECKBOXES:
                pass  # Aşağıda grup olarak render edilecek
            elif baslik in KOMORBIDITE_CHECKBOXES:
                pass  # Aşağıda grup olarak render edilecek
            else:
                input_values[baslik] = render_alan_standart(i, baslik)
        
        # Yatış Yeri checkbox grubu
        yatis_items = [(i, b) for i, b in sekme_basliklar["hasta"] if b in YATIS_YERI_CHECKBOXES]
        if yatis_items:
            st.markdown("---")
            st.markdown("**Yatış Yeri**")
            input_values.update(render_checkbox_grubu(yatis_items, kolon_sayisi=2))
        
        # Komorbidite checkbox grubu
        komorbidite_items = [(i, b) for i, b in sekme_basliklar["hasta"] if b in KOMORBIDITE_CHECKBOXES]
        if komorbidite_items:
            st.markdown("---")
            st.markdown("**Komorbiditeler**")
            input_values.update(render_checkbox_grubu(komorbidite_items, kolon_sayisi=3))
    
    # ======================================
    # SEKME 2: VİTAL BULGULAR
    # ======================================
    with tab_vital:
        st.caption("💚 Yukarıdaki 'Vitalleri Normal Getir' butonu ile hızlıca doldurabilirsiniz.")
        
        for i, baslik in sekme_basliklar["vital"]:
            b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
            
            # Vital slider alanları
            if b_lower in SLIDER_AYARLARI:
                input_values[baslik] = render_slider_vital(i, baslik)
            # Müdahale checkbox'ları
            elif baslik in MUDAHALE_CHECKBOXES:
                pass  # Aşağıda grup olarak
            else:
                input_values[baslik] = render_alan_standart(i, baslik)
        
        # Müdahale checkbox grubu
        mudahale_items = [(i, b) for i, b in sekme_basliklar["vital"] if b in MUDAHALE_CHECKBOXES]
        if mudahale_items:
            st.markdown("---")
            st.markdown("**Müdahale**")
            input_values.update(render_checkbox_grubu(mudahale_items, kolon_sayisi=2))
    
    # ======================================
    # SEKME 3: LABORATUVAR / TETKİK
    # ======================================
    with tab_lab:
        # Tetkik checkbox'ları
        tetkik_items = [(i, b) for i, b in sekme_basliklar["lab"] if b in TETKIK_CHECKBOXES]
        if tetkik_items:
            st.markdown("**İstenen Tetkikler**")
            input_values.update(render_checkbox_grubu(tetkik_items, kolon_sayisi=3))
        
        # Sorun checkbox'ları
        sorun_items = [(i, b) for i, b in sekme_basliklar["lab"] if b in SORUN_CHECKBOXES]
        if sorun_items:
            st.markdown("---")
            st.markdown("**Sorun Bildirimi**")
            input_values.update(render_checkbox_grubu(sorun_items, kolon_sayisi=1))
        
        # Diğer lab alanları
        for i, baslik in sekme_basliklar["lab"]:
            if baslik not in TETKIK_CHECKBOXES and baslik not in SORUN_CHECKBOXES:
                input_values[baslik] = render_alan_standart(i, baslik)
    
    # ======================================
    # SEKME 4: SONUÇ / KONSÜLTASYON
    # ======================================
    with tab_sonuc:
        # Konsültasyon checkbox'ları
        kons_items = [(i, b) for i, b in sekme_basliklar["sonuc"] if b in KONSULTASYON_CHECKBOXES]
        if kons_items:
            st.markdown("**İstenen Konsültasyonlar**")
            input_values.update(render_checkbox_grubu(kons_items, kolon_sayisi=3))
        
        # Konsültasyon sayıları
        kons_sayi_items = [(i, b) for i, b in sekme_basliklar["sonuc"] if b in KONSULTASYON_SAYI_LIST]
        if kons_sayi_items:
            st.markdown("---")
            st.markdown("**Konsültasyon Sayıları**")
            for i, baslik in kons_sayi_items:
                input_values[baslik] = render_alan_standart(i, baslik)
        
        # Mesai dilimleri
        mesai_items = [(i, b) for i, b in sekme_basliklar["sonuc"] if b in MESAI_CHECKBOXES]
        if mesai_items:
            st.markdown("---")
            st.markdown("**Mesai Dilimi**")
            input_values.update(render_checkbox_grubu(mesai_items, kolon_sayisi=3))
        
        # Sonuç checkbox'ları
        sonuc_items = [(i, b) for i, b in sekme_basliklar["sonuc"] if b in SONUC_CHECKBOXES]
        if sonuc_items:
            st.markdown("---")
            st.markdown("**Sonuç**")
            input_values.update(render_checkbox_grubu(sonuc_items, kolon_sayisi=2))
        
        # Diğer alanlar (açıklama, not vb.)
        for i, baslik in sekme_basliklar["sonuc"]:
            if (baslik not in KONSULTASYON_CHECKBOXES and baslik not in KONSULTASYON_SAYI_LIST 
                and baslik not in MESAI_CHECKBOXES and baslik not in SONUC_CHECKBOXES):
                input_values[baslik] = render_alan_standart(i, baslik)

    # --- KAYDET BUTONU (form içinde) ---
    st.markdown("---")
    kaydet_btn = st.form_submit_button("✅ VERİYİ KAYDET", type="primary", use_container_width=True)

# --- PAS GEÇ BUTONU (form dışında) ---
pas_gec_btn = st.button("🚫 PAS GEÇ", use_container_width=True)

# ==========================================
# 9. KAYIT (OTOMATİK HESAPLAMALAR DAHİL)
# ==========================================
if kaydet_btn:
    try:
        # --- Otomatik Hesaplamalar ---
        konsultasyon_toplam = sum(1 for b in KONSULTASYON_CHECKBOXES if input_values.get(b, 0) == 1)
        input_values["Yapılan Kolsültasyon sayısı"] = konsultasyon_toplam
        
        try:
            servis_val = int(input_values.get("1Servis", 0))
            ybu_val = int(input_values.get("Ybü", 0))
            input_values["Toplam"] = servis_val + ybu_val
        except:
            input_values["Toplam"] = 0

        # --- Satır Oluşturma ---
        yeni_satir = []
        for baslik in headers:
            if not baslik.strip():
                yeni_satir.append("")
            else:
                val = input_values.get(baslik, "")
                if val == "" and baslik in SIFIR_LIST:
                    val = 0
                if hasattr(val, 'strftime'):
                    val = val.strftime("%d.%m.%Y")
                yeni_satir.append(str(val))
        
        w_veri.append_row(yeni_satir)
        st.success("✅ Kaydedildi!")
        
        # RuntimeError önleme: anahtarları listeye kopyalayarak silme
        keys_to_delete = [key for key in list(st.session_state.keys()) 
                          if key.startswith("input_") or key.startswith("num_")]
        for key in keys_to_delete:
            del st.session_state[key]
        
        st.cache_data.clear()
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Kayıt Hatası: {e}")

if pas_gec_btn:
    try:
        w_atlanan.append_row([secilen_ad, datetime.now().strftime("%Y-%m-%d")])
        st.warning(f"⏩ {secilen_ad} atlandı.")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")
