import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import pandas as pd
from groq import Groq
import json

# ==========================================
# 1. AYARLAR VE STİL
# ==========================================
st.set_page_config(page_title="Pro Hasta Takip v15", layout="centered", page_icon="🏥")

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
    
    /* === v15 MOBİL İYİLEŞTİRMELER === */
    
    /* Expander başlıklarını daha belirgin yap */
    .streamlit-expanderHeader {
        font-size: 16px !important;
        font-weight: bold !important;
        background-color: #f0f2f6 !important;
        border-radius: 8px !important;
    }
    
    /* Mobilde butonları daha büyük yap */
    @media (max-width: 768px) {
        .stButton>button {
            min-height: 50px !important;
            font-size: 16px !important;
        }
        .stCheckbox label {
            font-size: 15px !important;
            padding: 8px 0 !important;
        }
        /* Number input butonlarını büyüt */
        button[data-testid="stNumberInputStepUp"],
        button[data-testid="stNumberInputStepDown"] {
            min-width: 40px !important;
            min-height: 40px !important;
        }
    }
    
    /* Geri tuşuyla çıkmayı engelle - history API */
</style>
""", unsafe_allow_html=True)

# === GERİ TUŞUYLA ÇIKMAYI ENGELLEME ===
import streamlit.components.v1 as components
components.html("""
<script>
    // Tarayıcı geri tuşuyla uygulamadan çıkmayı engelle
    history.pushState(null, null, location.href);
    window.onpopstate = function () {
        history.go(1);
    };
    // Her 2 saniyede bir history'ye ekle (klavye kapatma sonrası koruma)
    setInterval(function() {
        history.pushState(null, null, location.href);
    }, 2000);
