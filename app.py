import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# ==========================================
# 1. AYARLAR VE CSS
# ==========================================
SHEET_ADI = "Hasta_Takip_Sistemi"
st.set_page_config(page_title="Pro Hasta Takip", layout="centered", page_icon="🏥")

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

st.title("🏥 Dikey Hızlı Veri Girişi (v8.0 - Final)")

# Checkbox olacak başlıklar
CHECKBOX_LIST = [
    "1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü", "Servis",
    "HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER",
    "Entübasyon", "İnotrop", "Mükerrer tetkik Ya da tedavi istemi", 
    "Kesin tanı koyulamaması", "8 saati aşıp yatmaması", "Birden fazla kliniği ilgilendirmesi",
    "KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı", "MALİYET", "Cr", "Ct", "Mr", "Usg",
    "Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb", "Plastik", "Göz", 
    "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji", "Göğüs H.", "Enfeksiyon H.", 
    "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji",
    "08.00-16.00", "16.00-24.00", "00.00-08.00", "DEVİR", "Taburcu", "Ölüm", "T. RED"
]

# ==========================================
# 2. BAĞLANTI VE VERİ ÇEKME
# ==========================================
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_all_data():
    client = get_connection()
    sh = client.open(SHEET_ADI)
    w_veri = sh.worksheet("Veri")
    w_liste = sh.worksheet("Liste")
    w_atlanan = sh.worksheet("Atlananlar")
    
    # --- Veri Sayfası Başlıklarını Düzeltme ---
    # 1. ve 2. satırı çekip birleştiriyoruz.
    # Tarih 1. satırda, İsim 2. satırda.
    raw_headers = w_veri.get_all_values()[:2]
    row1 = raw_headers[0]
    row2 = raw_headers[1]
    
    final_headers = []
    max_len = max(len(row1), len(row2))
    
    for i in range(max_len):
        v1 = row1[i].strip() if i < len(row1) else ""
        v2 = row2[i].strip() if i < len(row2) else ""
        # 2. satır doluysa onu al (İsim, Yaş vb.), boşsa 1. satırı al (Tarih vb.)
        if v2: final_headers.append(v2)
        else: final_headers.append(v1)

    # Liste verisi
    liste_data = w_liste.get_all_values()
    
    # Atlananlar
    atlanan_data = w_atlanan.get_all_values()
    skipped_names = [r[0].strip() for r in atlanan_data if r]
    
    # İşlenenler (Veri sayfasından kontrol)
    # İsim sütunu genelde 4. sırada (Index 3) ama başlık yapısına göre değişebilir.
    # Biz dinamik arayalım:
    processed_names = []
    isim_col_idx = -1
    for idx, h in enumerate(final_headers):
        if "isim" in h.lower().replace('İ','i'):
            isim_col_idx = idx
            break
            
    if isim_col_idx != -1:
        processed_names = [r[isim_col_idx].strip() for r in w_veri.get_all_values()[2:] if len(r) > isim_col_idx]

    return w_veri, w_atlanan, final_headers, liste_data, processed_names, skipped_names

# ==========================================
# 3. STATE YÖNETİMİ (EN ÖNEMLİ KISIM)
# ==========================================
# Formun içindeki değerleri tutacak sözlük.
if 'active_patient' not in st.session_state:
    st.session_state.active_patient = {
        'isim': '',
        'tarih': datetime.now(),
        'karar': '0',
        'transfer': '0'
    }

# ==========================================
# 4. UYGULAMA AKIŞI
# ==========================================
try:
    w_veri, w_atlanan, headers, liste_rows, processed, skipped = get_all_data()
except Exception as e:
    st.error(f"Veri bağlantı hatası: {e}")
    st.stop()

# --- SIDEBAR: GERİ AL ---
with st.sidebar:
    st.header("⚙️ İşlemler")
    if st.button("⏪ SON KAYDI SİL (GERİ AL)", use_container_width=True):
        all_vals = w_veri.get_all_values()
        if len(all_vals) > 2:
            w_veri.delete_rows(len(all_vals))
            st.success("Son satır silindi.")
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Silinecek veri yok.")

# --- ANA EKRAN: LİSTE SEÇİMİ ---
with st.container():
    yapilacaklar = []
    # Liste.csv 4. satırdan başlar (Index 3)
    for row in liste_rows[3:]:
        if len(row) > 10:
            # LİSTE.CSV SÜTUN HARİTASI (Dosyana Göre Sabitlendi)
            # Index 4: İsim (E Sütunu)
            # Index 6: Tarih (G Sütunu) - Format: 2022-09-26
            # Index 8: Yatış Saati (I Sütunu)
            # Index 10: Karar Süresi (K Sütunu)
            # Index 11: Transfer Süresi (L Sütunu)
            
            p_name = str(row[4]).strip()
            p_date = str(row[6]).strip()
            p_time = str(row[8]).strip() if len(row) > 8 else "-"
            p_karar = str(row[10]).strip()
            p_transfer = str(row[11]).strip()
            
            if p_name and "isim" not in p_name.lower():
                if p_name not in processed and p_name not in skipped:
                    yapilacaklar.append({
                        "isim": p_name, "tarih": p_date, "saat": p_time,
                        "karar": p_karar, "transfer": p_transfer
                    })

    if not yapilacaklar:
        st.success("🎉 Liste Bitti!")
        st.stop()

    st.info(f"Kalan Hasta: **{len(yapilacaklar)}**")
    
    # Selectbox
    options = [f"{x['isim']} | {x['tarih']}" for x in yapilacaklar]
    selected_opt = st.selectbox("👇 Sıradaki Hasta:", options)
    
    # Seçilen objeyi bul
    sel_name = selected_opt.split(" | ")[0]
    sel_obj = next((x for x in yapilacaklar if x['isim'] == sel_name), None)
    
    st.warning(f"⏰ **Yatış Saati:** {sel_obj['saat']}")
    
    # --- BUTON: VERİLERİ DOLDUR ---
    if st.button("⬇️ BU HASTANIN BİLGİLERİNİ FORMA ÇEK", type="primary", use_container_width=True):
        # 1. İsim
        st.session_state.active_patient['isim'] = sel_obj['isim']
        # 2. Süreler
        st.session_state.active_patient['karar'] = sel_obj['karar']
        st.session_state.active_patient['transfer'] = sel_obj['transfer']
        # 3. Tarih (Parsing)
        d_str = sel_obj['tarih'].split(" ")[0] # Saati at
        try:
            # Dosyadaki format YYYY-MM-DD
            dt_val = datetime.strptime(d_str, "%Y-%m-%d")
        except:
            try:
                dt_val = datetime.strptime(d_str, "%d.%m.%Y")
            except:
                dt_val = datetime.now()
        st.session_state.active_patient['tarih'] = dt_val
        
        st.rerun() # Sayfayı yenile ki aşağıdaki form yeni değerlerle çizilsin

