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

st.title("🏥 Dikey Hızlı Veri Girişi (v5.0)")

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

def get_data_fix():
    try:
        client = get_connection()
        sh = client.open(SHEET_ADI)
        w_veri = sh.worksheet("Veri")      # Hedef
        w_liste = sh.worksheet("Liste")    # Kaynak
        w_atlanan = sh.worksheet("Atlananlar")
        
        # --- BAŞLIKLARI DÜZELTME (VERİ SAYFASI) ---
        # Veri sayfasının ilk 2 satırını çekip birleştiriyoruz.
        # Böylece hem 1. satırdaki "Tarih" hem 2. satırdaki "İsim" yakalanacak.
        all_data_veri = w_veri.get_all_values()
        row1 = all_data_veri[0] 
        row2 = all_data_veri[1] 
        
        headers = []
        max_len = max(len(row1), len(row2))
        
        for i in range(max_len):
            val1 = row1[i].strip() if i < len(row1) else ""
            val2 = row2[i].strip() if i < len(row2) else ""
            
            # Eğer 2. satır doluysa onu başlık yap (Örn: İsim, Yaş)
            # Eğer 2. satır boşsa 1. satırı al (Örn: Tarih, Sıra No)
            if val2:
                headers.append(val2)
            else:
                headers.append(val1)
        
        # --- LİSTE VERİLERİNİ ÇEKME ---
        data_liste = w_liste.get_all_values()
        
        # --- ATLANANLAR ---
        data_atlanan = w_atlanan.get_all_values()
        skipped_names = [row[0].strip() for row in data_atlanan if len(row) > 0]
        
        # İşlenmiş isimleri Veri sayfasının "İsim" sütunundan (kabaca 4. sütun / index 3) bulmaya çalışalım
        # Headers içinde "İsim" kaçıncı sırada bulup oradan kontrol etmek en garantisi
        try:
            isim_index = -1
            for idx, h in enumerate(headers):
                if "isim" in h.lower():
                    isim_index = idx
                    break
            
            if isim_index != -1:
                 processed_names = [row[isim_index].strip() for row in all_data_veri[2:] if len(row) > isim_index]
            else:
                 processed_names = []
        except:
            processed_names = []

        return w_veri, w_atlanan, headers, data_liste, processed_names, skipped_names
        
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None, None, [], [], [], []

# --- SESSION STATE (Form Verilerini Hafızada Tut) ---
if 'form_isim' not in st.session_state: st.session_state['form_isim'] = ""
if 'form_karar' not in st.session_state: st.session_state['form_karar'] = "0"
if 'form_transfer' not in st.session_state: st.session_state['form_transfer'] = "0"
if 'form_tarih' not in st.session_state: st.session_state['form_tarih'] = datetime.now()

# --- ANA AKIŞ ---
w_veri, w_atlanan, headers, ham_liste_verisi, processed_names, skipped_names = get_data_fix()