</script>
""", height=0)

st.title("🏥 Dikey Hızlı Veri Girişi (v15)")

if st.query_params.get("scroll_top") == "1":
    components.html("""<script>
        setTimeout(function() {
            window.parent.document.querySelector('section.main').scrollTo({top: 0, behavior: 'smooth'});
            window.scrollTo({top: 0, behavior: 'smooth'});
        }, 100);
    </script>""", height=0)
    st.query_params.clear()

# --- Sayfa başına kaydırma fonksiyonu ---
def sayfa_basina_kaydir():
    st.markdown(
        """<script>
            window.parent.document.querySelector('section.main').scrollTo(0, 0);
            window.scrollTo(0, 0);
        </script>""",
        unsafe_allow_html=True
    )
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
    "DEVİR", "Taburcu", "Ölüm", "T. RED", "KDH", "orto"
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
    "1Psikiyatri", "1Cildiye", "1Anestezi", "1Radyoloji", "1KDH"
]

# --- C. VARSAYILAN SABİT DEĞERLER ---
SABIT_DEGERLER = {
    "ateş": 36.5,
    "sistolik tansiyon": 120,
    "diyastolik tansiyon": 80,
    "nabız": 80,
    "spo2": 98,
    "gks": 15
}

# === v15 YENİ: ŞİKAYET VE TANI LİSTELERİ ===
BASVURU_SIKAYETLERI = [
    "", "KARIN AĞRISI", "NEFES DARLIĞI", "HALSİZLİK", "HEMOPTİZİ", "ANEMİ",
    "GÖĞÜS AĞRISI", "BAŞ AĞRISI", "ATEŞ", "SENKOP", "BULANTI-KUSMA",
    "BİLİNÇ BOZUKLUĞU", "DİZÜRİ", "HEMATÜRİ", "NEFES DARLIĞI",
    "ORAL ALIM BOZUKLUĞU", "GİS KANAMA", "MELENA", "HEMATEMEZ",
    "YAN AĞRISI", "BEL AĞRISI", "SIRT AĞRISI", "BACAK AĞRISI",
    "BACAK ŞİŞLİĞİ", "ÇARPINTI", "ÖKSÜRÜK", "NÖBET", "BAYILMA",
    "KANAMA", "KIRMIZI DIŞKILAMA", "İSHAL", "KABIZLIK", "YUTMA GÜÇLÜĞÜ",
    "İDRAR YAPAMAMA", "İLAÇ İNTOKSİKASYONU", "GENEL DURUM BOZUKLUĞU",
    "BİLİNÇ DEĞİŞİKLİĞİ", "HALSİZLİK", "BAŞ DÖNMESİ", "SİYAH DIŞKILAMA"
]

TANI_LISTESI = [
    "", "ANEMİ", "AKUT BÖBREK YETMEZLİĞİ", "PNÖMONİ", "KOAH ATAK",
    "KOLEDOKOLİTİAZİS", "KOLESİSTİT", "GİS KANAMA", "HİPOPOTASEMİ",
    "HİPOGLİSEMİ", "İSKEMİK SVO", "KOLANJİT", "BİLİYER PANKREATİT",
    "HİPONATREMİ", "DİRENÇLİ HİPERTANSİYON", "HİPERKALEMİ",
    "BEYİN ÖDEMİ", "HİPERKALSEMİ", "SUBDURAL HEMATOM", "DERİN DOKU ABSESİ",
    "ÜRİNER SİSTEM ENFEKSİYONU", "YARA YERİ ENFEKSİYONU",
    "BESLENME BOZUKLUKLARI", "İLAÇ İNTOKSİKASYONU", "ORAL ALIM BOZUKLUĞU",
    "KOAH", "PLEVRAL EFÜZYON", "AKCİĞER ÖDEMİ", "KALP YETMEZLİĞİ",
    "AKUT MİYOKARD İNFARKTÜSÜ", "PULMONER EMBOLİ", "DVT", "SEPSİS",
    "DİYABETİK KETOASIDOZ", "AKUT PANKREATİT", "SAFRA KESESİ TAŞI",
    "BÖBREK TAŞI", "APANDİSİT", "İLEUS", "GİS PERFORASYON",
    "RETROPERİTONEAL HEMATOM", "PNÖMOTORAKS", "SELÜLİT", " KOLESİSTİT", "HEMORAJİK SVO"
]

# === v15 YENİ: EXPANDER GRUPLARI ===
# Hangi header'ların hangi expander grubuna ait olduğunu belirle
EXPANDER_GRUPLARI = {
    "ek_hastalik": {
        "baslik": "🩺 Ek Hastalıklar",
        "alanlar": ["HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER"]
    },
    "yatirilma_sebebi": {
        "baslik": "📋 Yatırılma Sebebi",
        "alanlar": ["Entübasyon", "İnotrop", "Mükerrer tetkik Ya da tedavi istemi",
                     "Kesin tanı koyulamaması", "8 saati aşıp yatmaması", 
                     "Birden fazla kliniği ilgilendirmesi"]
    },
    "konsultasyon": {
        "baslik": "🏥 Konsültasyonlar",
        "alanlar": ["Yapılan Kolsültasyon sayısı", 
                     "1Dahilye", "1Göğüs Hast", "1Genel Cerrahi", "1Nrş", "1KVC",
                     "1Kbb", "1Plastik", "1Göz", "1Üroloji", "1Göğüs C.",
                     "1Kardiyoloji", "1Nöroloji", "1Orto", "1Enfeksiyon H.",
                     "1Psikiyatri", "1Cildiye", "1Anestezi", "1Radyoloji", "1KDH"]
    },
    "lab": {
        "baslik": "🧪 Laboratuvar & Görüntüleme",
        "alanlar": ["KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı", "Cr",
                     "Ct", "Mr", "Usg"]
    },
    "yatis_yeri": {
        "baslik": "🛏️ Yatış Yeri & Bölüm",
        "alanlar": ["Servis", "1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü",
                     "Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb",
                     "Plastik", "Göz", "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji",
                     "Göğüs H.", "Enfeksiyon H.", "Psikiyatri", "Cildiye", "Anestezi",
                     "Radyoloji", "KDH", "orto"]
    },
    "yatis_saati": {
        "baslik": "⏰ Yatış Saati & Süre",
        "alanlar": ["08.00-16.00", "16.00-24.00", "00.00-08.00",
                     "1Servis", "Ybü", "Toplam"]
    },
    "sonuc": {
        "baslik": "📊 Sonuç",
        "alanlar": ["DEVİR", "Taburcu", "Ölüm", "T. RED"]
    }
}

# Tüm expander alanlarını düz bir set olarak topla
ALL_EXPANDER_FIELDS = set()
for grp in EXPANDER_GRUPLARI.values():
    ALL_EXPANDER_FIELDS.update(grp["alanlar"])

# Bir header'ın hangi gruba ait olduğunu bul
def get_expander_group(baslik):
    for grp_key, grp_val in EXPANDER_GRUPLARI.items():
        if baslik in grp_val["alanlar"]:
            return grp_key
    return None

# Şikayet/Tanı alanı mı kontrol et
def is_sikayet_alani(b_lower):
    return "başvuru şikayeti" in b_lower or "şikayet" in b_lower

def is_tani_alani(b_lower, baslik):
    return baslik.strip() in ("Tanısı", "SON TANISI") or "tanısı" in b_lower.replace("İ","i") or "son tanisi" in b_lower.replace("İ","i")

# ==========================================
# 2. BAĞLANTI VE VERİ HAZIRLIĞI
# ==========================================
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds)

@st.cache_resource
def get_groq_client():
    api_key = st.secrets["groq_api_key"]["key"]
    return Groq(api_key=api_key)

def groq_ile_veri_cikar(metin):
    """Ses metnini Groq API ile JSON formatına dönüştürür."""
    client = get_groq_client()
    
    prompt = """Sen bir hasta veri çıkarma asistanısın. Türkçe hasta bilgilerini JSON formatına dönüştür.
