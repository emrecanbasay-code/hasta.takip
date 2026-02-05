import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# --- AYARLAR ---
SHEET_ADI = "Hasta_Takip_Sistemi"

st.set_page_config(page_title="Pro Hasta Takip", layout="centered", page_icon="🏥") 

# --- CSS DÜZENLEMELERİ ---
st.markdown("""
<style>
    .stMarkdown { margin-bottom: -10px; }
    div[data-testid="column"] { align-items: center; display: flex; }
    .etiket-box {
        font-weight: bold;
        font-size: 14px;
        color: #1f77b4;
        text-align: right;
        padding-right: 15px;
        width: 100%;
    }
    .stTextInput, .stNumberInput, .stDateInput, .stSelectbox { width: 100%; }
    .row-container {
        padding: 5px 0;
        border-bottom: 1px solid #f0f2f6;
    }
    div[data-testid="stCheckbox"] { display: flex; align-items: center; }
</style>
""", unsafe_allow_html=True)

st.title("🏥 Dikey Hızlı Veri Girişi")

# --- CHECKBOX OLMASI GEREKEN SÜTUNLARIN TAM LİSTESİ ---
CHECKBOX_LIST = [
    # Yoğun Bakım Basamakları (Eklenenler)
    "1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü", "Servis",
    
    # Ek Hastalıklar
    "HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER",
    
    # Yatırılma Sebebi
    "Entübasyon", "İnotrop", "Mükerrer tetkik Ya da tedavi istemi", 
    "Kesin tanı koyulamaması", "8 saati aşıp yatmaması", "Birden fazla kliniği ilgilendirmesi",
    
    # Laboratuvar ve Görüntüleme Sayıları
    "KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı", "MALİYET", 
    "Cr", "Ct", "Mr", "Usg",
    
    # Yatırılan Bölümler
    "Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb", "Plastik", "Göz", 
    "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji", "Göğüs H.", "Enfeksiyon H.", 
    "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji",
    
    # Saatler
    "08.00-16.00", "16.00-24.00", "00.00-08.00",
    
    # Sonuç
    "DEVİR", "Taburcu", "Ölüm", "T. RED"
]

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_data():
    try:
        client = get_connection()
        sh = client.open(SHEET_ADI)
        w_veri = sh.worksheet("Veri")
        w_liste = sh.worksheet("Liste")
        w_atlanan = sh.worksheet("Atlananlar")
        
        data_veri = w_veri.get_all_values()
        headers = []
        if len(data_veri) > 1:
            headers = data_veri[1] 
        
        data_liste = w_liste.get_all_values()
        
        # Son Kayıt Bulma
        son_kayit_isim = None
        try:
            isimler = w_veri.col_values(5) # E Sütunu
            dolu = [x for x in isimler[2:] if x.strip()]
            if dolu: son_kayit_isim = dolu[-1]
        except: pass
        
        return w_veri, w_atlanan, headers, data_liste, son_kayit_isim
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None, None, [], [], None

# --- ANA AKIŞ ---
w_veri, w_atlanan, headers, tum_veriler, son_kayit_isim = get_data()

