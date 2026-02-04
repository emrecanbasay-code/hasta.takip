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

# --- GOOGLE SHEETS BAĞLANTISI (Sadece Bağlantı) ---
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# --- VERİ ÇEKME (ÖNBELLEKLİ - CACHED) ---
# Bu fonksiyon veriyi çeker ve 15 saniye boyunca hafızada tutar.
# Böylece her tıklamada Google'a gidip kota harcamaz.
@st.cache_data(ttl=15)
def get_cached_data():
    try:
        client = get_connection()
        sh = client.open(SHEET_ADI)
        w_veri = sh.worksheet("Veri")
        w_liste = sh.worksheet("Liste")
        
        # Tüm veriyi tek seferde çekiyoruz (En az maliyetli yöntem)
        data_veri = w_veri.get_all_values()
        data_liste = w_liste.get_all_values()
        
        headers = []
        if len(data_veri) > 1:
            headers = data_veri[1] 
        
        # Son Kayıt Bulma (Python tarafında yapıyoruz, API kullanmadan)
        son_kayit_isim = None
        try:
            # 5. sütun (Index 4) isim sütunu. Başlıkları atla.
            isimler = [row[4] for row in data_veri[2:] if len(row) > 4 and row[4].strip()]
            if isimler:
                son_kayit_isim = isimler[-1]
        except: pass
        
        return data_veri, headers, data_liste, son_kayit_isim
    except Exception as e:
        # Hata olursa None döndür
        return None, [], [], None

# --- YAZMA İŞLEMİ İÇİN SHEET NESNESİ ---
def get_worksheet_objects():
    client = get_connection()
    sh = client.open(SHEET_ADI)
    return sh.worksheet("Veri"), sh.worksheet("Atlananlar")

# --- ANA AKIŞ ---
tum_veriler, headers, liste_verisi, son_kayit_isim = get_cached_data()

# Güvenli değişkenler
secilen_isim = ""
secilen_tarih_str = ""
t_obj = datetime.now()

if tum_ver
