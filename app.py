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

# --- SESSION STATE ---
if 'form_vals' not in st.session_state: st.session_state.form_vals = {}

# --- ANA PROGRAM ---
w_veri, w_atlanan, headers, tum_veriler, atlanan_list = get_data_safe()

if w_veri:
    
    # 1. SIRADAKİ HASTAYI BULMA
    siradaki_isim = None
    siradaki_tarih_str = None
    bulundu_mesaji = "✅ Liste tamamlandı!"
    
    atlananlar_temiz = [str(i).strip() for i in atlanan_list]
    
    if debug_mode:
        st.sidebar.warning("📊 Ham Veri (Kontrol):")
        st.sidebar.write(tum_veriler[:6])

    # Liste tarama (3. satırdan başla - index 3)
    for row in tum_veriler[3:]:
        if len(row) < 7: continue 
        
        try:
            aday_isim = str(row[4]).strip()  # E Sütunu (İsim)
            aday_tarih = str(row[6]).strip() # G Sütunu (Tarih)
        except:
            continue
            
        if not aday_isim or len(aday_isim) < 3 or "Sütun" in aday_isim: 
            continue
        
        if aday_isim not in atlananlar_temiz:
            siradaki_isim = aday_isim
            siradaki_tarih_str = aday_tarih
            bulundu_mesaji = f"Sıradaki Hasta: **{siradaki_isim}** ({siradaki_tarih_str})"
            break

    # 2. BİLGİ BUTONLARI
    if siradaki_isim:
        st.info(f"🔔 {bulundu_mesaji}")
        col_btn1, col_btn2 = st.columns([1, 4])
        
        if col_btn1.button("⬇️ Bilgileri Getir"):
            # Tarihi parse et
            tarih_val = datetime.now()
            try:
                t_str = siradaki_tarih_str.split(' ')[0]
                for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
                    try:
                        tarih_val = datetime.strptime(t_str, fmt)
                        break
                    except: pass
            except: pass
            
            # Değerleri hafızaya al
            st.session_state.form_vals['Auto_Isim'] = siradaki_isim
            st.session_state.form_vals['Auto_Tarih'] = tarih_val
            st.rerun()

        if col_btn2.button("🚫 Pas Geç"):
            w_atlanan.append_row([siradaki_isim, siradaki_tarih_str])
            st.success("Hasta atlandı.")
            st.rerun()
    
    st.markdown("---")

    # 3. VERİ GİRİŞ FORMU
    with st.form("main_form", clear_on_submit=True):
        st.subheader("📝 Veri Girişi")
        
        form_inputs = {}
        cols = st.columns(3)
        
        # --- ÖNEMLİ: ENUMERATE KULLANIYORUZ (SIRA NUMARASINA GÖRE İŞLEM) ---
        # i = 0 (A sütunu), i = 4 (E sütunu - İsim), i = 6 (G sütunu - Tarih)
        
        for i, baslik in enumerate(headers):
            # Boş başlık varsa atla
            if not baslik.strip(): 
                form_inputs[f"col_{i}"] = "" # Yer tutucu
                continue
            
            c = cols[i % 3] # 3 sütunlu düzen
            key_name = f"input_{i}_{baslik}"
            
            # --- KURAL 1: İSİM ALANI (SIRA 4) ---
            if i == 4: 
                # Session'dan gelen isim varsa onu kullan, yoksa başlığı kullanma
                val = st.session_state.form_vals.get('Auto_Isim', "")
                form_inputs[baslik] = c.text_input(f"{baslik} (İsim)", value=val, key=key_name)
                
            # --- KURAL 2: TARİH ALANI (SIRA 6) ---
            elif i == 6:
                val = st.session_state.form_vals.get('Auto_Tarih', datetime.now())
                form_inputs[baslik] = c.date_input(f"{baslik} (Tarih)", value=val, key=key_name)
            
            # --- KURAL 3: CİNSİYET ---
            elif "cinsiyet" in baslik.lower():
                form_inputs[baslik] = c.selectbox(baslik, ["", "E", "K"], key=key_name)
                
            # --- KURAL 4: EVET/HAYIR ---
            elif baslik in ["HT", "DM", "KOAH", "KBY", "KAH", "AF", "SVH", "Malignite"]:
                check = c.checkbox(baslik, key=key_name)
                form_inputs[baslik] = 1 if check else 0
            
            # --- KURAL 5: SAYISAL (Ateş, Tansiyon vs.) ---
            elif any(x in baslik.lower() for x in ['yaş', 'ateş', 'nabız', 'tansiyon', 'spo2']):
                form_inputs[baslik] = c.number_input(baslik, value=0.0, step=1.0, format="%.2f", key=key_name)
                
            # --- KURAL 6: DİĞER HER ŞEY (0 OLARAK GELSİN) ---
            else:
                # Bölüm, Yatış gibi metinler boş kalsın
                if any(x in baslik.lower() for x in ['bölüm', 'yatış', 'açıklama', 'not']):
                    form_inputs[baslik] = c.text_input(baslik, value="", key=key_name)
                else:
                    # Laboratuvarlar 0 gelsin
                    form_inputs[baslik] = c.text_input(baslik, value="0", key=key_name)

        st.markdown("---")
        submitted = st.form_submit_button("✅ KESİN KAYDET")
        
        if submitted:
            yeni_satir = []
            
            # Sırayla verileri topla
            for i, baslik in enumerate(headers):
                if not baslik.strip():
                    yeni_satir.append("") # Boş sütun
                else:
                    raw_val = form_inputs.get(baslik, "")
                    
                    # Tarih objesini string'e çevir
                    if isinstance(raw_val, (datetime, pd.Timestamp)):
                        final_val = raw_val.strftime("%d.%m.%Y")
                    else:
                        final_val = str(raw_val)
                        
                    yeni_satir.append(final_val)
            
            try:
                # Veriyi gönder
                w_veri.append_row(yeni_satir)
                st.success(f"✅ Başarıyla Kaydedildi! (İsim: {yeni_satir[4]})")
                
                # Hafızayı temizle
                st.session_state.form_vals = {}
                
            except Exception as e:
                st.error(f"Kayıt Hatası: {e}")

else:
    st.warning("Veritabanı bağlantısı yok.")