İsim ve vardiya bilgisi VERİLMEYECEK, onlar zaten mevcut. Sadece aşağıdaki alanları çıkar:

{
  "yas": 0,
  "cinsiyet": "",
  "ates": 36.5,
  "sistolik": 120,
  "diyastolik": 80,
  "nabiz": 80,
  "spo2": 98,
  "gks": 15,
  "sikayet": "",
  "ht": 0, "dm": 0, "kby": 0, "kah": 0, "af": 0, "koah": 0, "svh": 0, "malignite": 0, "kky": 0, "alzheimer": 0,
  "entubasyon": 0, "inotrop": 0, "mukerrer_tetkik": 0, "kesin_tani": 0, "sekiz_saat": 0, "coklu_klinik": 0,
  "konsultasyon_toplam": 0,
  "1dahilye": 0, "1gogus_hast": 0, "1genel_cerrahi": 0, "1nrs": 0, "1kvc": 0, "1kbb": 0, "1plastik": 0, "1goz": 0, "1uroloji": 0, "1gogus_c": 0, "1kardiyoloji": 0, "1noroloji": 0, "1orto": 0, "1enfeksiyon_h": 0, "1psikiyatri": 0, "1cildiye": 0, "1anestezi": 0, "1radyoloji": 0, "1kdh": 0,
  "koag": 0, "tit": 0, "trop": 0, "hmg": 0, "bk": 0, "kan_gazi": 0,
  "cr": 0, "ct": 0, "mr": 0, "usg": 0,
  "tani": "",
  "son_tani": "",
  "servis": 0, "1_basamak_ybu": 0, "2_basamak_ybu": 0, "3_basamak_ybu": 0,
  "bolum_dahilye": 0, "bolum_gogus_hast": 0, "bolum_genel_cerrahi": 0, "bolum_nrs": 0, "bolum_kvc": 0, "bolum_kbb": 0, "bolum_plastik": 0, "bolum_goz": 0, "bolum_uroloji": 0, "bolum_gogus_c": 0, "bolum_kardiyoloji": 0, "bolum_noroloji": 0, "bolum_gogus_h": 0, "bolum_enfeksiyon_h": 0, "bolum_psikiyatri": 0, "bolum_cildiye": 0, "bolum_anestezi": 0, "bolum_radyoloji": 0, "bolum_kdh": 0, "bolum_orto": 0,
  "devir": 0, "taburcu": 0, "olum": 0, "t_red": 0,
  "yatis_suresi": 0,
  "transfer_suresi": 0
}

Kurallar:
- Sayısal değerler için sayı kullan (0 veya pozitif tam sayı)
- String değerler için BÜYÜK HARF kullan
- Bilgi metinde geçmiyorsa varsayılan değeri kullan
- Çıktı SADECE JSON olacak, başka hiçbir şey yazma

