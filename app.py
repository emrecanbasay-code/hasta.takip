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

# --- CHECKBOX LİSTESİ ---
CHECKBOX_LIST = [
    "HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER",
    "Entübasyon", "İnotrop", "Mükerrer tetkik Ya da tedavi istemi", 
    "Kesin tanı koyulamaması", "8 saati aşıp yatmaması", "Birden fazla kliniği ilgilendirmesi",
    "KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı", "MALİYET", 
    "Cr", "Ct", "Mr", "Usg",
    "Servis", "1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü",
    "Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb", "Plastik", "Göz", 
    "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji", "Göğüs H.", "Enfeksiyon H.", 
    "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji",
    "08.00-16.00", "16.00-24.00", "00.00-08.00",
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
            isimler = w_veri.col_values(5) 
            dolu = [x for x in isimler[2:] if x.strip()]
            if dolu: son_kayit_isim = dolu[-1]
        except: pass
        
        return w_veri, w_atlanan, headers, data_liste, son_kayit_isim
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None, None, [], [], None

# --- ANA AKIŞ ---
w_veri, w_atlanan, headers, tum_veriler, son_kayit_isim = get_data()

# --- GÜVENLİ DEĞİŞKEN BAŞLATMA ---
# Hatanın sebebi bu değişkenlerin tanımlanmamış olmasıydı.
secilen_isim = ""
secilen_tarih_str = ""
t_obj = datetime.now()
secenekler = []

if w_veri:
    
    # 1. SEÇİM ALANI
    with st.container():
        st.info(f"📝 Son Kayıt: **{son_kayit_isim if son_kayit_isim else 'Yok'}**")
        
        temiz_liste = []
        # Veri kontrolü
        if len(tum_veriler) > 3:
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
            aday_list