if w_veri:
    
    # 1. SEÇİM ALANI
    with st.container():
        st.info(f"📝 Son Kayıt: **{son_kayit_isim if son_kayit_isim else 'Yok'}**")
        
        temiz_liste = []
        for row in tum_veriler[3:]:
            if len(row) > 6:
                isim = str(row[4]).strip()
                tarih = str(row[6]).strip()
                if len(isim) > 2 and "Sütun" not in isim:
                    temiz_liste.append({"isim": isim, "tarih": tarih})
        
        aday_listesi = []
        if son_kayit_isim:
            idx = -1
            for i, h in enumerate(temiz_liste):
                if h["isim"] == son_kayit_isim:
                    idx = i
                    break
            if idx != -1:
                s = max(0, idx - 5)
                e = min(len(temiz_liste), idx + 10)
                aday_listesi = temiz_liste[s:e]
            else:
                aday_listesi = temiz_liste[:15]
        else:
            aday_listesi = temiz_liste[:15]
            
        secenekler = [f"{h['isim']} | {h['tarih']}" for h in aday_listesi]
        if not secenekler:
            st.error("Liste Boş.")
            st.stop()
            
        secilen_str = st.selectbox("👇 Hasta Seçiniz:", secenekler)
        secilen_isim = secilen_str.split(" | ")[0]
        secilen_tarih_str = secilen_str.split(" | ")[1]

        t_obj = datetime.now()
        try:
            t_clean = secilen_tarih_str.split(' ')[0]
            for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
                try: t_obj = datetime.strptime(t_clean, fmt); break
                except: pass
        except: pass

    st.markdown("---")
    
    # 2. DİKEY VERİ GİRİŞ FORMU
    input_values = {}
    
    with st.form("dikey_form", clear_on_submit=False):
        st.write("### 📋 Veri Kartı")
        
        for i, baslik in enumerate(headers):
            if not baslik.strip(): continue
            
            # --- KRİTİK DÜZELTME: Satır sonu karakterlerini temizle ---
            # Excel'de Alt+Enter yapılmışsa "1. Basamak\nYbü" olarak gelir.
            # Bunu "1. Basamak Ybü" haline çeviriyoruz ki listeyle eşleşsin.
            baslik_temiz = baslik.strip().replace("\n", " ")
            
            c1, c2 = st.columns([1.5, 3])
            c1.markdown(f"<div class='etiket-box'>{baslik}:</div>", unsafe_allow_html=True)
            
            key_name = f"in_{i}_{baslik}"
            
            with c2:
                # --- KURAL 1: CHECKBOX LİSTESİNDEKİLER ---
                if baslik_temiz in CHECKBOX_LIST:
                    chk = st.checkbox("Evet / Var", key=key_name)
                    input_values[baslik] = 1 if chk else 0
                
                # --- KURAL 2: İSİM ---
                elif i == 4: 
                    input_values[baslik] = st.text_input("İsim", value=secilen_isim, key=key_name, label_visibility="collapsed")
                
                # --- KURAL 3: TARİH ---
                elif i == 6:
                    input_values[baslik] = st.date_input("Tarih", value=t_obj, key=key_name, label_visibility="collapsed")
                
                # --- KURAL 4: CİNSİYET ---
                elif "cinsiyet" in baslik.lower():
                    input_values[baslik] = st.selectbox("Cinsiyet", ["", "E", "K"], key=key_name, label_visibility="collapsed")
                
                # --- KURAL 5: SAYISAL ---
                elif any(x in baslik.lower() for x in ['yaş', 'ateş', 'nabız', 'tansiyon', 'spo2']):
                    input_values[baslik] = st.number_input("Değer", value=0.0, step=1.0, format="%.2f", key=key_name, label_visibility="collapsed")
                    
                # --- KURAL 6: NOTLAR ---
                elif any(x in baslik.lower() for x in ['açıklama', 'not']):
                    input_values[baslik] = st.text_area("Not", height=68, key=key_name, label_visibility="collapsed")
                
                # --- KURAL 7: DİĞER HER ŞEY (0) ---
                else:
                    input_values[baslik] = st.text_input("Sonuç", value="0", key=key_name, label_visibility="collapsed")
            
            st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)

        st.markdown("---")
        
        col_submit, col_pass = st.columns([3, 1])
        kaydet_btn = col_submit.form_submit_button("✅ KAYDET", type="primary", use_container_width=True)
        
    pas_gec_btn = st.button("🚫 BU HASTAYI PAS GEÇ", use_container_width=True)

    # --- İŞLEMLER ---
    if kaydet_btn:
        try:
            mevcut = w_veri.col_values(5)
            dolu = [x for x in mevcut if x.strip()]
            hedef_satir = len(dolu) + 1
            if hedef_satir < 3: hedef_satir = 3
            
            yeni_satir = []
            for baslik in headers:
                if not baslik.strip():
                    yeni_satir.append("")
                else:
                    val = input_values.get(baslik, "")
                    if isinstance(val, (datetime, pd.Timestamp)): val = val.strftime("%d.%m.%Y")
                    yeni_satir.append(str(val))
            
            hucre = f"A{hedef_satir}"
            if hedef_satir > len(w_veri.get_all_values()):
                w_veri.append_row(yeni_satir)
            else:
                w_veri.update(range_name=hucre, values=[yeni_satir])
                
            st.success(f"✅ Kaydedildi! (Satır: {hedef_satir})")
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"Hata: {e}")

    if pas_gec_btn:
        try:
            w_atlanan.append_row([secilen_isim, secilen_tarih_str])
            st.warning(f"⏩ {secilen_isim} pas geçildi.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")
