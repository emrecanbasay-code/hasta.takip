import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Kesin Çözüm v9", layout="centered")

# --- CSS (Görünüm) ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
    .baslik-box { text-align: right; font-weight: bold; padding-top: 10px; color: #0f54c9; }
    div[data-testid="column"] { align-items: center; }
</style>
""", unsafe_allow_html=True)

st.title("🏥 HASTA GİRİŞ SİSTEMİ (LİSTE -> VERİ)")

# --- 1. BAĞLANTI VE VERİ HAZIRLIĞI ---
@st.cache_resource
def baglanti_kur():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds)

def verileri_al():
    client = baglanti_kur()
    sh = client.open("Hasta_Takip_Sistemi")
    w_veri = sh.worksheet("Veri")
    w_liste = sh.worksheet("Liste")
    w_atlanan = sh.worksheet("Atlananlar")
    
    # VERİ SAYFASI BAŞLIKLARINI BİRLEŞTİR (1. ve 2. Satır)
    # Hedefimiz: "İsim", "Tarih" gibi başlıkların tam listesini çıkarmak
    raw = w_veri.get_all_values()
    row1 = raw[0] # Tarih vs.
    row2 = raw[1] # İsim, Yaş vs.
    
    headers = []
    max_len = max(len(row1), len(row2))
    for i in range(max_len):
        v1 = row1[i].strip() if i < len(row1) else ""
        v2 = row2[i].strip() if i < len(row2) else ""
        # 2. satır doluysa onu al, boşsa 1.'yi al
        headers.append(v2 if v2 else v1)
        
    return w_veri, w_atlanan, headers, w_liste.get_all_values()

# --- 2. VERİLERİ YÜKLE ---
try:
    w_veri, w_atlanan, headers, liste_rows = verileri_al()
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

# --- 3. LİSTE İŞLEME (KAYNAK) ---
# Liste.csv -> 4. Satırdan (Index 3) başlar
# E Sütunu (Index 4) -> İsim
# G Sütunu (Index 6) -> Tarih
# K Sütunu (Index 10) -> Karar Süresi
# L Sütunu (Index 11) -> Transfer Süresi

yapilacaklar = []
# Zaten işlenmişleri kontrol etmemiz gerekirse buraya ekleriz, şimdilik basit tutuyorum.
for row in liste_rows[3:]:
    if len(row) > 10:
        h_isim = str(row[4]).strip() # E Sütunu
        if h_isim and "isim" not in h_isim.lower(): # Başlık satırını atla
            yapilacaklar.append({
                "isim": h_isim,
                "tarih": str(row[6]).strip(), # G Sütunu
                "karar": str(row[10]).strip(), # K Sütunu
                "transfer": str(row[11]).strip() # L Sütunu
            })

# --- 4. ARAYÜZ ---

# Üst Kısım: Seçim ve Buton
st.info(f"Listede Bekleyen Hasta Sayısı: {len(yapilacaklar)}")
secilen_str = st.selectbox("HASTA SEÇİN:", [f"{x['isim']} | {x['tarih']}" for x in yapilacaklar])
secilen_veri = next((x for x in yapilacaklar if f"{x['isim']} | {x['tarih']}" == secilen_str), None)

col_btn1, col_btn2 = st.columns(2)
getir_btn = col_btn1.button("⬇️ BİLGİLERİ KUTULARA DOLDUR", type="primary")
temizle_btn = col_btn2.button("🔄 FORMU TEMİZLE")

# --- 5. KRİTİK NOKTA: STATE GÜNCELLEME ---
# Butona basıldığında, form elementlerinin "Key"lerine (ID) doğrudan veri basacağız.

if getir_btn and secilen_veri:
    # A. Tarihi Formatla (YYYY-MM-DD -> DD.MM.YYYY veya Date Object)
    t_obj = datetime.now()
    try:
        t_str = secilen_veri['tarih'].split(" ")[0]
        t_obj = datetime.strptime(t_str, "%Y-%m-%d") # Liste formatı
    except:
        pass # Hata olursa bugün kalsın

    # B. Başlıkları Tara ve Doğru Kutuyu Bul
    for i, h in enumerate(headers):
        h_low = h.lower().replace("İ","i").replace("I","ı")
        key_id = f"col_{i}" # Her kutunun kimliği: col_0, col_1, col_3 (İsim)...
        
        # 1. İSİM KUTUSU BULUNDU MU? (Liste E -> Veri D)
        if "isim" in h_low or "adı soyadı" in h_low:
            st.session_state[key_id] = secilen_veri['isim']
            
        # 2. TARİH KUTUSU
        elif "tarih" in h_low:
            st.session_state[key_id] = t_obj
            
        # 3. KARAR SÜRESİ
        elif "karar" in h_low and "süre" in h_low:
            st.session_state[key_id] = secilen_veri['karar']
            
        # 4. TRANSFER SÜRESİ
        elif ("transfer" in h_low or "transver" in h_low) and "süre" in h_low:
            st.session_state[key_id] = secilen_veri['transfer']

    st.success(f"{secilen_veri['isim']} bilgileri çekildi!")
    # Sayfayı yeniden yüklemeye gerek yok, session_state değiştiği için form render edilirken yeni değeri alacak.

if temizle_btn:
    for key in st.session_state.keys():
        if key.startswith("col_"):
            del st.session_state[key] # State'i temizle
    st.rerun()

# --- 6. FORM OLUŞTURMA (DİNAMİK) ---
st.markdown("---")
input_data = {}

with st.form("kayit_formu", clear_on_submit=False):
    st.write(f"### 📝 Kayıt: {secilen_veri['isim'] if secilen_veri else 'Seçim Yok'}")
    
    for i, baslik in enumerate(headers):
        if not baslik.strip(): continue
        
        key_id = f"col_{i}" # ÖNEMLİ: Yukarıdaki güncelleme ile aynı ID
        
        # Eğer butonla basılmadıysa ve state'de yoksa varsayılan değerler
        if key_id not in st.session_state:
            val_default = ""
            if "tarih" in baslik.lower(): val_default = datetime.now()
            st.session_state[key_id] = val_default # Boş başlat

        # Görsel Düzen
        c1, c2 = st.columns([1, 3])
        c1.markdown(f"<div class='baslik-box'>{baslik}</div>", unsafe_allow_html=True)
        
        with c2:
            # Widget Tipi Seçimi
            if "tarih" in baslik.lower():
                input_data[baslik] = st.date_input("Tarih", key=key_id, label_visibility="collapsed")
            elif any(x in baslik.lower() for x in ["cinsiyet"]):
                 input_data[baslik] = st.selectbox("Cinsiyet", ["", "E", "K"], key=key_id, label_visibility="collapsed")
            elif any(x in baslik.lower() for x in ["not", "açıklama"]):
                 input_data[baslik] = st.text_area("Not", key=key_id, height=70, label_visibility="collapsed")
            # Checkbox Listesi (Manuel kontrol gerekebilir, şimdilik text/number gidiyoruz, istenirse eklenir)
            else:
                 input_data[baslik] = st.text_input("Değer", key=key_id, label_visibility="collapsed")

    st.markdown("---")
    kaydet = st.form_submit_button("✅ VERİ DOSYASINA KAYDET", use_container_width=True)

# --- 7. KAYIT İŞLEMİ ---
if kaydet:
    satir = []
    for h in headers:
        if not h.strip():
            satir.append("")
            continue
        
        raw_val = input_data.get(h, "")
        # Tarih formatını string yap
        if isinstance(raw_val, (datetime, pd.Timestamp)):
             raw_val = raw_val.strftime("%d.%m.%Y")
        satir.append(str(raw_val))
        
    w_veri.append_row(satir)
    st.success("✅ Başarıyla Kaydedildi!")
    time.sleep(1)
    st.rerun()
