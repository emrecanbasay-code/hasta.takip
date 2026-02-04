import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- AYARLAR ---
SHEET_ADI = "Hasta_Takip_Sistemi" 

st.set_page_config(page_title="Pro Hasta Takip", layout="wide", page_icon="🏥")
st.title("🏥 Akıllı Hasta Veri Giriş Paneli")

# --- YAN MENÜ (HATA AYIKLAMA) ---
st.sidebar.header("🔧 Ayarlar / Kontrol")
debug_mode = st.sidebar.checkbox("Hata Ayıklama Modunu Aç (Verileri Gör)")

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_data():
    client = get_connection()
    sh = client.open(SHEET_ADI)
    
    w_veri = sh.worksheet("Veri")
    w_liste = sh.worksheet("Liste")
    w_atlanan = sh.worksheet("Atlananlar")
    
    # 1. VERİ SAYFASI (Başlıkları okumak için kritik)
    data_veri = w_veri.get_all_values()
    
    # Başlıkları 2. satırdan alalım (Senin dosyanda 2. satırda olduğu için)
    # Eğer başlıklar 1. satırdaysa `data_veri[0]` yap.
    headers = []
    if len(data_veri) > 1:
        headers = data_veri[1] # 2. Satır Başlıklar
        # Pandas DF oluştur (Eski kayıtları kontrol için)
        df_veri = pd.DataFrame(data_veri[2:], columns=headers)
    else:
        df_veri = pd.DataFrame()

    # 2. LİSTE VE ATLANANLAR
    atlanan_list = w_atlanan.col_values(1) 
    
    return w_veri, w_liste, w_atlanan, df_veri, headers, atlanan_list

# --- SESSION STATE ---
if 'form_vals' not in st.session_state: st.session_state.form_vals = {}
if 'siradaki_kisi' not in st.session_state: st.session_state.siradaki_kisi = None

try:
    w_veri, w_liste, w_atlanan, df_veri, headers, atlanan_list = get_data()
    
    # --- SIRADAKİ HASTAYI BULMA MANTIĞI ---
    siradaki_isim = None
    siradaki_tarih_str = None
    bulundu_mesaji = "✅ Tüm liste tamamlandı!"
    
    # Kayıtlı isimler
    kayitli_isimler = []
    if 'İsim' in df_veri.columns:
        kayitli_isimler = [str(i).strip() for i in df_veri['İsim'].tolist() if str(i).strip() != '']
    atlananlar_temiz = [str(i).strip() for i in atlanan_list]

    # Listeyi Tara
    tum_veriler = w_liste.get_all_values()
    
    # Debug Modunda Listenin ilk satırlarını gösterelim ki sütun yerini bulalım
    if debug_mode:
        st.sidebar.warning("📊 Liste Dosyası İlk 5 Satır (Sütun Saymak İçin):")
        st.sidebar.write(tum_veriler[:5])

    # Excel yapına göre döngü (3. satırdan başla)
    for row in tum_veriler[2:]: 
        if len(row) < 7: continue # Satır çok kısaysa atla
        
        # --- KRİTİK DÜZELTME BURADA ---
        # Senin dosya yapın: ",,,,İsim,Doktor,Tarih" şeklinde görünüyor.
        # Bu yüzden İsim index 4, Tarih index 6 olabilir.
        aday_isim = str(row[4]).strip()  # 5. Sütun (İsim) - Burası değişti
        aday_tarih = str(row[6]).strip() # 7. Sütun (Tarih) - Burası değişti
        
        # Eğer yukarıdaki indexler yanlışsa Debug modundan bakıp değiştirebilirsin.
        
        if not aday_isim or len(aday_isim) < 3 or aday_isim.lower() in ['nan', 'none']: 
            continue
        
        if (aday_isim not in kayitli_isimler) and (aday_isim not in atlananlar_temiz):
            siradaki_isim = aday_isim
            siradaki_tarih_str = aday_tarih
            bulundu_mesaji = f"Sıradaki Hasta: **{siradaki_isim}** ({siradaki_tarih_str})"
            break

    # --- BİLGİ KUTUSU ---
    if siradaki_isim:
        st.info(f"🔔 {bulundu_mesaji}")
        c1, c2 = st.columns([1, 4])
        
        if c1.button("⬇️ Bilgileri Doldur"):
            # Tarihi düzelt
            tarih_val = datetime.now()
            try:
                # "2022-01-02" veya "02.01.2022" formatlarını dene
                t_str = siradaki_tarih_str.split(' ')[0]
                for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'):
                    try:
                        tarih_val = datetime.strptime(t_str, fmt)
                        break
                    except: pass
            except: pass
            
            st.session_state.form_vals['İsim'] = siradaki_isim
            st.session_state.form_vals['Tarih'] = tarih_val
            st.rerun()
            
        if c2.button("🚫 Pas Geç"):
            w_atlanan.append_row([siradaki_isim, siradaki_tarih_str])
            st.success("Atlandı.")
            st.rerun()
    elif debug_mode:
        st.write("Sıradaki kişi bulunamadı. Lütfen sütun indexlerini kontrol et.")

    st.markdown("---")

    # --- OTOMATİK FORM ALANI ---
    # Burada Google Sheet'teki başlıkları okuyup ona göre form oluşturuyoruz
    with st.form("main_form", clear_on_submit=True):
        st.subheader("📝 Veri Girişi")
        
        form_values = {}
        
        # Başlıkları 3'erli gruplar halinde gösterelim ki sayfa uzamasın