Hasta bilgileri:"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": metin}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        yanit = response.choices[0].message.content.strip()
        
        if yanit.startswith("```"):
            yanit = yanit.split("```")[1]
            if yanit.startswith("json"):
                yanit = yanit[4:]
        
        return json.loads(yanit)
    except json.JSONDecodeError:
        st.error("AI çıktısı JSON formatına dönüştürülemedi. Tekrar deneyin.")
        return None
    except Exception as e:
        st.error(f"Groq API hatası: {e}")
        return None

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
# YARDIMCI FONKSİYONLAR
# ==========================================
def yatis_saatinden_vardiya_belirle(saat_str):
    if not saat_str or saat_str.strip() in ("-", ""):
        return None
    saat_str = saat_str.strip()
    saat_num = None
    for fmt in ["%H:%M", "%H.%M", "%H:%M:%S", "%H.%M.%S"]:
        try:
            t = datetime.strptime(saat_str, fmt)
            saat_num = t.hour
            break
        except ValueError:
            continue
    if saat_num is None:
        try:
            saat_num = int(saat_str.split(":")[0].split(".")[0].strip())
        except (ValueError, IndexError):
            return None
    if 8 <= saat_num < 16:
        return "08.00-16.00"
    elif 16 <= saat_num < 24:
        return "16.00-24.00"
    else:
        return "00.00-08.00"

def listeden_hasta_sil(hasta_isim, w_liste_sheet):
    try:
        tum_satirlar = w_liste_sheet.get_all_values()
        for idx, row in enumerate(tum_satirlar):
            if idx < 3:
                continue
            if len(row) > 4:
                liste_isim = str(row[4]).strip()
                if liste_isim == hasta_isim.strip():
                    w_liste_sheet.delete_rows(idx + 1)
                    return True
        return False
    except Exception as e:
        st.warning(f"Liste silme hatası: {e}")
        return False

