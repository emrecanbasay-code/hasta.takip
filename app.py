import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pandas as pd

# ==========================================
# 1. AYARLAR VE STİL
# ==========================================
st.set_page_config(page_title="Pro Hasta Takip v14", layout="centered", page_icon="🏥")

st.markdown("""
<style>
    .stMarkdown { margin-bottom: -10px; }
    div[data-testid="column"] { align-items: center; display: flex; }
    .etiket-box {
        font-weight: bold; font-size: 13px; color: #0044cc;
        text-align: right; padding-right: 10px; width: 100%;
    }
    .stTextInput, .stNumberInput, .stDateInput, .stSelectbox { width: 100%; }
    .row-container { padding: 4px 0; border-bottom: 1px solid #eee; }
    div[data-testid="stCheckbox"] { display: flex; align-items: center; }
    .stButton>button { border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🏥 Dikey Hızlı Veri Girişi (v14)")

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

# --- D. GRUPLAR ---
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

VITAL_KEYWORDS = ["ateş", "nabız", "sistolik tansiyon", "diyastolik tansiyon", "spo2", "gks"]

# Otomatik hesaplanacak alanlar (form içinde widget gösterilmeyecek)
OTOMATIK_HESAPLANAN = ["Toplam", "Yapılan Kolsültasyon sayısı"]


def baslik_sekme_belirle(baslik):
    """Her başlığın hangi sekmeye ait olduğunu belirler."""
    b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
    
    if baslik in YATIS_YERI_CHECKBOXES:
        return "yatis"
    if "isim" in b_lower or "adı soyadı" in b_lower or "cinsiyet" in b_lower or "yaş" in b_lower or "tarih" in b_lower:
        return "kimlik"
    if baslik in KOMORBIDITE_CHECKBOXES:
        return "komorbidite"
    if any(v in b_lower for v in VITAL_KEYWORDS):
        return "vital"
    if baslik in MUDAHALE_CHECKBOXES:
        return "mudahale"
    if baslik in SORUN_CHECKBOXES:
        return "sorun"
    if baslik in TETKIK_CHECKBOXES:
        return "tetkik"
    if baslik in KONSULTASYON_CHECKBOXES or baslik in KONSULTASYON_SAYI_LIST:
        return "konsultasyon"
    if baslik in MESAI_CHECKBOXES:
        return "mesai"
    if baslik in SONUC_CHECKBOXES:
        return "sonuc"
    if "süre" in b_lower and ("karar" in b_lower or "transfer" in b_lower or "transver" in b_lower):
        return "kimlik"
    if any(x in b_lower for x in ['açıklama', 'not']):
        return "sonuc"
    if baslik in SIFIR_LIST:
        return "diger"
    return "diger"


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
# 2. BAĞLANTI VE VERİ HAZIRLIĞI
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
# 3. SIDEBAR: GERİ AL
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
# 4. HASTA SEÇİMİ (FİLTRELİ ARAMA)
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

        st.toast("Bilgiler çekildi!", icon="✅")

st.markdown("---")

# ==========================================
# 5. FORM OLUŞTURMA (SEKMELERLE GRUPLANDIRILMIŞ)
# ==========================================
input_values = {}

# Başlıkları sekmelere ayır
sekme_basliklar = {
    "kimlik": [], "yatis": [], "vital": [], "komorbidite": [], 
    "mudahale": [], "sorun": [], "tetkik": [], "konsultasyon": [], 
    "mesai": [], "sonuc": [], "diger": []
}

for i, baslik in enumerate(headers):
    if not baslik.strip():
        continue
    # Otomatik hesaplanan alanları atla (form'da gösterilmeyecek)
    if baslik in OTOMATIK_HESAPLANAN:
        continue
    sekme = baslik_sekme_belirle(baslik)
    sekme_basliklar[sekme].append((i, baslik))

# Session state başlatma (tüm alanlar için, form dışında)
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


def render_alan(i, baslik):
    """Tek bir form alanını render eder ve değerini döndürür."""
    key_id = f"input_{i}"
    b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
    
    # 1. OTOMATİK "0" VEYA SABİT GELEN SAYILAR
    if baslik in SIFIR_LIST or b_lower in SABIT_DEGERLER:
        try:
            val = float(st.session_state[key_id]) if st.session_state[key_id] else 0.0
        except:
            val = 0.0
        
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{baslik}:</div>", unsafe_allow_html=True)
        with c2:
            if "ateş" in b_lower:
                return st.number_input("Sayı", value=val, step=0.1, format="%.1f", key=key_id, label_visibility="collapsed")
            else:
                return st.number_input("Sayı", value=int(val), step=1, format="%d", key=key_id, label_visibility="collapsed")
    
    # 2. CHECKBOX
    elif baslik in CHECKBOX_LIST:
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{baslik}:</div>", unsafe_allow_html=True)
        with c2:
            val = st.checkbox("Var", key=key_id)
            return 1 if val else 0
    
    # 3. İSİM
    elif "isim" in b_lower or "adı soyadı" in b_lower:
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{baslik}:</div>", unsafe_allow_html=True)
        with c2:
            return st.text_input("İsim", key=key_id, label_visibility="collapsed")
    
    # 4. TARİH
    elif "tarih" in b_lower:
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{baslik}:</div>", unsafe_allow_html=True)
        with c2:
            val_t = st.session_state[key_id] if st.session_state[key_id] else datetime.now()
            return st.date_input("Tarih", value=val_t, key=key_id, format="DD.MM.YYYY", label_visibility="collapsed")
    
    # 5. SÜRELER
    elif "süre" in b_lower and ("karar" in b_lower or "transfer" in b_lower or "transver" in b_lower):
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{baslik}:</div>", unsafe_allow_html=True)
        with c2:
            return st.text_input("Süre", key=key_id, label_visibility="collapsed")
    
    # 6. CİNSİYET
    elif "cinsiyet" in b_lower:
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{baslik}:</div>", unsafe_allow_html=True)
        with c2:
            return st.selectbox("Cinsiyet", ["", "E", "K"], key=key_id, label_visibility="collapsed")
    
    # 7. VİTAL BULGULAR (SABİT LİSTEDE DEĞİLSE)
    elif any(x in b_lower for x in ['yaş', 'ateş', 'nabız', 'tansiyon', 'spo2', 'gks']):
        try:
            m_val = float(st.session_state[key_id]) if st.session_state[key_id] else 0.0
        except:
            m_val = 0.0
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{baslik}:</div>", unsafe_allow_html=True)
        with c2:
            if "ateş" in b_lower:
                return st.number_input("Değer", value=m_val, step=0.1, format="%.1f", key=f"num_{i}", label_visibility="collapsed")
            else:
                return st.number_input("Değer", value=int(m_val), step=1, format="%d", key=f"num_{i}", label_visibility="collapsed")
    
    # 8. NOT ALANLARI
    elif any(x in b_lower for x in ['açıklama', 'not']):
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{baslik}:</div>", unsafe_allow_html=True)
        with c2:
            return st.text_area("Not", key=key_id, height=70, label_visibility="collapsed")
    
    # 9. DİĞER
    else:
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{baslik}:</div>", unsafe_allow_html=True)
        with c2:
            return st.text_input("Sonuç", key=key_id, label_visibility="collapsed")


def render_checkbox_grubu(items, kolon_sayisi=4):
    """Checkbox grubunu yan yana kolonlarda render eder."""
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


with st.form("veri_giris", clear_on_submit=False):
    st.write("### 📝 Kayıt Formu")
    
    tab_kimlik, tab_vital, tab_komorbidite, tab_tetkik, tab_konsultasyon, tab_mesai_sonuc, tab_diger = st.tabs([
        "👤 Kimlik & Yatış", "💓 Vital Bulgular", "🩺 Komorbidite & Müdahale", 
        "🔬 Tetkikler", "📋 Konsültasyonlar", "⏰ Mesai & Sonuç", "📁 Diğer"
    ])
    
    # ---- SEKME 1: KİMLİK & YATIŞ ----
    with tab_kimlik:
        st.markdown("**Hasta Kimlik Bilgileri**")
        for i, baslik in sekme_basliklar["kimlik"]:
            input_values[baslik] = render_alan(i, baslik)
        
        if sekme_basliklar["yatis"]:
            st.markdown("---")
            st.markdown("**Yatış Yeri**")
            yatis_items = [(i, b) for i, b in sekme_basliklar["yatis"] if b in YATIS_YERI_CHECKBOXES]
            if yatis_items:
                input_values.update(render_checkbox_grubu(yatis_items, kolon_sayisi=4))
            for i, baslik in sekme_basliklar["yatis"]:
                if baslik not in YATIS_YERI_CHECKBOXES:
                    input_values[baslik] = render_alan(i, baslik)
    
    # ---- SEKME 2: VİTAL BULGULAR ----
    with tab_vital:
        st.markdown("**Vital Bulgular**")
        for i, baslik in sekme_basliklar["vital"]:
            input_values[baslik] = render_alan(i, baslik)
    
    # ---- SEKME 3: KOMORBİDİTE & MÜDAHALE ----
    with tab_komorbidite:
        st.markdown("**Komorbiditeler**")
        komorbidite_items = [(i, b) for i, b in sekme_basliklar["komorbidite"] if b in KOMORBIDITE_CHECKBOXES]
        if komorbidite_items:
            input_values.update(render_checkbox_grubu(komorbidite_items, kolon_sayisi=5))
        
        if sekme_basliklar["mudahale"]:
            st.markdown("---")
            st.markdown("**Müdahale**")
            mudahale_items = [(i, b) for i, b in sekme_basliklar["mudahale"] if b in MUDAHALE_CHECKBOXES]
            if mudahale_items:
                input_values.update(render_checkbox_grubu(mudahale_items, kolon_sayisi=4))
        
        if sekme_basliklar["sorun"]:
            st.markdown("---")
            st.markdown("**Sorun Bildirimi**")
            sorun_items = [(i, b) for i, b in sekme_basliklar["sorun"] if b in SORUN_CHECKBOXES]
            if sorun_items:
                input_values.update(render_checkbox_grubu(sorun_items, kolon_sayisi=2))
    
    # ---- SEKME 4: TETKİKLER ----
    with tab_tetkik:
        st.markdown("**İstenen Tetkikler**")
        tetkik_items = [(i, b) for i, b in sekme_basliklar["tetkik"] if b in TETKIK_CHECKBOXES]
        if tetkik_items:
            input_values.update(render_checkbox_grubu(tetkik_items, kolon_sayisi=5))
    
    # ---- SEKME 5: KONSÜLTASYONLAR ----
    with tab_konsultasyon:
        st.markdown("**İstenen Konsültasyonlar**")
        kons_cb_items = [(i, b) for i, b in sekme_basliklar["konsultasyon"] if b in KONSULTASYON_CHECKBOXES]
        if kons_cb_items:
            input_values.update(render_checkbox_grubu(kons_cb_items, kolon_sayisi=4))
        
        st.markdown("---")
        st.markdown("**Konsültasyon Sayıları**")
        for i, baslik in sekme_basliklar["konsultasyon"]:
            if baslik in KONSULTASYON_SAYI_LIST:
                input_values[baslik] = render_alan(i, baslik)
            elif baslik not in KONSULTASYON_CHECKBOXES:
                input_values[baslik] = render_alan(i, baslik)
    
    # ---- SEKME 6: MESAİ & SONUÇ ----
    with tab_mesai_sonuc:
        st.markdown("**Mesai Dilimi**")
        mesai_items = [(i, b) for i, b in sekme_basliklar["mesai"] if b in MESAI_CHECKBOXES]
        if mesai_items:
            input_values.update(render_checkbox_grubu(mesai_items, kolon_sayisi=3))
        
        if sekme_basliklar["sonuc"]:
            st.markdown("---")
            st.markdown("**Sonuç**")
            sonuc_cb_items = [(i, b) for i, b in sekme_basliklar["sonuc"] if b in SONUC_CHECKBOXES]
            if sonuc_cb_items:
                input_values.update(render_checkbox_grubu(sonuc_cb_items, kolon_sayisi=4))
            for i, baslik in sekme_basliklar["sonuc"]:
                if baslik not in SONUC_CHECKBOXES:
                    input_values[baslik] = render_alan(i, baslik)
    
    # ---- SEKME 7: DİĞER ----
    with tab_diger:
        st.markdown("**Diğer Alanlar**")
        for i, baslik in sekme_basliklar["diger"]:
            input_values[baslik] = render_alan(i, baslik)

    st.markdown("---")
    c_btn1, c_btn2 = st.columns([3, 1])
    kaydet_btn = c_btn1.form_submit_button("✅ VERİYİ KAYDET", type="primary", use_container_width=True)

pas_gec_btn = st.button("🚫 PAS GEÇ", use_container_width=True)

# ==========================================
# 6. KAYIT (OTOMATİK HESAPLAMALAR BURADA)
# ==========================================
if kaydet_btn:
    try:
        # --- Otomatik Hesaplamalar (form dışında, kayıt anında) ---
        # Konsültasyon checkbox'larından toplam hesapla
        konsultasyon_toplam = sum(1 for b in KONSULTASYON_CHECKBOXES if input_values.get(b, 0) == 1)
        input_values["Yapılan Kolsültasyon sayısı"] = konsultasyon_toplam
        
        # Toplam = 1Servis + Ybü
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
