import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# --- AYARLAR ---
SHEET_ADI = "Hasta_Takip_Sistemi"

st.set_page_config(page_title="Pro Hasta Takip", layout="centered", page_icon="🏥") 

# --- CSS ---
st.markdown("""
<style>
    .stMarkdown { margin-bottom: -10px; }
    div[data-testid="column"] { align-items: center; display: flex; }
    .etiket-box {
        font-weight: bold; font-size: 14px; color: #1f77b4;
        text-align: right; padding-right: 15px; width: 100%;
    }
    .stTextInput, .stNumberInput, .stDateInput, .stSelectbox { width: 100%; }
    .row-container { padding: 5px 0; border-bottom: 1px solid #f0f2f6; }
    div[data-testid="stCheckbox"] { display: flex; align-items: center; }
</style>
""", unsafe_allow_html=True)

st.title("🏥 Dikey Hızlı Veri Girişi (v7.0 - Liste Kaynaklı)")

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

def get_data_v7():
    try:
        client = get_connection()
        sh = client.open(SHEET_ADI)
        w_veri = sh.worksheet("Veri")      # Hedef (Format buradan alınır)
        w_liste = sh.worksheet("Liste")    # Kaynak (İsim/Tarih buradan alınır)
        w_atlanan = sh.worksheet("Atlananlar")
        
        # --- BAŞLIKLARI VERİ SAYFASINDAN OLUŞTUR ---
        # 1. ve 2. satırı birleştiriyoruz (Tarih 1'de, İsim 2'de olabilir)
        all_veri = w_veri.get_all_values()
        if len(all_veri) < 2: return None, None, [], [], [], []
        
        row1 = all_veri[0]
        row2 = all_veri[1]
        
        headers = []
        max_col = max(len(row1), len(row2))
        
        for i in range(max_col):
            v1 = row1[i].strip() if i < len(row1) else ""
            v2 = row2[i].strip() if i < len(row2) else ""
            # Öncelik 2. satırda, boşsa 1. satırı al
            header_text = v2 if v2 else v1
            headers.append(header_text)

        # --- LİSTE VERİLERİNİ ÇEK ---
        data_liste = w_liste.get_all_values()
        
        # --- ATLANANLAR ---
        data_atlanan = w_atlanan.get_all_values()
        skipped_names = [row[0].strip() for row in data_atlanan if len(row) > 0]
        
        # İşlenenleri Veri sayfasındaki İsim sütunundan bul (Yaklaşık 4. index)
        processed_names = []
        if len(all_veri) > 2:
            # Başlıklarda "İsim" nerede geçiyor bulalım
            isim_col_index = 3 # Varsayılan (D/E sütunu civarı)
            for idx, h in enumerate(headers):
                if "isim" in h.lower().replace("İ","i"):
                    isim_col_index = idx
                    break
            
            for row in all_veri[2:]:
                if len(row) > isim_col_index:
                    processed_names.append(row[isim_col_index].strip())

        return w_veri, w_atlanan, headers, data_liste, processed_names, skipped_names
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        return None, None, [], [], [], []

# --- SESSION STATE (Değerleri Burada Tutuyoruz) ---
if 'form_vals' not in st.session_state:
    st.session_state['form_vals'] = {
        'isim': '',
        'tarih': datetime.now(),
        'karar': '0',
        'transfer': '0'
    }

# --- ANA AKIŞ ---
w_veri, w_atlanan, headers, ham_liste_verisi, processed_names, skipped_names = get_data_v7()

