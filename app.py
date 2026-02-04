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
st.sidebar.header("🔧 Ayarlar")
debug_mode = st.sidebar.checkbox("Hata Ayıklama Modu (Listeyi Gör)")

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# --- VERİLERİ ÇEKME ---
def get_data_safe():
    try:
        client = get_connection()
        sh = client.open(SHEET_ADI)
        w_veri = sh.worksheet("Veri")
        w_liste = sh.worksheet("Liste")
        w_atlanan = sh.worksheet("Atlananlar")
        
        # Başlıkları al
        data_veri = w_veri.get_all_values()
        headers = []
        if len(data_veri) > 1:
            headers = data_veri[1] # 2. Satır başlıklar
        
        # Liste verisi
        data_liste = w_liste.get_all_values()
        
        # Atlananlar
        atlanan_list = w_atlanan.col_values(1)
        
        return w_veri, w_atlanan, headers, data_liste, atlanan_list
    except Exception as e:
        st.error(f"Google Sheets Bağlantı Hatası: {e}")
        return None, None, [], [], []

# --- SESSION STATE BAŞLATMA ---
if 'form_vals' not in st.session_state: st.session_state.form_vals = {}

# --- ANA PROGRAM AKIŞI ---
w_veri, w_atlanan, headers, tum_veriler, atlanan_list = get_data_safe()

if w_veri: # Eğer bağlantı başarılıysa devam et
    
    # 1. SIRADAKİ HASTAYI BUL
    siradaki_isim = None
    siradaki_tarih_str = None
    bulundu_mesaji = "✅ Liste tamamlandı!"
    
    # İsimlerin olduğu sütunu bulmak için hazırlık
    atlananlar_temiz = [str(i).strip() for i in atlanan_list]
    
    # Kayıtlı olanları 'Veri' sekmesinden kontrol etmemiz lazım ama
    # performans için şimdilik sadece atlananlara ve sıraya bakalım.
    # Daha sağlam kontrol için Veri sekmesindeki isim sütunu da çekilebilir.
    
    if debug_mode:
        st.sidebar.warning("📊 Liste İlk 5 Satır:")
        st.sidebar.write(tum_veriler[:5])

    # Döngü (3. satırdan başla)
    for row in tum_veriler[2:]:
        if len(row) < 5: continue
        
        # --- DİKKAT: SÜTUN AYARI BURADA ---
        # Senin dosyanda İsim 5. sütun (index 4), Tarih 7. sütun (index 6) görünüyordu.
        # Eğer yine boş gelirse buradaki sayıları değiştir: row[X]
        try:
            aday_isim = str(row[4]).strip()  
            aday_tarih = str(row[6]).strip() 
        except:
            continue
            
        if not aday_isim or len(aday_isim) < 3: continue
        
        # Eğer atlananlarda yoksa (Basit mantık)
        if aday_isim not in atlananlar_temiz:
            # Not: Zaten kaydedilmiş mi kontrolünü eklemek için
            # Veri sayfasındaki isimleri de çekip bakmak gerekir.
            siradaki_isim = aday_isim
            siradaki_tarih_str = aday_tarih
            bulundu_mesaji = f"Sıradaki Hasta: **{siradaki_isim}** ({siradaki_tarih_str})"
            break

    # 2. BİLGİ KUTUSU VE BUTONLAR
    if siradaki_isim:
        st.info(f"🔔 {bulundu_mesaji}")
        col_btn1, col_btn2 = st.columns([1, 4])
        
        if col_btn1.button("⬇️ Bilgileri Getir"):
            # Tarihi ayarla
            tarih_val = datetime.now()
            try:
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

        if col_btn2.button("🚫 Pas Geç"):
            w_atlanan.append_row([siradaki_isim, siradaki_tarih_str])
            st.success("Hasta atlandı.")
            st.rerun()
    
    st.markdown("---")

    # 3. OTOMATİK FORM OLUŞTURMA
    with st.form("main_form", clear_on_submit=True):
        st.subheader("📝 Veri Girişi")
        
        form_inputs = {}
        cols = st.columns(3)
        idx = 0
        
        # Başlıkları dön ve input oluştur
        for baslik in headers:
            if not baslik.strip(): continue
            
            c = cols[idx % 3]
            idx += 1
            
            # Varsayılan değer
            val = st.session_state.form_vals.get(baslik, None)
            
            key_name = f"input_{baslik}_{idx}" # Benzersiz ID
            
            if "tarih" in baslik.lower():
                default_date = val if val else datetime.now()
                form_inputs[baslik] = c.date_input(baslik, value=default_date, key=key_name)
            
            elif any(x in baslik.lower() for x in ['yaş', 'ateş', 'nabız', 'tansiyon', 'spo2']):
                form_inputs[baslik] = c.number_input(baslik, step=1.0, format="%.2f", key=key_name)
            
            elif "cinsiyet" in baslik.lower():
                form_inputs[baslik] = c.selectbox(baslik, ["", "E", "K"], key=key_name)
                
            elif baslik in ["HT", "DM", "KOAH", "KBY", "KAH", "AF", "SVH", "Malignite"]:
                check = c.checkbox(baslik, key=key_name)
                form_inputs[baslik] = 1 if check else 0
            
            else:
                default_text = val if val else ""
                form_inputs[baslik] = c.text_input(baslik, value=default_text, key=key_name)

        st.markdown("---")
        submitted = st.form_submit_button("✅ KAYDET")
        
        if submitted:
            # Kayıt işlemi
            yeni_satir = []
            for baslik in headers:
                if baslik.strip():
                    deger = form_inputs.get(baslik, "")
                    # Tarih formatı düzeltme
                    if isinstance(deger, (datetime, pd.Timestamp)):
                        deger = deger.strftime("%d.%m.%Y")
                    # Sayı formatı (0 yerine '0' gitmesi için string yapabiliriz gerekirse)
                    yeni_satir.append(deger)
                else:
                    yeni_satir.append("")
            
            try:
                w_veri.append_row(yeni_satir)
                st.success("✅ Kayıt Başarılı!")
                st.session_state.form_vals = {} # Formu temizle
                # Sayfayı yenilemeye gerek yok, clear_on_submit hallediyor
            except Exception as e:
                st.error(f"Kayıt sırasında hata oluştu: {e}")

else:
    st.warning("Veritabanına bağlanılamadı. Lütfen sayfayı yenileyin.")
