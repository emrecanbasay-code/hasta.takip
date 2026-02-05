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
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏥 Dikey Hızlı Veri Girişi (v3.0 - Butonlu)")

# --- CHECKBOX LİSTESİ ---
CHECKBOX_LIST = [
    "1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü", "Servis",
    "HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER",
    "Entübasyon", "İnotrop", "Mükerrer tetkik Ya da tedavi istemi", 
    "Kesin tanı koyulamaması", "8 saati aşıp yatmaması", "Birden fazla kliniği ilgilendirmesi",
    "KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı", "MALİYET", 
    "Cr", "Ct", "Mr", "Usg",
    "Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb", "Plastik", "Göz", 
    "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji", "Göğüs H.", "Enfeksiyon H.", 
    "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji",
    "08.00-16.00", "16.00-24.00", "00.00-08.00",
    "DEVİR", "Taburcu", "Ölüm", "T. RED"
]

# --- BAĞLANTI ---
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_data_v3():
    try:
        client = get_connection()
        sh = client.open(SHEET_ADI)
        w_veri = sh.worksheet("Veri")
        w_liste = sh.worksheet("Liste")
        w_atlanan = sh.worksheet("Atlananlar")
        
        data_veri = w_veri.get_all_values()
        headers = []
        processed_names = []
        if len(data_veri) > 1:
            headers = [h.strip() for h in data_veri[1]] # Başlıklardaki boşlukları temizle
            processed_names = [row[4].strip() for row in data_veri[2:] if len(row) > 4]

        data_atlanan = w_atlanan.get_all_values()
        skipped_names = [row[0].strip() for row in data_atlanan if len(row) > 0]

        data_liste = w_liste.get_all_values()
        
        return w_veri, w_atlanan, headers, data_liste, processed_names, skipped_names
        
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None, None, [], [], [], []

# --- SESSION STATE (Form Verilerini Tutmak İçin) ---
if 'form_isim' not in st.session_state: st.session_state['form_isim'] = ""
if 'form_karar' not in st.session_state: st.session_state['form_karar'] = "0"
if 'form_transfer' not in st.session_state: st.session_state['form_transfer'] = "0"
if 'form_tarih' not in st.session_state: st.session_state['form_tarih'] = datetime.now()

# --- ANA AKIŞ ---
w_veri, w_atlanan, headers, ham_liste_verisi, processed_names, skipped_names = get_data_v3()

