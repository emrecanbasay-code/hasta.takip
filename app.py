import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- AYARLAR ---
SHEET_ADI = "Hasta_Takip_Sistemi" 

st.set_page_config(page_title="Bulut Hasta Takip", layout="wide", page_icon="☁️")
st.title("🏥 Bulut Tabanlı Hasta Giriş Paneli")

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
    
    # Başlık hatasını önlemek için get_all_values kullanıyoruz
    data_veri = w_veri.get_all_values()
    
    # Veri sayfasını DataFrame'e çevir (2. satır başlık varsayımıyla)
    if len(data_veri) > 1:
        headers = data_veri[1] # 2. satır başlık
        rows = data_veri[2:]   # 3. satır ve sonrası veri
        df_veri = pd.DataFrame(rows, columns=headers)
    else:
        df_veri = pd.DataFrame()

    # Atlananlar listesini al
    atlanan_list = w_atlanan.col_values(1) 
    
    return w_veri, w_liste, w_atlanan, df_veri, atlanan_list

# --- SESSION STATE ---
if 'form_isim' not in st.session_state: st.session_state.form_isim = ""
if 'form_tarih' not in st.session_state: st.session_state.form_tarih = datetime.now()

try:
    w_veri, w_liste, w_atlanan, df_veri, atlanan_list = get_data()
    
    # --- SIRADAKİ HASTAYI BULMA ---
    siradaki_isim = None
    siradaki_tarih_str = None
    bulundu_mesaji = "Tüm kayıtlar tamamlandı!"
    
    # Kayıtlı isimleri listeye al
    if 'İsim' in df_veri.columns:
        kayitli_isimler = [str(i).strip() for i in df_veri['İsim'].tolist() if str(i).strip() != '']
    else:
        kayitli_isimler = []
        # Eğer İsim sütunu bulunamazsa uyarı vermemesi için boş liste atadık,
        # ancak aşağıda kullanıcıya bilgi vereceğiz.

    atlananlar_temiz = [str(i).strip() for i in atlanan_list]

    # Listeyi tara
    tum_veriler = w_liste.get_all_values() 
    
    # Excel yapısına göre veri tarama (3. satırdan başlar)
    for row in tum_veriler[2:]: 
        if len(row) < 5: continue
        
        aday_isim = str(row[2]).strip() # C Sütunu
        aday_tarih = str(row[4]).strip() # E Sütunu
        
        if not aday_isim or aday_isim.lower() in ['nan', '', 'none', 'adı soyadı', 'sütun3']: 
            continue
        
        # Eğer kayıtlı değilse ve atlanmamışsa
        if (aday_isim not in kayitli_isimler) and (aday_isim not in atlananlar_temiz):
            siradaki_isim = aday_isim
            siradaki_tarih_str = aday_tarih
            bulundu_mesaji = f"Sıradaki Hasta: **{siradaki_isim}** ({siradaki_tarih_str})"
            break

    # --- BİLGİ KUTUSU ---
    if siradaki_isim:
        st.info(f"🔔 {bulundu_mesaji}")
        
        c1, c2, c3 = st.columns([1, 1, 3])
        
        if c1.button("⬇️ Bilgileri Doldur"):
            st.session_state.form_isim = siradaki_isim
            try:
                tarih_temiz = siradaki_tarih_str.split(' ')[0]
                for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'):
                    try:
                        st.session_state.form_tarih = datetime.strptime(tarih_temiz, fmt)
                        break
                    except: pass
            except: pass
            st.rerun()
            
        if c2.button("🚫 Pas Geç"):
            w_atlanan.append_row([siradaki_isim, siradaki_tarih_str])
            st.success(f"{siradaki_isim} atlandı.")
            st.rerun()
    
    elif not kayitli_isimler and 'İsim' not in df_veri.columns:
         st.warning("⚠️ Veri sayfasında 'İsim' sütunu bulunamadı. Lütfen Google Sheet başlıklarını (2. satır) kontrol et.")

    # --- FORM ALANI ---
    with st.form("main_form", clear_on_submit=True):
        st.subheader("📝 Veri Girişi")
        col1, col2 = st.columns(2)
        isim = col1.text_input("İsim", value=st.session_state.form_isim)
        tarih = col2.date_input("Tarih", value=st.session_state.form_tarih)
        
        col3, col4, col5 = st.columns(3)
        yas = col3.number_input("Yaş", step=1, min_value=0)
        cinsiyet = col4.selectbox("Cinsiyet", ["E", "K", "Belirtilmemiş"])
        bolum = col5.text_input("Yatırılan Bölüm")

        st.markdown("---")
        
        submitted = st.form_submit_button("✅ KAYDET")
        
        if submitted:
            if not isim:
                st.warning("Lütfen bir isim girin.")
            else:  # <--- HATA BURADAYDI, ŞİMDİ DÜZELTİLDİ
                # Veri sekmesine eklenecek satır
                yeni_satir = [
                    "", # A Sütunu (Boş)
                    str(tarih), # B
                    isim,       # C
                    yas,        # D
                    cinsiyet,   # E
                    bolum       # F
                ]
                
                try:
                    w_veri.append_row(yeni_satir)
                    st.success(f"✅ {isim} başarıyla kaydedildi!")
                    st.session_state.form_isim = ""
                except Exception as e:
                    st.error(f"Kayıt hatası: {e}")

except Exception as e:
    st.error(f"Sistem Hatası: {e}")