if w_veri:
    
    # --- GERİ AL BUTONU ---
    with st.sidebar:
        st.header("⚙️ İşlemler")
        if st.button("⏪ SON KAYDI GERİ AL", use_container_width=True):
            try:
                all_values = w_veri.get_all_values()
                if len(all_values) > 2:
                    w_veri.delete_rows(len(all_values))
                    st.success("Son kayıt silindi.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Silinecek kayıt yok.")
            except Exception as e:
                st.error(f"Hata: {e}")

    # --- SEÇİM ALANI ---
    with st.container():
        yapilacaklar = []
        # Liste sayfasının 4. satırından (Index 3) itibaren tara
        for row in ham_liste_verisi[3:]:
            if len(row) > 10: # Satır dolu mu kontrolü
                # --- DOSYANA GÖRE SÜTUN HARİTALAMA ---
                # E Sütunu (Index 4) -> İsim
                # G Sütunu (Index 6) -> Tarih
                # K Sütunu (Index 10) -> Yatış Karar Süresi
                # L Sütunu (Index 11) -> Transfer Süresi
                
                isim = str(row[4]).strip()
                tarih = str(row[6]).strip()
                sure_karar = str(row[10]).strip() 
                sure_transfer = str(row[11]).strip()
                
                if isim and "isim" not in isim.lower(): 
                    if isim not in processed_names and isim not in skipped_names:
                        yapilacaklar.append({
                            "isim": isim, 
                            "tarih": tarih,
                            "sure_karar": sure_karar,
                            "sure_transfer": sure_transfer
                        })
        
        if not yapilacaklar:
            st.success("🎉 Liste Tamamlandı!")
            st.stop()
            
        st.info(f"Kalan Hasta: **{len(yapilacaklar)}**")
        
        secenekler = [f"{h['isim']} | {h['tarih']}" for h in yapilacaklar]
        secilen_str = st.selectbox("👇 Sıradaki Hasta:", secenekler)
        
        # Seçilen veriyi bul
        secilen_isim = secilen_str.split(" | ")[0]
        secilen_data = next((item for item in yapilacaklar if item["isim"] == secilen_isim), None)
        
        raw_tarih = secilen_data["tarih"]
        val_karar = secilen_data["sure_karar"]
        val_transfer = secilen_data["sure_transfer"]

        # --- VERİLERİ GETİR BUTONU ---
        if st.button("⬇️ VERİLERİ GETİR / DOLDUR", type="primary", use_container_width=True):
            st.session_state['form_isim'] = secilen_isim
            st.session_state['form_karar'] = val_karar
            st.session_state['form_transfer'] = val_transfer
            
            # Tarih Çevirme (Excel formatına göre)
            t_obj = datetime.now()
            try:
                # Sadece tarihi al, saati at (2022-09-26 18:11:27 -> 2022-09-26)
                t_clean = raw_tarih.split(' ')[0]
                for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y.%m.%d'):
                    try: 
                        t_obj = datetime.strptime(t_clean, fmt)
                        break
                    except: pass
            except: pass
            st.session_state['form_tarih'] = t_obj
            
            st.rerun()

    st.markdown("---")
    
    # --- FORM OLUŞTURMA ---
    input_values = {}
    
    with st.form("dikey_form", clear_on_submit=False):
        st.write(f"### 📋 Kayıt Ekranı: {st.session_state['form_isim']}")
        
        for i, baslik in enumerate(headers):
            if not baslik or baslik.strip() == "": 
                continue
            
            # --- BAŞLIK NORMALİZASYONU ---
            # Excel'deki \n karakterlerini ve Türkçe harfleri düzeltiyoruz
            baslik_clean = baslik.strip().replace("\n", " ")
            baslik_lower = baslik_clean.replace("İ", "i").replace("I", "ı").lower()
            
            c1, c2 = st.columns([1.5, 3])
            c1.markdown(f"<div class='etiket-box'>{baslik_clean}:</div>", unsafe_allow_html=True)
            
            key_name = f"in_{i}_{baslik_clean}"
            
            with c2:
                # 1. CHECKBOX
                if baslik_clean in [x.strip() for x in CHECKBOX_LIST]: 
                    chk = st.checkbox("Evet / Var", key=key_name)
                    input_values[baslik] = 1 if chk else 0
                
                # 2. İSİM (Eşleşme)
                elif any(x in baslik_lower for x in ['isim', 'adı soyadı', 'hasta adı']):
                    input_values[baslik] = st.text_input("İsim", key="form_isim_input", value=st.session_state['form_isim'], label_visibility="collapsed")
                
                # 3. TARİH (Eşleşme)
                elif "tarih" in baslik_lower:
                    input_values[baslik] = st.date_input("Tarih", key="form_tarih_input", value=st.session_state['form_tarih'], label_visibility="collapsed")
                
                # 4. YATIŞ KARAR SÜRESİ
                # "karar" ve "süre" kelimeleri varsa, "Verileri Getir"den gelen değeri yaz
                elif "karar" in baslik_lower and "süre" in baslik_lower:
                     input_values[baslik] = st.text_input("Süre (dk)", key="form_karar_input", value=st.session_state['form_karar'], label_visibility="collapsed")

                # 5. TRANSFER SÜRESİ
                # "transfer" veya "transver" ve "süre" varsa
                elif ("transfer" in baslik_lower or "transver" in baslik_lower) and "süre" in baslik_lower:
                     input_values[baslik] = st.text_input("Süre (dk)", key="form_transfer_input", value=st.session_state['form_transfer'], label_visibility="collapsed")
                
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
        kaydet_btn = col_submit.form_submit_button("✅ VERİ SAYFASINA GÖNDER", type="primary", use_container_width=True)
    
    pas_gec_btn = st.button("🚫 BU HASTAYI PAS GEÇ", use_container_width=True)

    # --- KAYIT FONKSİYONU ---
    if kaydet_btn:
        try:
            yeni_satir = []
            for baslik in headers:
                if not baslik or baslik.strip() == "":
                    yeni_satir.append("")
                else:
                    val = input_values.get(baslik, "")
                    if isinstance(val, (datetime, pd.Timestamp)): val = val.strftime("%d.%m.%Y")
                    yeni_satir.append(str(val))
            
            w_veri.append_row(yeni_satir)
            st.success(f"✅ {st.session_state['form_isim']} Veri sayfasına eklendi!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Kayıt Hatası: {e}")

    # --- PAS GEÇME FONKSİYONU ---
    if pas_gec_btn:
        try:
            w_atlanan.append_row([secilen_isim, datetime.now().strftime("%Y-%m-%d")])
            st.warning(f"⏩ {secilen_isim} atlananlara eklendi.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")
