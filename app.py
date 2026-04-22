import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pandas as pd

# ==========================================
# 1. AYARLAR VE STİL
# ==========================================
st.set_page_config(page_title="Pro Hasta Takip v14", layout="centered", page_icon="🏥")

st.markdown("""
<style>
    .stMarkdown { margin-bottom: -10px; }
    div[data-testid="column"] { align-items: center; display: flex; }
    .etiket-box {
        font-weight: bold; font-size: 13px; color: #0044cc;
        text-align: right; padding-right: 10px; width: 100%;
    }
    .stTextInput, .stNumberInput, .stDateInput, .stSelectbox { width: 100%; }
    .row-container { padding: 4px 0; border-bottom: 1px solid #eee; }
    div[data-testid="stCheckbox"] { display: flex; align-items: center; }
    .stButton>button { border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🏥 Dikey Hızlı Veri Girişi (v14)")

# --- Sayfa başına kaydırma fonksiyonu ---
def sayfa_basina_kaydir():
    st.markdown(
        """<script>
            window.parent.document.querySelector('section.main').scrollTo(0, 0);
            window.scrollTo(0, 0);
        </script>""",
        unsafe_allow_html=True
    )
    # Alternatif yöntem: st.components kullanarak
    import streamlit.components.v1 as components
    components.html(
        """<script>
            window.parent.document.querySelector('section.main').scrollTo({top: 0, behavior: 'smooth'});
        </script>""",
        height=0
    )

# --- A. CHECKBOX OLACAKLAR (EVET/HAYIR) ---
CHECKBOX_LIST = [
    "1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü", "Servis",
    "HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER",
    "Entübasyon", "İnotrop", "Mükerrer tetkik Ya da tedavi istemi", 
    "Kesin tanı koyulamaması", "8 saati aşıp yatmaması", "Birden fazla kliniği ilgilendirmesi",
    "KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı",  
    "Cr", "Ct", "Mr", "Usg",
    "Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb", "Plastik", "Göz", 
    "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji", "Göğüs H.", "Enfeksiyon H.", 
    "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji",
    "08.00-16.00", "16.00-24.00", "00.00-08.00",
    "DEVİR", "Taburcu", "Ölüm", "T. RED"
]

# --- B. OTOMATİK "0" GELECEK OLANLAR (SAYI GİRİŞİ) ---
SIFIR_LIST = [
    "Sıra Numarası", 
    "1Servis", 
    "Ybü", 
    "Toplam", 
    "Yapılan Kolsültasyon sayısı", 
    "1Dahilye", "1Göğüs Hast", "1Genel Cerrahi", "1Nrş", "1KVC", 
    "1Kbb", "1Plastik", "1Göz", "1Üroloji", "1Göğüs C.", 
    "1Kardiyoloji", "1Nöroloji", "1Orto", "1Enfeksiyon H.", 
    "1Psikiyatri", "1Cildiye", "1Anestezi", "1Radyoloji"
]

# --- C. YENİ: VARSAYILAN SABİT DEĞERLER ---
SABIT_DEGERLER = {
    "ateş": 36.5,
    "sistolik tansiyon": 120,
    "diyastolik tansiyon": 80,
    "nabız": 80,
    "spo2": 98,
    "gks": 15
}

# ==========================================
# 2. BAĞLANTI VE VERİ HAZIRLIĞI
# ==========================================
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds)

def verileri_hazirla():
    client = get_connection()
    sh = client.open("Hasta_Takip_Sistemi")
    w_veri = sh.worksheet("Veri")
    w_liste = sh.worksheet("Liste")
    w_atlanan = sh.worksheet("Atlananlar")
    
    raw_headers = w_veri.get_all_values()
    row1 = raw_headers[0]
    row2 = raw_headers[1]
    
    headers = []
    max_len = max(len(row1), len(row2))
    
    for i in range(max_len):
        v1 = row1[i].strip() if i < len(row1) else ""
        v2 = row2[i].strip() if i < len(row2) else ""
        final_header = v2 if v2 else v1
        headers.append(final_header.replace("\n", " ").strip())
        
    return w_veri, w_atlanan, headers, w_liste, w_liste.get_all_values()

try:
    w_veri, w_atlanan, headers, w_liste, liste_rows = verileri_hazirla()
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}"); st.stop()

# ==========================================
# 3. SIDEBAR: GERİ AL
# ==========================================
with st.sidebar:
    st.header("⚙️ İşlemler")
    st.write("Son satırı silmek için:")
    if st.button("⏪ SON KAYDI SİL", type="primary", use_container_width=True):
        mevcut = w_veri.get_all_values()
        if len(mevcut) > 2:
            w_veri.delete_rows(len(mevcut))
            st.success("✅ Silindi.")
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Veri yok.")

# ==========================================
# YARDIMCI FONKSİYON: Yatış saatine göre
# hangi vardiya checkbox'ının seçileceğini belirle
# ==========================================
def yatis_saatinden_vardiya_belirle(saat_str):
    """
    Yatış saati string'ini parse edip hangi vardiya checkbox'ının
    işaretleneceğini döndürür.
    Vardiyalar:
      08.00-16.00 -> saat 08:00 - 15:59
      16.00-24.00 -> saat 16:00 - 23:59
      00.00-08.00 -> saat 00:00 - 07:59
    """
    if not saat_str or saat_str.strip() in ("-", ""):
        return None
    
    saat_str = saat_str.strip()
    
    # Farklı saat formatlarını dene
    saat_num = None
    for fmt in ["%H:%M", "%H.%M", "%H:%M:%S", "%H.%M.%S"]:
        try:
            t = datetime.strptime(saat_str, fmt)
            saat_num = t.hour
            break
        except ValueError:
            continue
    
    # Eğer yukarıdaki formatlar tutmadıysa, sadece saat kısmını almayı dene
    if saat_num is None:
        try:
            # "08", "16" gibi sadece saat
            saat_num = int(saat_str.split(":")[0].split(".")[0].strip())
        except (ValueError, IndexError):
            return None
    
    if 8 <= saat_num < 16:
        return "08.00-16.00"
    elif 16 <= saat_num < 24:
        return "16.00-24.00"
    else:  # 0 <= saat_num < 8
        return "00.00-08.00"


# ==========================================
# YARDIMCI FONKSİYON: LİSTE sekmesinden
# kaydedilen hastayı satır numarasıyla sil
# ==========================================
def listeden_hasta_sil(hasta_isim, w_liste_sheet):
    """
    LİSTE sekmesinde hasta ismini bulup o satırı siler.
    Satır 4'ten itibaren arar (ilk 3 satır başlık).
    """
    try:
        tum_satirlar = w_liste_sheet.get_all_values()
        for idx, row in enumerate(tum_satirlar):
            if idx < 3:  # İlk 3 satır başlık, atla
                continue
            if len(row) > 4:
                liste_isim = str(row[4]).strip()
                if liste_isim == hasta_isim.strip():
                    # gspread satır numarası 1-indexed, idx 0-indexed
                    w_liste_sheet.delete_rows(idx + 1)
                    return True
        return False
    except Exception as e:
        st.warning(f"Liste silme hatası: {e}")
        return False


# ==========================================
# 4. HASTA SEÇİMİ
# ==========================================
with st.container():
    yapilacaklar = []
    # Her hasta için LİSTE'deki satır indexini de saklayalım
    for row_idx, row in enumerate(liste_rows[3:], start=3):
        if len(row) > 10:
            p_isim = str(row[4]).strip()
            if p_isim and "isim" not in p_isim.lower():
                yapilacaklar.append({
                    "isim": p_isim,
                    "tarih": str(row[6]).strip(),
                    "saat": str(row[8]).strip() if len(row) > 8 else "-",
                    "karar": str(row[10]).strip(),
                    "transfer": str(row[11]).strip(),
                    "liste_satir_idx": row_idx  # 0-indexed satır numarası
                })

    if not yapilacaklar:
        st.success("🎉 Liste Bitti!")
        st.stop()

    st.info(f"Kalan Hasta: **{len(yapilacaklar)}**")
    
    secenekler = [f"{x['isim']} | {x['tarih']}" for x in yapilacaklar]
    secilen_str = st.selectbox("👇 Sıradaki Hasta:", secenekler)
    secilen_ad = secilen_str.split(" | ")[0]
    secilen_veri = next((x for x in yapilacaklar if x['isim'] == secilen_ad), None)
    
    col_info, col_btn = st.columns([2, 1])
    col_info.warning(f"⏰ **Yatış Saati:** {secilen_veri['saat']}")
    
    getir_btn = col_btn.button("⬇️ BİLGİLERİ DOLDUR", type="primary", use_container_width=True)

    if getir_btn and secilen_veri:
        t_obj = datetime.now()
        try:
            d_str = secilen_veri['tarih'].split(" ")[0]
            t_obj = datetime.strptime(d_str, "%Y-%m-%d")
        except:
            try: t_obj = datetime.strptime(d_str, "%d.%m.%Y")
            except: pass

        # --- YATIŞ SAATİNE GÖRE VARDİYA CHECKBOX'INI OTOMATİK İŞARETLE ---
        vardiya = yatis_saatinden_vardiya_belirle(secilen_veri['saat'])
        
        for idx, h in enumerate(headers):
            h_cl = h.lower().replace("İ", "i").replace("I", "ı")
            key_id = f"input_{idx}"
            
            if "isim" in h_cl or "adı soyadı" in h_cl:
                st.session_state[key_id] = secilen_veri['isim']
            elif "tarih" in h_cl:
                st.session_state[key_id] = t_obj
            elif "karar" in h_cl and "süre" in h_cl:
                st.session_state[key_id] = secilen_veri['karar']
            elif ("transfer" in h_cl or "transver" in h_cl) and "süre" in h_cl:
                st.session_state[key_id] = secilen_veri['transfer']
            # Vardiya checkbox'larını otomatik işaretle
            elif h in ("08.00-16.00", "16.00-24.00", "00.00-08.00"):
                if vardiya and h == vardiya:
                    st.session_state[key_id] = True
                else:
                    st.session_state[key_id] = False

        st.toast("Bilgiler çekildi! Yatış saati vardiyası otomatik işaretlendi.", icon="✅")

st.markdown("---")

# ==========================================
# 5. FORM OLUŞTURMA
# ==========================================
input_values = {}

with st.form("veri_giris", clear_on_submit=False):
    st.write("### 📝 Kayıt Formu")
    
    for i, baslik in enumerate(headers):
        if not baslik.strip(): continue
        
        key_id = f"input_{i}"
        b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()

        # --- STATE BAŞLATMA (Varsayılan Değerler Dahil) ---
        if key_id not in st.session_state:
            if b_lower in SABIT_DEGERLER:
                st.session_state[key_id] = SABIT_DEGERLER[b_lower]
            elif baslik in SIFIR_LIST:
                st.session_state[key_id] = 0
            elif "tarih" in b_lower: 
                st.session_state[key_id] = datetime.now()
            elif baslik in CHECKBOX_LIST: 
                st.session_state[key_id] = False
            else: 
                st.session_state[key_id] = ""

        # Temizlik
        b_clean = baslik
        
        c1, c2 = st.columns([1.5, 3])
        c1.markdown(f"<div class='etiket-box'>{b_clean}:</div>", unsafe_allow_html=True)
        
        with c2:
            # 1. OTOMATİK "0" VEYA SABİT GELMESİ İSTENEN SAYILAR
            if baslik in SIFIR_LIST or b_lower in SABIT_DEGERLER:
                try: val = float(st.session_state[key_id]) if st.session_state[key_id] else 0.0
                except: val = 0.0
                
                # Ateş ise ondalıklı göster, diğerleri tam sayı
                if "ateş" in b_lower:
                    input_values[baslik] = st.number_input("Sayı", value=val, step=0.1, format="%.1f", key=key_id, label_visibility="collapsed")
                else:
                    input_values[baslik] = st.number_input("Sayı", value=int(val), step=1, format="%d", key=key_id, label_visibility="collapsed")

            # 2. CHECKBOX OLANLAR
            elif baslik in CHECKBOX_LIST:
                val = st.checkbox("Var", key=key_id)
                input_values[baslik] = 1 if val else 0
            
            # 3. İSİM
            elif "isim" in b_lower or "adı soyadı" in b_lower:
                input_values[baslik] = st.text_input("İsim", key=key_id, label_visibility="collapsed")
            
            # 4. TARİH (GÜN.AY.YIL)
            elif "tarih" in b_lower:
                val_t = st.session_state[key_id] if st.session_state[key_id] else datetime.now()
                input_values[baslik] = st.date_input("Tarih", value=val_t, key=key_id, format="DD.MM.YYYY", label_visibility="collapsed")
            
            # 5. SÜRELER
            elif "süre" in b_lower and ("karar" in b_lower or "transfer" in b_lower or "transver" in b_lower):
                input_values[baslik] = st.text_input("Süre", key=key_id, label_visibility="collapsed")
            
            # 6. CİNSİYET
            elif "cinsiyet" in b_lower:
                input_values[baslik] = st.selectbox("Cinsiyet", ["", "E", "K"], key=key_id, label_visibility="collapsed")
            
            # 7. VİTAL BULGULAR (EĞER SABİT LİSTEDE DEĞİLSE GENEL KURAL)
            elif any(x in b_lower for x in ['yaş', 'ateş', 'nabız', 'tansiyon', 'spo2', 'gks']):
                try: m_val = float(st.session_state[key_id]) if st.session_state[key_id] else 0.0
                except: m_val = 0.0
                if "ateş" in b_lower:
                    input_values[baslik] = st.number_input("Değer", value=m_val, step=0.1, format="%.1f", key=f"num_{i}", label_visibility="collapsed")
                else:
                    input_values[baslik] = st.number_input("Değer", value=int(m_val), step=1, format="%d", key=f"num_{i}", label_visibility="collapsed")
            
            # 8. NOT ALANLARI
            elif any(x in b_lower for x in ['açıklama', 'not']):
                input_values[baslik] = st.text_area("Not", key=key_id, height=70, label_visibility="collapsed")
            
            # 9. DİĞER STANDART METİN GİRİŞLERİ
            else:
                input_values[baslik] = st.text_input("Sonuç", key=key_id, label_visibility="collapsed")

        st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)

    st.markdown("---")
    c_btn1, c_btn2 = st.columns([3, 1])
    kaydet_btn = c_btn1.form_submit_button("✅ VERİYİ KAYDET", type="primary", use_container_width=True)

# --- PAS GEÇ: İki seçenekli ---
st.markdown("#### 🚫 Pas Geç")
pas_col1, pas_col2 = st.columns(2)
pas_eksik_btn = pas_col1.button("📋 VERİ EKSİK", use_container_width=True)
pas_sevk_btn = pas_col2.button("🚑 DIŞARIYA SEVK", use_container_width=True)

# ==========================================
# 6. KAYIT
# ==========================================
if kaydet_btn:
    try:
        yeni_satir = []
        for baslik in headers:
            if not baslik.strip():
                yeni_satir.append("")
            else:
                val = input_values.get(baslik, "")
                if hasattr(val, 'strftime'):
                    val = val.strftime("%d.%m.%Y")
                yeni_satir.append(str(val))
        
        w_veri.append_row(yeni_satir)
        
        # --- YENİ: KAYIT SONRASI LİSTE SEKMESİNDEN HASTAYI SİL ---
        silme_basarili = listeden_hasta_sil(secilen_ad, w_liste)
        
        if silme_basarili:
            st.success("✅ Kaydedildi ve listeden silindi!")
        else:
            st.success("✅ Kaydedildi! (Listeden silme yapılamadı, lütfen kontrol edin.)")
        
        for key in list(st.session_state.keys()):
            if key.startswith("input_") or key.startswith("num_"): 
                del st.session_state[key]
        
        sayfa_basina_kaydir()
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Kayıt Hatası: {e}")

if pas_eksik_btn:
    try:
        w_atlanan.append_row([secilen_ad, datetime.now().strftime("%Y-%m-%d"), "Veri Eksik"])
        st.warning(f"⏩ {secilen_ad} atlandı. (Sebep: Veri Eksik)")
        sayfa_basina_kaydir()
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")

if pas_sevk_btn:
    try:
        w_atlanan.append_row([secilen_ad, datetime.now().strftime("%Y-%m-%d"), "Dışarıya Sevk"])
        st.warning(f"⏩ {secilen_ad} atlandı. (Sebep: Dışarıya Sevk)")
        sayfa_basina_kaydir()
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")