def formu_doldur(veri_json):
    """AI çıktısındaki değerleri form alanlarına yazar."""
    if not veri_json:
        return
    
    header_map = {}
    for idx, h in enumerate(headers):
        h_lower = h.lower().replace("İ", "i").replace("I", "ı").strip()
        header_map[h_lower] = idx
    
    if "yas" in veri_json and veri_json["yas"]:
        key = f"input_{header_map.get('yaş', -1)}"
        if key in st.session_state:
            st.session_state[key] = int(veri_json["yas"])
    
    if "cinsiyet" in veri_json and veri_json["cinsiyet"]:
        key = f"input_{header_map.get('cinsiyet', -1)}"
        if key in st.session_state:
            st.session_state[key] = veri_json["cinsiyet"].upper()
    
    vital_map = {
        "ates": "ateş", "sistolik": "sistolik tansiyon",
        "diyastolik": "diyastolik tansiyon", "nabiz": "nabız",
        "spo2": "spo2", "gks": "gks"
    }
    for json_key, header_key in vital_map.items():
        if json_key in veri_json and veri_json[json_key]:
            idx = header_map.get(header_key, -1)
            if idx >= 0:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = float(veri_json[json_key])
    
    if "sikayet" in veri_json and veri_json["sikayet"]:
        for idx, h in enumerate(headers):
            h_lower = h.lower().replace("İ", "i").replace("I", "ı")
            if "başvuru şikayeti" in h_lower or "şikayet" in h_lower:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = veri_json["sikayet"].upper()
                break
    
    kronik_map = {
        "ht": "HT", "dm": "DM", "kby": "KBY", "kah": "KAH",
        "af": "AF", "koah": "KOAH", "svh": "SVH", "malignite": "Malignite",
        "kky": "KKY", "alzheimer": "ALZHEİMER"
    }
    for json_key, header_key in kronik_map.items():
        if json_key in veri_json:
            idx = header_map.get(header_key.lower(), -1)
            if idx >= 0:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = bool(veri_json[json_key])
    
    yatirim_map = {
        "entubasyon": "Entübasyon", "inotrop": "İnotrop",
        "mukerrer_tetkik": "Mükerrer tetkik Ya da tedavi istemi",
        "kesin_tani": "Kesin tanı koyulamaması",
        "sekiz_saat": "8 saati aşıp yatmaması",
        "coklu_klinik": "Birden fazla kliniği ilgilendirmesi"
    }
    for json_key, header_key in yatirim_map.items():
        if json_key in veri_json:
            idx = header_map.get(header_key.lower(), -1)
            if idx >= 0:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = bool(veri_json[json_key])
    
    kons_map = {
        "1dahilye": "1Dahilye", "1gogus_hast": "1Göğüs Hast",
        "1genel_cerrahi": "1Genel Cerrahi", "1nrs": "1Nrş",
        "1kvc": "1KVC", "1kbb": "1Kbb", "1plastik": "1Plastik",
        "1goz": "1Göz", "1uroloji": "1Üroloji", "1gogus_c": "1Göğüs C.",
        "1kardiyoloji": "1Kardiyoloji", "1noroloji": "1Nöroloji",
        "1orto": "1Orto", "1enfeksiyon_h": "1Enfeksiyon H.",
        "1psikiyatri": "1Psikiyatri", "1cildiye": "1Cildiye",
        "1anestezi": "1Anestezi", "1radyoloji": "1Radyoloji", "1kdh": "1KDH"
    }
    for json_key, header_key in kons_map.items():
        if json_key in veri_json and veri_json[json_key]:
            idx = header_map.get(header_key.lower(), -1)
            if idx >= 0:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = int(veri_json[json_key])
    
    if "konsultasyon_toplam" in veri_json and veri_json["konsultasyon_toplam"]:
        idx = header_map.get("yapılan kolsültasyon sayısı", -1)
        if idx >= 0:
            key = f"input_{idx}"
            if key in st.session_state:
                st.session_state[key] = int(veri_json["konsultasyon_toplam"])
    
    lab_map = {
        "koag": "KOAG", "tit": "TİT", "trop": "TROP",
        "hmg": "Hmg", "bk": "Bk", "kan_gazi": "Kan Gazı"
    }
    for json_key, header_key in lab_map.items():
        if json_key in veri_json:
            idx = header_map.get(header_key.lower(), -1)
            if idx >= 0:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = bool(veri_json[json_key])
    
    gor_map = {"cr": "Cr", "ct": "Ct", "mr": "Mr", "usg": "Usg"}
    for json_key, header_key in gor_map.items():
        if json_key in veri_json:
            idx = header_map.get(header_key.lower(), -1)
            if idx >= 0:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = bool(veri_json[json_key])
    
    if "tani" in veri_json and veri_json["tani"]:
        for idx, h in enumerate(headers):
            if h.strip() == "Tanısı":
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = veri_json["tani"].upper()
                break
    
    if "son_tani" in veri_json and veri_json["son_tani"]:
        for idx, h in enumerate(headers):
            if h.strip() == "SON TANISI":
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = veri_json["son_tani"].upper()
                break
    
    yatyeri_map = {
        "servis": "Servis", "1_basamak_ybu": "1. Basamak Ybü",
        "2_basamak_ybu": "2. Basamak Ybü", "3_basamak_ybu": "3. Basamak Ybü"
    }
    for json_key, header_key in yatyeri_map.items():
        if json_key in veri_json:
            idx = header_map.get(header_key.lower(), -1)
            if idx >= 0:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = bool(veri_json[json_key])
    
    bolum_map = {
        "bolum_dahilye": "Dahilye", "bolum_gogus_hast": "Göğüs Hast",
        "bolum_genel_cerrahi": "Genel Cerrahi", "bolum_nrs": "Nrş",
        "bolum_kvc": "KVC", "bolum_kbb": "Kbb", "bolum_plastik": "Plastik",
        "bolum_goz": "Göz", "bolum_uroloji": "Üroloji", "bolum_gogus_c": "Göğüs C.",
        "bolum_kardiyoloji": "Kardiyoloji", "bolum_noroloji": "Nöroloji",
        "bolum_gogus_h": "Göğüs H.", "bolum_enfeksiyon_h": "Enfeksiyon H.",
        "bolum_psikiyatri": "Psikiyatri", "bolum_cildiye": "Cildiye",
        "bolum_anestezi": "Anestezi", "bolum_radyoloji": "Radyoloji",
        "bolum_kdh": "KDH", "bolum_orto": "orto"
    }
    for json_key, header_key in bolum_map.items():
        if json_key in veri_json:
            idx = header_map.get(header_key.lower(), -1)
            if idx >= 0:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = bool(veri_json[json_key])
    
    sonuc_map = {
        "devir": "DEVİR", "taburcu": "Taburcu",
        "olum": "Ölüm", "t_red": "T. RED"
    }
    for json_key, header_key in sonuc_map.items():
        if json_key in veri_json:
            idx = header_map.get(header_key.lower(), -1)
            if idx >= 0:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = bool(veri_json[json_key])
    
    if "yatis_suresi" in veri_json and veri_json["yatis_suresi"]:
        for idx, h in enumerate(headers):
            h_lower = h.lower().replace("İ", "i").replace("I", "ı")
            if "yatış karar" in h_lower and "süre" in h_lower:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = veri_json["yatis_suresi"]
                break
    
    if "transfer_suresi" in veri_json and veri_json["transfer_suresi"]:
        for idx, h in enumerate(headers):
            h_lower = h.lower().replace("İ", "i").replace("I", "ı")
            if "transfer" in h_lower and "süre" in h_lower:
                key = f"input_{idx}"
                if key in st.session_state:
                    st.session_state[key] = veri_json["transfer_suresi"]
                break