st.markdown("---")

# ==========================================
# 5. FORM OLUŞTURMA
# ==========================================
form_inputs = {}

with st.form("main_form", clear_on_submit=False):
    st.write(f"### 📋 Kayıt Formu: {st.session_state.active_patient['isim']}")
    
    for i, header in enumerate(headers):
        if not header or not header.strip(): continue
        
        # Temizlik
        h_clean = header.strip().replace("\n", " ")
        h_lower = h_clean.replace("İ", "i").replace("I", "ı").lower()
        
        # Layout
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{h_clean}:</div>", unsafe_allow_html=True)
        
        unique_key = f"inp_{i}"
        
        with c2:
            # 1. Checkboxlar
            if h_clean in CHECKBOX_LIST:
                val = st.checkbox("Var", key=unique_key)
                form_inputs[header] = 1 if val else 0
            
            # 2. İSİM (State'den okur)
            elif any(x in h_lower for x in ['isim', 'adı soyadı']):
                form_inputs[header] = st.text_input(
                    "İsim",
                    value=st.session_state.active_patient['isim'],
                    key=unique_key, label_visibility="collapsed"
                )
                
            # 3. TARİH (State'den okur)
            elif "tarih" in h_lower:
                form_inputs[header] = st.date_input(
                    "Tarih",
                    value=st.session_state.active_patient['tarih'],
                    key=unique_key, label_visibility="collapsed"
                )
                
            # 4. KARAR SÜRESİ
            elif "karar" in h_lower and "süre" in h_lower:
                form_inputs[header] = st.text_input(
                    "Süre",
                    value=st.session_state.active_patient['karar'],
                    key=unique_key, label_visibility="collapsed"
                )
                
            # 5. TRANSFER SÜRESİ (Transver hatasını da yakalar)
            elif ("transfer" in h_lower or "transver" in h_lower) and "süre" in h_lower:
                form_inputs[header] = st.text_input(
                    "Süre",
                    value=st.session_state.active_patient['transfer'],
                    key=unique_key, label_visibility="collapsed"
                )
            
            # 6. Cinsiyet
            elif "cinsiyet" in h_lower:
                form_inputs[header] = st.selectbox("Cinsiyet", ["", "E", "K"], key=unique_key, label_visibility="collapsed")
            
            # 7. Sayısal Alanlar
            elif any(x in h_lower for x in ['yaş', 'ateş', 'nabız', 'tansiyon', 'spo2']):
                form_inputs[header] = st.number_input("Değer", step=1.0, format="%.2f", key=unique_key, label_visibility="collapsed")
            
            # 8. Not
            elif any(x in h_lower for x in ['açıklama', 'not']):
                form_inputs[header] = st.text_area("Not", height=68, key=unique_key, label_visibility="collapsed")
            
            # 9. Diğerleri
            else:
                form_inputs[header] = st.text_input("Değer", value="0", key=unique_key, label_visibility="collapsed")
        
        st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # --- ALT BUTONLAR ---
    col_submit, col_pass = st.columns([3, 1])
    submitted = col_submit.form_submit_button("✅ VERİ SAYFASINA KAYDET", type="primary", use_container_width=True)

pas_btn = st.button("🚫 PAS GEÇ", use_container_width=True)

# --- AKSİYONLAR ---
if submitted:
    try:
        new_row = []
        for h in headers:
            val = form_inputs.get(h, "")
            # Tarih formatını Excel'e uygun string yap
            if isinstance(val, (datetime, pd.Timestamp)):
                val = val.strftime("%d.%m.%Y")
            new_row.append(str(val))
        
        w_veri.append_row(new_row)
        st.success(f"✅ {st.session_state.active_patient['isim']} başarıyla kaydedildi!")
        
        # Formu temizle
        st.session_state.active_patient = {'isim': '', 'tarih': datetime.now(), 'karar': '0', 'transfer': '0'}
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Kayıt Hatası: {e}")

if pas_btn:
    try:
        w_atlanan.append_row([sel_obj['isim'], datetime.now().strftime("%Y-%m-%d")])
        st.warning(f"{sel_obj['isim']} pas geçildi.")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")