if w_veri:
    
    # --- GERİ AL BUTONU (SIDEBAR) ---
    with st.sidebar:
        st.header("⚙️ İşlemler")
        if st.button("⏪ SON KAYDI GERİ AL", use_container_width=True):
            try:
                all_values = w_veri.get_all_values()
                if len(all_values) > 2:
                    last_index = len(all_values)
                    silinen_kisi = all_values[-1][4]
                    w_veri.delete_rows(last_index)
                    st.success(f"Geri Alındı: {silinen_kisi}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Silinecek kayıt yok.")
            except Exception as e:
                st.error(f"Hata: {e}")

    # --- SEÇİM ALANI ---
    with st.container():
        yapilacaklar = []
        for row in ham_liste_verisi[3:]:
            if len(row) > 8:
                isim = str(row[4]).strip()
                tarih = str(row[6]).strip()
                yatis_saati = str(row[8]).strip() if len(row) > 8 else "-"
                sure_karar = str(row[10]).strip() if len(row) > 10 else "0"
                sure_transfer = str(row[11]).strip() if len(row) > 11 else "0"
                
                if isim and "isim" not in isim.lower(): 
                    if isim not in processed_names and isim not in skipped_names:
                        yapilacaklar.append({
                            "isim": isim, 
                            "tarih": tarih,
                            "yatis_saati": yatis_saati,
                            "sure_karar": sure_karar,
                            "sure_transfer": sure_transfer
                        })
        
        if not yapilacaklar:
            st.success("🎉 Tüm hastalar bitti!")
            st.stop()
            
        st.info(f"Kalan Hasta: **{len(yapilacaklar)}**")
        
        secenekler = [f"{h['isim']} | {h['tarih']}" for h in yapilacaklar]
        secilen_str = st.selectbox("👇 Sıradaki Hasta:", secenekler)
        
        # Seçilen verileri bul
        secilen_isim = secilen_str.split(" | ")[0]
        secilen_data = next((item for item in yapilacaklar if item["isim"] == secilen_isim), None)
        raw_tarih = secilen_data["tarih"]
        val_saat = secilen_data["yatis_saati"]
        val_karar = secilen_data["sure_karar"]
        val_transfer = secilen_data["sure_transfer"]

        # YATIŞ SAATİ BİLGİSİ
        st.warning(f"⏰ **Yatış Verilme Saati:** {val_saat}")

        # --- VERİLERİ DOLDUR BUTONU ---
        # Bu buton tıklandığında Session State güncellenir ve form o verilerle dolar
        if st.button("⬇️ VERİLERİ GETİR / DOLDUR", type="primary", use_container_width=True):
            st.session_state['form_isim'] = secilen_isim
            st.session_state['form_karar'] = val_karar
            st.session_state['form_transfer'] = val_transfer
            
            # Tarih Çevirme İşlemi
            t_obj = datetime.now()
            try:
                t_clean = raw_tarih.split(' ')[0]
                for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y.%m.%d'):
                    try: 
                        t_obj = datetime.strptime(t_clean, fmt)
                        break
                    except: pass
            except: pass
            st.session_state['form_tarih'] = t_obj
            
            st.rerun() # Sayfayı yenile ki form güncel verilerle açılsın

    st.markdown("---")
    
    # --- FORM ---
    input_values = {}
    
    with st.form("dikey_form", clear_on_submit=False):
        st.write(f"### 📋 Kayıt Ekranı")
        
        for i, baslik in enumerate(headers):
            if not baslik: continue
            
            # Başlık Temizliği (Checkbox eşleşmesi için kritik)
            baslik_clean = baslik.strip() # Boşlukları sil
            baslik_lower = baslik_clean.lower()
            
            c1, c2 = st.columns([1.5, 3])
            c1.markdown(f"<div class='etiket-box'>{baslik_clean}:</div>", unsafe_allow_html=True)
            
            key_name = f"in_{i}_{baslik_clean}"
            
            with c2:
                # 1. CHECKBOX KONTROLÜ (Daha esnek hale getirildi)
                # Listede var mı diye bakarken hem listedekini hem başlıktakini temizliyoruz.
                if baslik_clean in [x.strip() for x in CHECKBOX_LIST]: 
                    chk = st.checkbox("Evet / Var", key=key_name)
                    input_values[baslik] = 1 if chk else 0
                
                # 2. İSİM (Otomatik Buton ile Dolar)
                elif any(x in baslik_lower for x in ['isim', 'adı soyadı', 'hasta adı']):
                    input_values[baslik] = st.text_input("İsim", key="form_isim_input", value=st.session_state['form_isim'], label_visibility="collapsed")
                
                # 3. TARİH (Otomatik Buton ile Dolar)
                elif "tarih" in baslik_lower:
                    input_values[baslik] = st.date_input("Tarih", key="form_tarih_input", value=st.session_state['form_tarih'], label_visibility="collapsed")
                
                # 4. YATIŞ KARAR SÜRESİ (Otomatik Buton ile Dolar)
                elif "karar" in baslik_lower and "süre" in baslik_lower:
                     input_values[baslik] = st.text_input("Süre", key="form_karar_input", value=st.session_state['form_karar'], label_visibility="collapsed")

                # 5. TRANSFER SÜRESİ (Otomatik Buton ile Dolar)
                elif ("transfer" in baslik_lower or "transver" in baslik_lower) and "süre" in baslik_lower:
                     input_values[baslik] = st.text_input("Süre", key="form_transfer_input", value=st.session_state['form_transfer'], label_visibility="collapsed")
                
                # 6. Cinsiyet
                elif "cinsiyet" in baslik_lower:
                    input_values[baslik] = st.selectbox("Cinsiyet", ["", "E", "K"], key=key_name, label_visibility="collapsed")
                
                # 7. Sayısal Alanlar
                elif any(x in baslik_lower for x in ['yaş', 'ateş', 'nabız', 'tansiyon', 'spo2']):
                    input_values[baslik] = st.number_input("Değer", value=0.0, step=1.0, format="%.2f", key=key_name, label_visibility="collapsed")
                
                # 8. Not Alanları
                elif any(x in baslik_lower for x in ['açıklama', 'not']):
                    input_values[baslik] = st.text_area("Not", height=68, key=key_name, label_visibility="collapsed")
                
                # 9. Diğerleri
                else:
                    input_values[baslik] = st.text_input("Sonuç", value="0", key=key_name, label_visibility="collapsed")
            
            st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)

        st.markdown("---")
        
        col_submit, col_pass = st.columns([3, 1])
        kaydet_btn = col_submit.form_submit_button("✅ KAYDET", type="primary", use_container_width=True)
    
    pas_gec_btn = st.button("🚫 BU HASTAYI PAS GEÇ", use_container_width=True)

    if kaydet_btn:
        try:
            yeni_satir = []
            for baslik in headers:
                if not baslik:
                    yeni_satir.append("")
                else:
                    val = input_values.get(baslik, "")
                    if isinstance(val, (datetime, pd.Timestamp)): val = val.strftime("%d.%m.%Y")
                    yeni_satir.append(str(val))
            
            w_veri.append_row(yeni_satir)
            st.success(f"✅ {st.session_state['form_isim']} başarıyla kaydedildi!")
            
            # Kayıttan sonra form temizlensin istersen bunları sıfırlayabilirsin:
            # st.session_state['form_isim'] = ""
            
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Kayıt Hatası: {e}")

    if pas_gec_btn:
        try:
            w_atlanan.append_row([secilen_isim, secilen_tarih_str])
            st.warning(f"⏩ {secilen_isim} pas geçildi.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")