# ==========================================
# 4. HASTA SEÇİMİ
# ==========================================
with st.container():
    yapilacaklar = []
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
                    "liste_satir_idx": row_idx
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
            elif h in ("08.00-16.00", "16.00-24.00", "00.00-08.00"):
                if vardiya and h == vardiya:
                    st.session_state[key_id] = True
                else:
                    st.session_state[key_id] = False

        st.toast("Bilgiler çekildi! Yatış saati vardiyası otomatik işaretlendi.", icon="✅")

st.markdown("---")

# ==========================================
# 5. FORM OLUŞTURMA (v15 - EXPANDER İLE)
# ==========================================
input_values = {}

# === YARDIMCI: Tek bir form alanını render et ===
def render_field(i, baslik, key_id, b_lower, inside_expander=False):
    """Tek bir form alanını render eder ve değeri döndürür."""
    
    # --- STATE BAŞLATMA ---
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

    b_clean = baslik
    
    c1, c2 = st.columns([1.5, 3])
    c1.markdown(f"<div class='etiket-box'>{b_clean}:</div>", unsafe_allow_html=True)
    
    with c2:
        # 1. OTOMATİK "0" VEYA SABİT SAYILAR
        if baslik in SIFIR_LIST or b_lower in SABIT_DEGERLER:
            try: val = float(st.session_state[key_id]) if st.session_state[key_id] else 0.0
            except: val = 0.0
            if "ateş" in b_lower:
                return st.number_input("Sayı", value=val, step=0.1, format="%.1f", key=key_id, label_visibility="collapsed")
            else:
                return st.number_input("Sayı", value=int(val), step=1, format="%d", key=key_id, label_visibility="collapsed")

        # 2. CHECKBOX
        elif baslik in CHECKBOX_LIST:
            val = st.checkbox("Var", key=key_id)
            return 1 if val else 0
        
        # 3. İSİM
        elif "isim" in b_lower or "adı soyadı" in b_lower:
            return st.text_input("İsim", key=key_id, label_visibility="collapsed")
        
        # 4. TARİH
        elif "tarih" in b_lower:
            val_t = st.session_state[key_id] if st.session_state[key_id] else datetime.now()
            return st.date_input("Tarih", value=val_t, key=key_id, format="DD.MM.YYYY", label_visibility="collapsed")
        
        # 5. SÜRELER
        elif "süre" in b_lower and ("karar" in b_lower or "transfer" in b_lower or "transver" in b_lower):
            return st.text_input("Süre", key=key_id, label_visibility="collapsed")
        
        # 6. CİNSİYET
        elif "cinsiyet" in b_lower:
            return st.selectbox("Cinsiyet", ["", "E", "K"], key=key_id, label_visibility="collapsed")
        
        # === v15 YENİ: BAŞVURU ŞİKAYETİ - COMBOBOX ===
        elif is_sikayet_alani(b_lower):
            # Önce selectbox ile sık şikayetlerden seç
            secim = st.selectbox(
                "Şikayet Seç", 
                BASVURU_SIKAYETLERI,
                key=f"sikayet_sec_{i}",
                label_visibility="collapsed",
                help="Listede yoksa aşağıya yazın"
            )
            # Eğer listede yoksa elle yazabilsin
            if secim:
                # Seçim yapıldıysa onu kullan
                st.session_state[key_id] = secim
                return secim
            else:
                # Boş seçildiyse text input göster
                return st.text_input("veya yazın...", key=key_id, label_visibility="collapsed",
                                     placeholder="Listede yoksa buraya yazın")
        
        # === v15 YENİ: TANI ALANLARI - COMBOBOX ===
        elif is_tani_alani(b_lower, baslik):
            secim = st.selectbox(
                "Tanı Seç",
                TANI_LISTESI,
                key=f"tani_sec_{i}",
                label_visibility="collapsed",
                help="Listede yoksa aşağıya yazın"
            )
            if secim:
                st.session_state[key_id] = secim
                return secim
            else:
                return st.text_input("veya yazın...", key=key_id, label_visibility="collapsed",
                                     placeholder="Listede yoksa buraya yazın")
        
        # 7. VİTAL BULGULAR
        elif any(x in b_lower for x in ['yaş', 'ateş', 'nabız', 'tansiyon', 'spo2', 'gks']):
            try: m_val = float(st.session_state[key_id]) if st.session_state[key_id] else 0.0
            except: m_val = 0.0
            if "ateş" in b_lower:
                return st.number_input("Değer", value=m_val, step=0.1, format="%.1f", key=f"num_{i}", label_visibility="collapsed")
            else:
                return st.number_input("Değer", value=int(m_val), step=1, format="%d", key=f"num_{i}", label_visibility="collapsed")
        
        # 8. NOT ALANLARI
        elif any(x in b_lower for x in ['açıklama', 'not']):
            return st.text_area("Not", key=key_id, height=70, label_visibility="collapsed")
        
        # 9. DİĞER METİN
        else:
            return st.text_input("Sonuç", key=key_id, label_visibility="collapsed")


