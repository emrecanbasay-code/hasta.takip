import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pandas as pd

# ==========================================
# 1. AYARLAR VE STİL
# ==========================================
st.set_page_config(
    page_title="Pro Hasta Takip v14 - Optimize", 
    layout="wide", 
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# Gelişmiş CSS
st.markdown("""
<style>
    /* Ana Konteyner */
    .main .block-container { padding-top: 1rem; }
    
    /* Bölüm Başlıkları */
    .section-header {
        font-size: 18px;
        font-weight: bold;
        color: #1f77b4;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 8px;
        margin-bottom: 15px;
    }
    
    /* Grid Yapısı */
    .stColumns { gap: 0.5rem; }
    
    /* Input Etiketleri */
    .input-label {
        font-weight: 600;
        font-size: 13px;
        color: #333;
        margin-bottom: 2px;
    }
    
    /* Hızlı Butonlar */
    .quick-btn > button {
        font-size: 11px !important;
        padding: 4px 8px !important;
        min-height: 28px !important;
    }
    
    /* Vital Bulgular Kutusu */
    .vital-box {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
    
    /* Checkbox Grid */
    div[data-testid="stCheckbox"] {
        background: #f8f9fa;
        padding: 5px 10px;
        border-radius: 5px;
        margin: 2px 0;
    }
    
    /* Başarı/Hata Mesajları */
    .stSuccess, .stWarning, .stError {
        padding: 10px;
        border-radius: 5px;
    }
    
    /* Form Submit Butonu */
    .stFormSubmitButton > button {
        background: linear-gradient(90deg, #00b894, #00cec9) !important;
        font-size: 16px !important;
        padding: 12px !important;
    }
    
    /* Accordion */
    .streamlit-expanderHeader {
        font-weight: bold;
        font-size: 15px;
        background: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SABİT LİSTELER VE SEÇENEKLER
# ==========================================

# Checkbox olacak alanlar (EVET/HAYIR)
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

# Otomatik "0" gelecek alanlar
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

# Varsayılan Sabit Değerler
SABIT_DEGERLER = {
    "ateş": 36.5,
    "sistolik tansiyon": 120,
    "diyastolik tansiyon": 80,
    "nabız": 80,
    "spo2": 98,
    "gks": 15
}

# YENİ: Dropdown Seçenekleri
TANI_SECENEKLERI = [
    "", "Pnömoni", "KOAH Ekzarbasyonu", "Kalp Yetmezliği", "Sepsis", 
    "Akut Böbrek Yetmezliği", "Serebrovasküler Olay", "Gastrointestinal Kanama",
    "Diyabetik Ketoasidoz", "Hipertansif Kriz", "Akut Koroner Sendrom",
    "Atriyal Fibrilasyon", "Derin Ven Trombozu", "Pulmoner Emboli",
    "Menenjit", "Üriner Sistem Enfeksiyonu", "Diğer"
]

YATIS_SEBEBI_SECENEKLERI = [
    "", "Nefes Darlığı", "Göğüs Ağrısı", "Karın Ağrısı", "Ateş",
    "Bilinç Bozukluğu", "Yüksek Tansiyon", "Şeker Yüksekliği", "Travma",
    "İshalli Hastalık", "Kusma", "Genel Durum Bozukluğu", "Diğer"
]

SERVIS_SECENEKLERI = [
    "", "Dahiliye Servisi", "Göğüs Hastalıkları", "Kardiyoloji", 
    "Nöroloji", "Enfeksiyon", "Genel Cerrahi", "Ortopedi", "Üroloji", "Diğer"
]

# Bölüm Grupları
BOLUM_GRUPLARI = {
    "Yatış Yeri": ["1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü", "Servis"],
    "Kronik Hastalıklar": ["HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER"],
    "Durum Özellikleri": ["Entübasyon", "İnotrop", "Mükerrer tetkik Ya da tedavi istemi", 
                          "Kesin tanı koyulamaması", "8 saati aşıp yatmaması", "Birden fazla kliniği ilgilendirmesi"],
    "Tetkikler": ["KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı", "Cr", "Ct", "Mr", "Usg"],
    "Konsültasyonlar": ["Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb", 
                        "Plastik", "Göz", "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji", 
                        "Göğüs H.", "Enfeksiyon H.", "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji"],
    "Vardiya": ["08.00-16.00", "16.00-24.00", "00.00-08.00"],
    "Sonuç": ["DEVİR", "Taburcu", "Ölüm", "T. RED"]
}

# ==========================================
# 3. BAĞLANTI FONKSİYONLARI
# ==========================================
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        dict(st.secrets["gcp_service_account"]), scope
    )
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

# ==========================================
# 4. OTURUM STATE YÖNETİMİ
# ==========================================
def init_session_state():
    """Session state'i başlat"""
    if "current_patient_index" not in st.session_state:
        st.session_state.current_patient_index = 0
    if "form_cleared" not in st.session_state:
        st.session_state.form_cleared = False

def clear_form_state():
    """Form state'ini temizle"""
    keys_to_remove = [k for k in st.session_state.keys() 
                      if k.startswith(("input_", "num_", "cb_", "sel_"))]
    for key in keys_to_remove:
        del st.session_state[key]

# ==========================================
# 5. ANA UYGULAMA
# ==========================================
def main():
    st.title("🏥 Hızlı Hasta Veri Girişi (v14 - Optimize)")
    
    init_session_state()
    
    # Bağlantı
    try:
        w_veri, w_atlanan, headers, liste_rows = verileri_hazirla()
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        st.stop()
    
    # ==========================================
    # SIDEBAR
    # ==========================================
    with st.sidebar:
        st.header("⚙️ İşlemler")
        
        # Son Kayıt Silme
        if st.button("⏪ SON KAYDI SİL", type="primary", use_container_width=True):
            mevcut = w_veri.get_all_values()
            if len(mevcut) > 2:
                w_veri.delete_rows(len(mevcut))
                st.success("✅ Silindi.")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("Silinecek veri yok.")
        
        st.divider()
        
        # Hızlı Ayarlar
        st.subheader("🎯 Hızlı Ayarlar")
        
        if st.button("🔄 Formu Temizle", use_container_width=True):
            clear_form_state()
            st.rerun()
        
        # Varsayılan Vital Bulgular
        st.subheader("📊 Varsayılan Vital")
        default_ates = st.number_input("Ateş", value=36.5, step=0.1, key="default_ates")
        default_nabiz = st.number_input("Nabız", value=80, step=1, key="default_nabiz")
        default_spo2 = st.number_input("SpO2", value=98, step=1, key="default_spo2")
        
        if st.button("✅ Varsayılanları Uygula", use_container_width=True):
            st.session_state["input_ates"] = default_ates
            st.session_state["input_nabiz"] = default_nabiz
            st.session_state["input_spo2"] = default_spo2
            st.toast("Uygulandı!", icon="✅")
    
    # ==========================================
    # HASTA SEÇİMİ
    # ==========================================
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
        st.success("🎉 Liste Bitti! Tüm hastalar işlendi.")
        st.balloons()
        st.stop()
    
    # Hasta Seçim Paneli
    col_select, col_count = st.columns([3, 1])
    
    with col_count:
        st.metric("Kalan Hasta", len(yapilacaklar))
    
    with col_select:
        secenekler = [f"{i+1}. {x['isim']} | {x['tarih']} | ⏰{x['saat']}" 
                      for i, x in enumerate(yapilacaklar)]
        secilen_str = st.selectbox("👇 Sıradaki Hasta:", secenekler, key="hasta_select")
        secilen_index = secenekler.index(secilen_str)
        secilen_ad = yapilacaklar[secilen_index]["isim"]
        secilen_veri = yapilacaklar[secilen_index]
    
    # Hasta Bilgi Kartı
    col_info1, col_info2, col_info3 = st.columns(3)
    col_info1.info(f"👤 **{secilen_ad}**")
    col_info2.info(f"📅 **Tarih:** {secilen_veri['tarih']}")
    col_info3.info(f"⏰ **Yatış Saati:** {secilen_veri['saat']}")
    
    # Bilgileri Doldur Butonu
    if st.button("⬇️ HASTA BİLGİLERİNİ ÇEK", type="secondary", use_container_width=True):
        t_obj = datetime.now()
        try:
            d_str = secilen_veri['tarih'].split(" ")[0]
            t_obj = datetime.strptime(d_str, "%Y-%m-%d")
        except:
            try:
                d_str = secilen_veri['tarih'].split(" ")[0]
                t_obj = datetime.strptime(d_str, "%d.%m.%Y")
            except:
                pass
        
        # Session state'e yaz
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
        
        st.toast("✅ Bilgiler çekildi!", icon="📥")
    
    st.divider()
    
    # ==========================================
    # FORM - BÖLÜM BÖLÜM
    # ==========================================
    input_values = {}
    
    with st.form("veri_giris", clear_on_submit=False):
        
        # ========== BÖLÜM 1: HASTA KİMLİK ==========
        with st.expander("📌 **BÖLÜM 1: Hasta Kimlik Bilgileri**", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            
            for i, baslik in enumerate(headers):
                if not baslik.strip():
                    continue
                    
                b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
                key_id = f"input_{i}"
                
                # İsim
                if "isim" in b_lower or "adı soyadı" in b_lower:
                    with col1:
                        st.markdown(f"**{baslik}:**")
                        input_values[baslik] = st.text_input("İsim", 
                            value=st.session_state.get(key_id, ""), 
                            key=key_id, label_visibility="collapsed")
                
                # Yaş
                elif "yaş" in b_lower:
                    with col2:
                        st.markdown(f"**{baslik}:**")
                        val = st.session_state.get(key_id, 0)
                        input_values[baslik] = st.number_input("Yaş", 
                            value=int(val) if val else 0, 
                            min_value=0, max_value=150, step=1,
                            key=key_id, label_visibility="collapsed")
                
                # Cinsiyet
                elif "cinsiyet" in b_lower:
                    with col3:
                        st.markdown(f"**{baslik}:**")
                        input_values[baslik] = st.selectbox("Cinsiyet", 
                            ["", "E", "K"], 
                            key=key_id, label_visibility="collapsed")
                
                # Tarih
                elif "tarih" in b_lower:
                    with col4:
                        st.markdown(f"**{baslik}:**")
                        val_t = st.session_state.get(key_id, datetime.now())
                        input_values[baslik] = st.date_input("Tarih", 
                            value=val_t, 
                            key=key_id, format="DD.MM.YYYY", 
                            label_visibility="collapsed")
        
        # ========== BÖLÜM 2: VİTAL BULGULAR ==========
        with st.expander("💓 **BÖLÜM 2: Vital Bulgular**", expanded=True):
            st.markdown("*(Eksiksiz doldurulması gerekmektedir)*")
            
            # Hızlı Butonlar
            st.markdown("#### ⚡ Hızlı Seçimler")
            qcol1, qcol2, qcol3, qcol4, qcol5 = st.columns(5)
            
            with qcol1:
                if st.button("🔥 Ateşli (>38°C)"):
                    st.session_state["input_ates"] = 38.5
                    st.rerun()
            with qcol2:
                if st.button("📉 Hipotansif (<90)"):
                    st.session_state["input_sistolik"] = 85
                    st.rerun()
            with qcol3:
                if st.button("❤️ Taşikardi (>100)"):
                    st.session_state["input_nabiz"] = 110
                    st.rerun()
            with qcol4:
                if st.button("🫁 Desatürasyon (<95)"):
                    st.session_state["input_spo2"] = 92
                    st.rerun()
            with qcol5:
                if st.button("🧠 GKS Düşük (<15)"):
                    st.session_state["input_gks"] = 13
                    st.rerun()
            
            st.markdown("---")
            
            # Vital Bulgular Grid
            vcol1, vcol2, vcol3 = st.columns(3)
            vital_headers = ["Ateş", "Sistolik Tansiyon", "Diyastolik Tansiyon", 
                           "Nabız", "SpO2", "GKS"]
            
            for i, baslik in enumerate(headers):
                if not baslik.strip():
                    continue
                    
                b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
                key_id = f"input_{i}"
                
                # Ateş
                if "ateş" in b_lower:
                    with vcol1:
                        st.markdown(f"**🌡️ {baslik}:**")
                        default_val = SABIT_DEGERLER.get("ateş", 36.5)
                        current_val = st.session_state.get(key_id, default_val)
                        input_values[baslik] = st.number_input("Ateş", 
                            value=float(current_val), step=0.1, format="%.1f",
                            key=key_id, label_visibility="collapsed")
                
                # Sistolik Tansiyon
                elif "sistolik" in b_lower:
                    with vcol1:
                        st.markdown(f"**📊 {baslik}:**")
                        default_val = SABIT_DEGERLER.get("sistolik tansiyon", 120)
                        current_val = st.session_state.get(key_id, default_val)
                        input_values[baslik] = st.number_input("Sistolik", 
                            value=int(current_val), step=1,
                            key=key_id, label_visibility="collapsed")
                
                # Diyastolik Tansiyon
                elif "diyastolik" in b_lower:
                    with vcol2:
                        st.markdown(f"**📊 {baslik}:**")
                        default_val = SABIT_DEGERLER.get("diyastolik tansiyon", 80)
                        current_val = st.session_state.get(key_id, default_val)
                        input_values[baslik] = st.number_input("Diyastolik", 
                            value=int(current_val), step=1,
                            key=key_id, label_visibility="collapsed")
                
                # Nabız
                elif "nabız" in b_lower:
                    with vcol2:
                        st.markdown(f"**❤️ {baslik}:**")
                        default_val = SABIT_DEGERLER.get("nabız", 80)
                        current_val = st.session_state.get(key_id, default_val)
                        input_values[baslik] = st.number_input("Nabız", 
                            value=int(current_val), step=1,
                            key=key_id, label_visibility="collapsed")
                
                # SpO2
                elif "spo2" in b_lower:
                    with vcol3:
                        st.markdown(f"**🫁 {baslik}:**")
                        default_val = SABIT_DEGERLER.get("spo2", 98)
                        current_val = st.session_state.get(key_id, default_val)
                        input_values[baslik] = st.number_input("SpO2", 
                            value=int(current_val), step=1, min_value=0, max_value=100,
                            key=key_id, label_visibility="collapsed")
                
                # GKS
                elif "gks" in b_lower:
                    with vcol3:
                        st.markdown(f"**🧠 {baslik}:**")
                        default_val = SABIT_DEGERLER.get("gks", 15)
                        current_val = st.session_state.get(key_id, default_val)
                        input_values[baslik] = st.number_input("GKS", 
                            value=int(current_val), step=1, min_value=3, max_value=15,
                            key=key_id, label_visibility="collapsed")
        
        # ========== BÖLÜM 3: YATIŞ VE TANI ==========
        with st.expander("🏥 **BÖLÜM 3: Yatış ve Tanı Bilgileri**"):
            # Yatış Yeri (Radio - Tek Seçim)
            st.markdown("#### 📍 Yatış Yeri (Tek Seçim)")
            yatis_yeri = st.radio("Yatış Yeri", 
                ["Hiçbiri", "1. Basamak YBÜ", "2. Basamak YBÜ", "3. Basamak YBÜ", "Servis"],
                horizontal=True, key="yatis_yeri_radio")
            
            # Yatış yeri checkbox'larını ayarla
            yatis_map = {
                "Hiçbiri": [],
                "1. Basamak YBÜ": ["1. Basamak Ybü"],
                "2. Basamak YBÜ": ["2. Basamak Ybü"],
                "3. Basamak YBÜ": ["3. Basamak Ybü"],
                "Servis": ["Servis"]
            }
            
            # Kronik Hastalıklar (Multi-select)
            st.markdown("#### 🩺 Kronik Hastalıklar")
            kronik_secim = st.multiselect("Kronik Hastalıklar", 
                BOLUM_GRUPLARI["Kronik Hastalıklar"],
                key="kronik_multiselect")
            
            # Tanı (Dropdown)
            st.markdown("#### 🔍 Tanı")
            tani = st.selectbox("Birincil Tanı", TANI_SECENEKLERI, key="tani_select")
            
            # Yatış Sebebi (Dropdown)
            st.markdown("#### 📋 Yatış Sebebi")
            yatis_sebebi = st.selectbox("Yatış Sebebi", YATIS_SEBEBI_SECENEKLERI, key="yatis_sebep_select")
            
            # Durum Özellikleri
            st.markdown("#### ⚠️ Durum Özellikleri")
            durum_cols = st.columns(3)
            durum_ozellikleri = []
            for idx, ozellik in enumerate(BOLUM_GRUPLARI["Durum Özellikleri"]):
                with durum_cols[idx % 3]:
                    if st.checkbox(ozellik, key=f"durum_{idx}"):
                        durum_ozellikleri.append(ozellik)
        
        # ========== BÖLÜM 4: TETKİKLER ==========
        with st.expander("🔬 **BÖLÜM 4: Tetkikler**"):
            st.markdown("Yapılan tetkikleri işaretleyin:")
            
            tetkik_cols = st.columns(5)
            tetkikler = []
            for idx, tetkik in enumerate(BOLUM_GRUPLARI["Tetkikler"]):
                with tetkik_cols[idx % 5]:
                    if st.checkbox(tetkik, key=f"tetkik_{idx}"):
                        tetkikler.append(tetkik)
        
        # ========== BÖLÜM 5: KONSÜLTASYONLAR ==========
        with st.expander("👨‍⚕️ **BÖLÜM 5: Konsültasyonlar**"):
            st.markdown("Konsültasyon istenen bölümleri işaretleyin:")
            
            kons_cols = st.columns(4)
            konsultasyonlar = []
            for idx, kons in enumerate(BOLUM_GRUPLARI["Konsültasyonlar"]):
                with kons_cols[idx % 4]:
                    if st.checkbox(kons, key=f"kons_{idx}"):
                        konsultasyonlar.append(kons)
        
        # ========== BÖLÜM 6: SONUÇ ==========
        with st.expander("📋 **BÖLÜM 6: Sonuç ve Vardiya**", expanded=True):
            sonuc_cols = st.columns(3)
            
            with sonuc_cols[0]:
                st.markdown("#### ⏰ Vardiya")
                vardiya = st.radio("Vardiya", 
                    ["08.00-16.00", "16.00-24.00", "00.00-08.00"],
                    key="vardiya_radio")
            
            with sonuc_cols[1]:
                st.markdown("#### 🏁 Sonuç")
                sonuc = st.radio("Sonuç", 
                    ["Devam", "DEVİR", "Taburcu", "Ölüm", "T. RED"],
                    key="sonuc_radio")
            
            with sonuc_cols[2]:
                st.markdown("#### 📝 Notlar")
                notlar = st.text_area("Ek Notlar", height=100, key="notlar_area")
        
        # ==========================================
        # KAYIT BUTONLARI
        # ==========================================
        st.markdown("---")
        btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])
        
        with btn_col1:
            kaydet_btn = st.form_submit_button("✅ KAYDET", type="primary", use_container_width=True)
        
        with btn_col2:
            pass  # Pas geç form dışında olacak
        
        with btn_col3:
            temizle_btn = st.form_submit_button("🔄 TEMİZLE", use_container_width=True)
    
    # ==========================================
    # KAYIT İŞLEMLERİ
    # ==========================================
    if kaydet_btn:
        try:
            # Tüm değerleri topla
            yeni_satir = []
            
            for baslik in headers:
                if not baslik.strip():
                    yeni_satir.append("")
                    continue
                
                b_lower = baslik.lower().replace("İ", "i").replace("I", "ı")
                
                # Yatış yeri
                if baslik in BOLUM_GRUPLARI["Yatış Yeri"]:
                    if baslik in yatis_map.get(yatis_yeri, []):
                        yeni_satir.append("1")
                    else:
                        yeni_satir.append("0")
                
                # Kronik hastalıklar
                elif baslik in BOLUM_GRUPLARI["Kronik Hastalıklar"]:
                    yeni_satir.append("1" if baslik in kronik_secim else "0")
                
                # Durum özellikleri
                elif baslik in BOLUM_GRUPLARI["Durum Özellikleri"]:
                    yeni_satir.append("1" if baslik in durum_ozellikleri else "0")
                
                # Tetkikler
                elif baslik in BOLUM_GRUPLARI["Tetkikler"]:
                    yeni_satir.append("1" if baslik in tetkikler else "0")
                
                # Konsültasyonlar
                elif baslik in BOLUM_GRUPLARI["Konsültasyonlar"]:
                    yeni_satir.append("1" if baslik in konsultasyonlar else "0")
                
                # Vardiya
                elif baslik in BOLUM_GRUPLARI["Vardiya"]:
                    yeni_satir.append("1" if baslik == vardiya else "0")
                
                # Sonuç
                elif baslik in BOLUM_GRUPLARI["Sonuç"]:
                    if baslik == sonuc or (sonuc == "Devam" and baslik not in ["DEVİR", "Taburcu", "Ölüm", "T. RED"]):
                        yeni_satir.append("1" if baslik == sonuc else "0")
                    else:
                        yeni_satir.append("0")
                
                # Diğer değerler
                elif baslik in input_values:
                    val = input_values[baslik]
                    if hasattr(val, 'strftime'):
                        val = val.strftime("%d.%m.%Y")
                    yeni_satir.append(str(val))
                else:
                    yeni_satir.append("")
            
            w_veri.append_row(yeni_satir)
            st.success(f"✅ {secilen_ad} başarıyla kaydedildi!")
            
            # Formu temizle
            clear_form_state()
            time.sleep(0.5)
            st.rerun()
            
        except Exception as e:
            st.error(f"Kayıt Hatası: {e}")
    
    if temizle_btn:
        clear_form_state()
        st.rerun()
    
    # PAS GEÇ (Form dışında)
    if st.button("🚫 PAS GEÇ", type="secondary", use_container_width=True):
        try:
            w_atlanan.append_row([secilen_ad, datetime.now().strftime("%Y-%m-%d %H:%M")])
            st.warning(f"⏩ {secilen_ad} atlandı.")
            time.sleep(0.5)
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

if __name__ == "__main__":
    main()