if w_veri:
    
    # --- GERİ AL ---
    with st.sidebar:
        st.header("⚙️ İşlemler")
        if st.button("⏪ SON KAYDI GERİ AL", use_container_width=True):
            try:
                # Başlıklar (2 satır) hariç veri varsa sil
                current_rows = len(w_veri.get_all_values())
                if current_rows > 2:
                    w_veri.delete_rows(current_rows)
                    st.success("Son satır silindi.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Silinecek kayıt yok.")
            except Exception as e: st.error(str(e))

    # --- LİSTEDEN SEÇİM ALANI ---
    with st.container():
        yapilacaklar = []
        
        # Liste sayfasını tarıyoruz (3. indexten başla / 4. satır)
        for row in ham_liste_verisi[3:]:
            if len(row) > 10:
                # LİSTE SAYFASI SÜTUN YAPISI:
                # E (Index 4) -> İsim
                # G (Index 6) -> Tarih (2022-09-26)
                # I (Index 8) -> Yatış Saati
                # K (Index 10) -> Karar Süresi
                # L (Index 11) -> Transfer Süresi
                
                isim_raw = str(row[4]).strip()
                tarih_raw = str(row[6]).strip()
                saat_raw = str(row[8]).strip() if len(row) > 8 else "-"
                karar_raw = str(row[10]).strip()
                transfer_raw = str(row[11]).strip()
                
                if isim_raw and "isim" not in isim_raw.lower():
                    if isim_raw not in processed_names and isim_raw not in skipped_names:
                        yapilacaklar.append({
                            "isim": isim_raw, 
                            "tarih": tarih_raw, 
                            "saat": saat_raw,
                            "karar": karar_raw, 
                            "transfer": transfer_raw
                        })
        
        if not yapilacaklar:
            st.success("🎉 Liste Tamamlandı!"); st.stop()
            
        st.info(f"Kalan: **{len(yapilacaklar)}**")
        
        secenekler = [f"{h['isim']} | {h['tarih']}" for h in yapilacaklar]
        secilen_str = st.selectbox("👇 Sıradaki Hasta (Listeden):", secenekler)
        
        # Seçili veriyi sözlükten çek
        secilen_isim = secilen_str.split(" | ")[0]
        secilen_data = next((x for x in yapilacaklar if x["isim"] == secilen_isim), None)
        
        st.warning(f"⏰ **Yatış Saati:** {secilen_data['saat']}")

        # --- VERİLERİ DOLDUR BUTONU ---
        if st.button("⬇️ VERİLERİ GETİR / DOLDUR", type="primary", use_container_width=True):
            
            # 1. İsmi LISTE'den alıp State'e yaz
            st.session_state['form_vals']['isim'] = secilen_data['isim']
            st.session_state['form_vals']['karar'] = secilen_data['karar']
            st.session_state['form_vals']['transfer'] = secilen_data['transfer']
            
            # 2. Tarihi LISTE'den alıp State'e yaz (Format Çevirici)
            t_str = secilen_data['tarih'].split(" ")[0] # Varsa saati at
            try:
                # Liste formatı: 2022-09-26 (Yıl-Ay-Gün)
                parsed_date = datetime.strptime(t_str, "%Y-%m-%d")
            except:
                try:
                    # Alternatif: Gün.Ay.Yıl
                    parsed_date = datetime.strptime(t_str, "%d.%m.%Y")
                except:
                    parsed_date = datetime.now()
            
            st.session_state['form_vals']['tarih'] = parsed_date
            
            st.rerun()

    st.markdown("---")

    # --- FORM (Başlıklar Veri Sayfasından) ---
    input_values = {}
    
    with st.form("main_form", clear_on_submit=False):
        st.write(f"### 📋 Kayıt: {st.session_state['form_vals']['isim']}")
        
        for i, baslik in enumerate(headers):
            if not baslik or not baslik.strip(): continue
            
            # Başlık Temizliği
            b_clean = baslik.strip().replace("\n", " ")
            b_lower = b_clean.replace("İ", "i").replace("I", "ı").lower()
            
            c1, c2 = st.columns([1.5, 3])
            c1.markdown(f"<div class='etiket-box'>{b_clean}:</div>", unsafe_allow_html=True)
            
            # Benzersiz anahtar
            key = f"input_{i}_{b_clean}" 
            
            with c2:
                # --- CHECKBOX ---
                if b_clean in [x.strip() for x in CHECKBOX_LIST]:
                    chk = st.checkbox("Evet", key=key)
                    input_values[baslik] = 1 if chk else 0
                
                # --- İSİM (State'den gelir - Listeden çekilmişti) ---
                elif any(x in b_lower for x in ['isim', 'adı soyadı']):
                    input_values[baslik] = st.text_input(
                        "İsim", 
                        value=st.session_state['form_vals']['isim'], 
                        key=key, label_visibility="collapsed"
                    )

                # --- TARİH (State'den gelir - Listeden çekilmişti) ---
                elif "tarih" in b_lower:
                    input_values[baslik] = st.date_input(
                        "Tarih", 
                        value=st.session_state['form_vals']['tarih'], 
                        key=key, label_visibility="collapsed"
                    )

                # --- KARAR SÜRESİ ---
                elif "karar" in b_lower and "süre" in b_lower:
                    input_values[baslik] = st.text_input(
                        "Süre", 
                        value=st.session_state['form_vals']['karar'], 
                        key=key, label_visibility="collapsed"
                    )

                # --- TRANSFER SÜRESİ ---
                elif ("transfer" in b_lower or "transver" in b_lower) and "süre" in b_lower:
                    input_values[baslik] = st.text_input(
                        "Süre", 
                        value=st.session_state['form_vals']['transfer'], 
                        key=key, label_visibility="collapsed"
                    )

                # --- DİĞER ALANLAR ---
                elif "cinsiyet" in b_lower:
                    input_values[baslik] = st.selectbox("Cinsiyet", ["", "E", "K"], key=key, label_visibility="collapsed")
                
                elif any(x in b_lower for x in ['yaş', 'ateş', 'nabız', 'tansiyon', 'spo2']):
                    input_values[baslik] = st.number_input("Değer", step=1.0, format="%.2f", key=key, label_visibility="collapsed")
                
                elif any(x in b_lower for x in ['açıklama', 'not']):
                    input_values[baslik] = st.text_area("Not", height=68, key=key, label_visibility="collapsed")
                
                else:
                    input_values[baslik] = st.text_input("Sonuç", value="0", key=key, label_visibility="collapsed")
            
            st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)

        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        # Formu Veri sayfasına kaydet
        kaydet = col1.form_submit_button("✅ KAYDET", type="primary", use_container_width=True)
    
    pas_gec = st.button("🚫 PAS GEÇ", use_container_width=True)

    if kaydet:
        try:
            satir = []
            for h in headers:
                val = input_values.get(h, "")
                if isinstance(val, (datetime, pd.Timestamp)): val = val.strftime("%d.%m.%Y")
                satir.append(str(val))
            
            w_veri.append_row(satir)
            st.success(f"✅ {st.session_state['form_vals']['isim']} Kaydedildi!")
            
            # Kayıttan sonra formu sıfırla
            st.session_state['form_vals'] = {'isim': '', 'tarih': datetime.now(), 'karar': '0', 'transfer': '0'}
            time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Kayıt Hatası: {e}")

    if pas_gec:
        try:
            w_atlanan.append_row([secilen_isim, datetime.now().strftime("%Y-%m-%d")])
            st.warning("⏩ Pas geçildi."); time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Hata: {e}")