# ==========================================
# SESLİ VERİ GİRİŞİ
# ==========================================
st.markdown("### 🎤 Sesli Veri Girişi")
st.caption("Hasta bilgilerini sesli anlatın. 'Doldur' dediğinizde AI formu dolduracak.")

col_mic, col_ai1, col_ai2 = st.columns([1, 1, 1])

with col_mic:
    try:
        from streamlit_mic_recorder import mic_recorder
        audio = mic_recorder(
            start_prompt="🎤 Konuş",
            stop_prompt="⏹ Durdur",
            just_once=True,
            use_container_width=True,
            key="mic_recorder"
        )
        if audio and audio.get("bytes"):
            st.session_state.ses_audio = audio["bytes"]
            st.info("🎤 Ses kaydedildi. 'AI ile Doldur' butonuna basın.")
    except ImportError:
        st.warning("streamlit-mic-recorder yüklenemedi. Manuel giriş yapın.")
        audio = None

with col_ai1:
    if st.button("🤖 AI ile Doldur", type="secondary", use_container_width=True):
        if "ses_audio" in st.session_state and st.session_state.ses_audio:
            try:
                from groq import Groq as GroqClient
                client = get_groq_client()
                
                with st.spinner("Ses metne dönüştürülüyor..."):
                    import io
                    audio_file = io.BytesIO(st.session_state.ses_audio)
                    audio_file.name = "audio.wav"
                    
                    transcription = client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3",
                        language="tr"
                    )
                    ses_metni = transcription.text
                    st.session_state.ses_metni = ses_metni
                    st.info(f"📝 Algılanan: {ses_metni}")
                
                with st.spinner("AI hasta bilgilerini çıkarıyor..."):
                    veri = groq_ile_veri_cikar(ses_metni)
                    if veri:
                        formu_doldur(veri)
                        st.success("✅ Form AI ile dolduruldu! Kontrol edip kaydedin.")
                        st.session_state.ses_audio = None
                        st.rerun()
            except Exception as e:
                st.error(f"AI hatası: {e}")
        else:
            st.warning("Önce sesli giriş yapın.")

with col_ai2:
    if st.button("🗑️ Temizle", use_container_width=True):
        st.session_state.ses_audio = None
        st.session_state.ses_metni = ""
        st.rerun()

st.markdown("---")


with st.form("veri_giris", clear_on_submit=False):
    st.write("### 📝 Kayıt Formu")
    
    rendered_group_headers = set()
    
    field_to_group = {}
    for baslik in headers:
        grp = get_expander_group(baslik)
        if grp:
            field_to_group[baslik] = grp
    
    i = 0
    while i < len(headers):
        baslik = headers[i]
        if not baslik.strip():
            i += 1
            continue
        
        key_id = f"input_{i}"
        b_lower = baslik.lower().replace("İ", "i").replace("I", "ı").strip()
        
        grp_key = field_to_group.get(baslik)
        
        if grp_key:
            if grp_key not in rendered_group_headers:
                grp = EXPANDER_GRUPLARI[grp_key]
                st.markdown(f"#### {grp['baslik']}")
                rendered_group_headers.add(grp_key)
            
            val = render_field(i, baslik, key_id, b_lower)
            input_values[baslik] = val
            st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)
        else:
            val = render_field(i, baslik, key_id, b_lower)
            input_values[baslik] = val
            st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)
        
        i += 1

    st.markdown("---")
    c_btn1, c_btn2 = st.columns([3, 1])
    kaydet_btn = c_btn1.form_submit_button("✅ VERİYİ KAYDET", type="primary", use_container_width=True)

# --- PAS GEÇ ---
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
        
        silme_basarili = listeden_hasta_sil(secilen_ad, w_liste)
        
        if silme_basarili:
            st.success("✅ Kaydedildi ve listeden silindi!")
        else:
            st.success("✅ Kaydedildi! (Listeden silme yapılamadı, lütfen kontrol edin.)")
        
        for i_h, h in enumerate(headers):
            if not h.strip():
                continue
            key = f"input_{i_h}"
            b_lower = h.lower().replace("İ", "i").replace("I", "ı").strip()
            if b_lower in SABIT_DEGERLER:
                st.session_state[key] = SABIT_DEGERLER[b_lower]
            elif h in SIFIR_LIST:
                st.session_state[key] = 0
            elif "tarih" in b_lower:
                st.session_state[key] = datetime.now()
            elif h in CHECKBOX_LIST:
                st.session_state[key] = False
            elif "cinsiyet" in b_lower:
                st.session_state[key] = ""
            else:
                st.session_state[key] = ""
        
        for key in list(st.session_state.keys()):
            if key.startswith("num_") or key.startswith("sikayet_sec_") or key.startswith("tani_sec_"):
                del st.session_state[key]
        
        st.query_params["scroll_top"] = "1"
        st.rerun()
    except Exception as e:
        st.error(f"Kayıt Hatası: {e}")

if pas_eksik_btn:
    try:
        silme_basarili = listeden_hasta_sil(secilen_ad, w_liste)
        w_atlanan.append_row([secilen_ad, datetime.now().strftime("%Y-%m-%d"), "Veri Eksik"])
        if silme_basarili:
            st.success(f"✅ {secilen_ad} atlandı ve listeden silindi!")
        else:
            st.warning(f"⏩ {secilen_ad} atlandı. (Listeden silme yapılamadı)")
        st.query_params["scroll_top"] = "1"
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")

if pas_sevk_btn:
    try:
        silme_basarili = listeden_hasta_sil(secilen_ad, w_liste)
        w_atlanan.append_row([secilen_ad, datetime.now().strftime("%Y-%m-%d"), "Dışarıya Sevk"])
        if silme_basarili:
            st.success(f"✅ {secilen_ad} atlandı ve listeden silindi!")
        else:
            st.warning(f"⏩ {secilen_ad} atlandı. (Listeden silme yapılamadı)")
        st.query_params["scroll_top"] = "1"
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")
