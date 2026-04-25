import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import streamlit.components.v1 as components

# ==========================================
# 1. SAYFA AYARLARI VE MOBİL STİL
# ==========================================
st.set_page_config(
    page_title="Hasta Takip Mobil",
    layout="centered",
    page_icon="🏥",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* --- GENEL MOBİL OPTİMİZASYON --- */
    .block-container {
        padding-top: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }

    /* Sidebar toggle daha büyük */
    button[kind="header"] { transform: scale(1.3); }

    /* Expander başlıkları daha büyük ve tıklanabilir */
    .streamlit-expanderHeader {
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        padding: 0.8rem 0.5rem !important;
        background-color: #f0f2f6 !important;
        border-radius: 8px !important;
    }

    /* Butonlar daha büyük (parmak dostu) */
    .stButton > button {
        min-height: 52px !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        touch-action: manipulation;
    }

    /* Form submit butonu */
    .stFormSubmitButton > button {
        min-height: 56px !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
    }

    /* Number input artı/eksi butonları büyüt */
    button[data-testid="stNumberInputStepUp"],
    button[data-testid="stNumberInputStepDown"] {
        width: 40px !important;
        height: 40px !important;
    }

    /* Selectbox ve multiselect daha yüksek */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        min-height: 44px !important;
    }

    /* Genel input alanları */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        min-height: 44px !important;
        font-size: 1rem !important;
    }

    /* Divider ince çizgi */
    hr { margin: 0.5rem 0 !important; }

    /* Küçük bilgi kutuları */
    .info-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 2px;
    }
    .info-badge-blue { background: #dbeafe; color: #1e40af; }
    .info-badge-green { background: #dcfce7; color: #166534; }
    .info-badge-orange { background: #ffedd5; color: #9a3412; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SABİT TANIMLAMALAR
# ==========================================

# --- A. CHECKBOX OLACAKLAR (orijinal koddan) ---
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
    "DEVİR", "Taburcu", "Ölüm", "T. RED", "KDH"
]

# --- B. OTOMATİK "0" GELECEK OLANLAR (UI'DA GÖSTERİLMEYECEK) ---
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

# --- D. MULTİSELECT GRUPLARI ---
# Her grup: (multiselect label, [Excel'deki başlık isimleri])
EK_HASTALIKLAR = ["HT", "DM", "KBY", "KAH", "AF", "KOAH", "SVH", "Malignite", "KKY", "ALZHEİMER"]
SORUN_DURUMLARI = [
    "Mükerrer tetkik Ya da tedavi istemi",
    "Kesin tanı koyulamaması",
    "8 saati aşıp yatmaması",
    "Birden fazla kliniği ilgilendirmesi"
]
LABORATUVAR = ["KOAG", "TİT", "TROP", "Hmg", "Bk", "Kan Gazı"]
GORUNTULEME = ["Cr", "Ct", "Mr", "Usg"]
KONSULTASYONLAR = [
    "Dahilye", "Göğüs Hast", "Genel Cerrahi", "Nrş", "KVC", "Kbb",
    "Plastik", "Göz", "Üroloji", "Göğüs C.", "Kardiyoloji", "Nöroloji",
    "Göğüs H.", "Enfeksiyon H.", "Psikiyatri", "Cildiye", "Anestezi", "Radyoloji"
]
YATIS_YERI_SECENEKLERI = ["", "Servis", "1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü"]
VARDIYA_SECENEKLERI = ["", "08.00-16.00", "16.00-24.00", "00.00-08.00"]
SONUC_SECENEKLERI = ["", "DEVİR", "Taburcu", "Ölüm", "T. RED", "KDH"]

# ==========================================
# 3. YARDIMCI FONKSİYONLAR
# ==========================================

def sayfa_basina_kaydir():
    """Sayfayı en üste kaydır."""
    components.html(
        """<script>
            window.parent.document.querySelector('section.main').scrollTo({top: 0, behavior: 'smooth'});
        </script>""",
        height=0
    )

def yatis_saatinden_vardiya_belirle(saat_str):
    """Yatış saati string'ini parse edip vardiya döndürür."""
    if not saat_str or saat_str.strip() in ("-", ""):
        return ""
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
            return ""
    if 8 <= saat_num < 16:
        return "08.00-16.00"
    elif 16 <= saat_num < 24:
        return "16.00-24.00"
    else:
        return "00.00-08.00"

def listeden_hasta_sil(hasta_isim, w_liste_sheet):
    """LİSTE sekmesinde hasta ismini bulup o satırı siler."""
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

# ==========================================
# 4. GOOGLE SHEETS BAĞLANTISI
# ==========================================
@st.cache_resource
def get_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        dict(st.secrets["gcp_service_account"]), scope
    )
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
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

# ==========================================
# 5. SIDEBAR: GERİ AL
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
# 6. BAŞLIK
# ==========================================
st.markdown("## 🏥 Hasta Takip")

# ==========================================
# 7. HASTA SEÇİMİ
# ==========================================
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
    st.success("🎉 Tüm hastalar tamamlandı!")
    st.stop()

# Kalan hasta sayısı badge
st.markdown(
    f'<span class="info-badge info-badge-blue">Kalan: {len(yapilacaklar)} hasta</span>',
    unsafe_allow_html=True
)

secenekler = [f"{x['isim']} | {x['tarih']}" for x in yapilacaklar]
secilen_str = st.selectbox("👇 Sıradaki Hasta", secenekler, label_visibility="visible")
secilen_ad = secilen_str.split(" | ")[0]
secilen_veri = next((x for x in yapilacaklar if x['isim'] == secilen_ad), None)

# Yatış saati bilgisi
if secilen_veri:
    st.markdown(
        f'<span class="info-badge info-badge-orange">⏰ Yatış: {secilen_veri["saat"]}</span>',
        unsafe_allow_html=True
    )

# Bilgileri Doldur butonu
getir_btn = st.button("⬇️ BİLGİLERİ GETİR", type="primary", use_container_width=True)

if getir_btn and secilen_veri:
    # Tarih parse
    t_obj = datetime.now()
    try:
        d_str = secilen_veri['tarih'].split(" ")[0]
        t_obj = datetime.strptime(d_str, "%Y-%m-%d")
    except:
        try:
            t_obj = datetime.strptime(d_str, "%d.%m.%Y")
        except:
            pass

    # Vardiya otomatik belirleme
    vardiya = yatis_saatinden_vardiya_belirle(secilen_veri['saat'])

    # Session state'e kaydet
    st.session_state["form_isim"] = secilen_veri['isim']
    st.session_state["form_tarih"] = t_obj
    st.session_state["form_karar_suresi"] = secilen_veri.get('karar', '')
    st.session_state["form_transfer_suresi"] = secilen_veri.get('transfer', '')
    st.session_state["form_vardiya"] = vardiya
    st.session_state["form_loaded"] = True

    st.toast("✅ Bilgiler çekildi!", icon="✅")

st.markdown("---")

# ==========================================
# 8. MOBİL FORM (EXPANDER YAPISI)
# ==========================================
with st.form("mobil_form", clear_on_submit=False):

    # ============================================================
    # EXPANDER 1: 👤 TEMEL VE VİTAL BİLGİLER
    # ============================================================
    with st.expander("👤 Temel ve Vital Bilgiler", expanded=True):

        # --- İsim ---
        form_isim = st.text_input(
            "Hasta Adı Soyadı",
            value=st.session_state.get("form_isim", ""),
            key="w_isim",
            placeholder="Hasta adı..."
        )

        # --- Tarih ve Cinsiyet (2 sütun) ---
        col_t, col_c = st.columns(2)
        with col_t:
            default_tarih = st.session_state.get("form_tarih", datetime.now())
            form_tarih = st.date_input(
                "📅 Tarih",
                value=default_tarih,
                key="w_tarih",
                format="DD.MM.YYYY"
            )
        with col_c:
            form_cinsiyet = st.selectbox(
                "⚧ Cinsiyet",
                ["", "E", "K"],
                key="w_cinsiyet"
            )

        # --- Yaş (tek satır) ---
        form_yas = st.number_input(
            "🎂 Yaş",
            min_value=0, max_value=150, value=0, step=1,
            key="w_yas"
        )

        st.markdown("##### Vital Bulgular")

        # --- Ateş ve Nabız (2 sütun) ---
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            form_ates = st.number_input(
                "🌡️ Ateş",
                min_value=30.0, max_value=45.0,
                value=36.5, step=0.1, format="%.1f",
                key="w_ates"
            )
        with col_v2:
            form_nabiz = st.number_input(
                "💓 Nabız",
                min_value=0, max_value=300,
                value=80, step=1,
                key="w_nabiz"
            )

        # --- Sistolik ve Diyastolik (2 sütun) ---
        col_v3, col_v4 = st.columns(2)
        with col_v3:
            form_sistolik = st.number_input(
                "🔴 Sistolik TA",
                min_value=0, max_value=400,
                value=120, step=1,
                key="w_sistolik"
            )
        with col_v4:
            form_diyastolik = st.number_input(
                "🔵 Diyastolik TA",
                min_value=0, max_value=300,
                value=80, step=1,
                key="w_diyastolik"
            )

        # --- SpO2 ve GKS (2 sütun) ---
        col_v5, col_v6 = st.columns(2)
        with col_v5:
            form_spo2 = st.number_input(
                "🫁 SpO2",
                min_value=0, max_value=100,
                value=98, step=1,
                key="w_spo2"
            )
        with col_v6:
            form_gks = st.number_input(
                "🧠 GKS",
                min_value=3, max_value=15,
                value=15, step=1,
                key="w_gks"
            )

        # --- Başvuru Şikayeti ---
        form_sikayet = st.text_input(
            "📋 Başvuru Şikayeti",
            key="w_sikayet",
            placeholder="Şikayet yazın..."
        )

    # ============================================================
    # EXPANDER 2: 🏥 TIBBİ DURUM
    # ============================================================
    with st.expander("🏥 Tıbbi Durum", expanded=False):

        # --- Ek Hastalıklar (multiselect) ---
        form_ek_hastaliklar = st.multiselect(
            "🩺 Ek Hastalıklar",
            options=EK_HASTALIKLAR,
            default=[],
            key="w_ek_hastaliklar",
            placeholder="Seçin..."
        )

        # --- Entübasyon ve İnotrop (2 sütun toggle) ---
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            form_entubasyon = st.checkbox("🫁 Entübasyon", key="w_entubasyon")
        with col_e2:
            form_inotrop = st.checkbox("💉 İnotrop", key="w_inotrop")

        # --- Sorun Durumları (multiselect) ---
        form_sorunlar = st.multiselect(
            "⚠️ Sorun Durumları",
            options=SORUN_DURUMLARI,
            default=[],
            key="w_sorunlar",
            placeholder="Varsa seçin..."
        )

        # --- Vardiya (selectbox - otomatik dolu) ---
        default_vardiya_idx = 0
        oto_vardiya = st.session_state.get("form_vardiya", "")
        if oto_vardiya in VARDIYA_SECENEKLERI:
            default_vardiya_idx = VARDIYA_SECENEKLERI.index(oto_vardiya)

        form_vardiya = st.selectbox(
            "🕐 Vardiya",
            options=VARDIYA_SECENEKLERI,
            index=default_vardiya_idx,
            key="w_vardiya"
        )

        # --- Yatış Yeri (selectbox) ---
        form_yatis_yeri = st.selectbox(
            "🏨 Yatış Yeri",
            options=YATIS_YERI_SECENEKLERI,
            key="w_yatis_yeri"
        )

    # ============================================================
    # EXPANDER 3: 🔬 TETKİK VE KONSÜLTASYON
    # ============================================================
    with st.expander("🔬 Tetkik ve Konsültasyon", expanded=False):

        # --- Laboratuvar (multiselect) ---
        form_lab = st.multiselect(
            "🧪 Laboratuvar",
            options=LABORATUVAR,
            default=[],
            key="w_lab",
            placeholder="İstenen tetkikleri seçin..."
        )

        # --- Maliyet L ---
        form_maliyet_l = st.text_input(
            "💰 Maliyet L",
            key="w_maliyet_l",
            placeholder="Opsiyonel"
        )

        # --- Görüntüleme (multiselect) ---
        form_goruntuleme = st.multiselect(
            "📷 Görüntüleme",
            options=GORUNTULEME,
            default=[],
            key="w_goruntuleme",
            placeholder="İstenen görüntülemeleri seçin..."
        )

        # --- Maliyet G ---
        form_maliyet_g = st.text_input(
            "💰 Maliyet G",
            key="w_maliyet_g",
            placeholder="Opsiyonel"
        )

        # --- Konsültasyonlar (multiselect) ---
        form_konsultasyon = st.multiselect(
            "👨‍⚕️ Konsültasyonlar",
            options=KONSULTASYONLAR,
            default=[],
            key="w_konsultasyon",
            placeholder="İstenen bölümleri seçin..."
        )

        # --- Maliyet T ---
        form_maliyet_t = st.text_input(
            "💰 Maliyet T",
            key="w_maliyet_t",
            placeholder="Opsiyonel"
        )

    # ============================================================
    # EXPANDER 4: 📝 SONUÇ VE TABURCULUK
    # ============================================================
    with st.expander("📝 Sonuç ve Taburculuk", expanded=False):

        # --- Tanı ve Son Tanı ---
        form_tani = st.text_input(
            "🏷️ Tanısı",
            key="w_tani",
            placeholder="Tanı yazın..."
        )
        form_son_tani = st.text_input(
            "🏷️ Son Tanısı",
            key="w_son_tani",
            placeholder="Son tanı yazın..."
        )

        # --- Süreler (2 sütun) ---
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            form_karar_suresi = st.text_input(
                "⏱️ Karar Süresi",
                value=st.session_state.get("form_karar_suresi", ""),
                key="w_karar_suresi",
                placeholder="dk"
            )
        with col_s2:
            form_transfer_suresi = st.text_input(
                "⏱️ Transfer Süresi",
                value=st.session_state.get("form_transfer_suresi", ""),
                key="w_transfer_suresi",
                placeholder="dk"
            )

        # --- Sonuç (selectbox) ---
        form_sonuc = st.selectbox(
            "🎯 Sonuç",
            options=SONUC_SECENEKLERI,
            key="w_sonuc"
        )

    # ============================================================
    # KAYDET BUTONU
    # ============================================================
    st.markdown("")  # Boşluk
    kaydet_btn = st.form_submit_button(
        "✅ VERİYİ KAYDET",
        type="primary",
        use_container_width=True
    )

# ==========================================
# PAS GEÇ BUTONLARI (form dışında)
# ==========================================
st.markdown("#### 🚫 Pas Geç")
pas_col1, pas_col2 = st.columns(2)
pas_eksik_btn = pas_col1.button("📋 VERİ EKSİK", use_container_width=True)
pas_sevk_btn = pas_col2.button("🚑 SEVK", use_container_width=True)

# ==========================================
# 9. VERİ KAYDETME MANTIĞI
# ==========================================

def form_verilerini_topla():
    """
    Formdaki tüm widget değerlerini bir dictionary'ye toplar.
    Key: Excel header adı, Value: yazılacak değer
    """
    veri = {}

    # --- Temel Bilgiler ---
    veri["isim"] = form_isim
    veri["Tarih"] = form_tarih
    veri["Yaş"] = form_yas
    veri["Cinsiyet"] = form_cinsiyet

    # --- Vital Bulgular ---
    veri["Ateş"] = form_ates
    veri["Sistolik Tansiyon"] = form_sistolik
    veri["Diyastolik Tansiyon"] = form_diyastolik
    veri["Nabız"] = form_nabiz
    veri["SpO2"] = form_spo2
    veri["GKS"] = form_gks

    # --- Başvuru Şikayeti ---
    veri["Başvuru Şikayeti"] = form_sikayet

    # --- Ek Hastalıklar (multiselect -> 1/0 mapping) ---
    for h in EK_HASTALIKLAR:
        veri[h] = 1 if h in form_ek_hastaliklar else 0

    # --- Entübasyon / İnotrop ---
    veri["Entübasyon"] = 1 if form_entubasyon else 0
    veri["İnotrop"] = 1 if form_inotrop else 0

    # --- Sorun Durumları (multiselect -> 1/0 mapping) ---
    for s in SORUN_DURUMLARI:
        veri[s] = 1 if s in form_sorunlar else 0

    # --- Laboratuvar (multiselect -> 1/0 mapping) ---
    for l in LABORATUVAR:
        veri[l] = 1 if l in form_lab else 0

    # --- Görüntüleme (multiselect -> 1/0 mapping) ---
    for g in GORUNTULEME:
        veri[g] = 1 if g in form_goruntuleme else 0

    # --- Konsültasyonlar (multiselect -> 1/0 mapping) ---
    for k in KONSULTASYONLAR:
        veri[k] = 1 if k in form_konsultasyon else 0

    # --- Maliyet alanları ---
    veri["Maaliyet L"] = form_maliyet_l
    veri["MALİYET G"] = form_maliyet_g
    veri["MAALİYET T"] = form_maliyet_t

    # --- Süreler ---
    veri["Yatış Kararı verilme süresi"] = form_karar_suresi
    veri["Yatış kar.arı sonrası transver süresi"] = form_transfer_suresi

    # --- Tanılar ---
    veri["Tanısı"] = form_tani
    veri["SON TANISI"] = form_son_tani

    # --- Yatış Yeri (selectbox -> her biri 1/0) ---
    for yy in ["Servis", "1. Basamak Ybü", "2. Basamak Ybü", "3. Basamak Ybü"]:
        veri[yy] = 1 if form_yatis_yeri == yy else 0

    # --- Vardiya (selectbox -> her biri 1/0) ---
    for v in ["08.00-16.00", "16.00-24.00", "00.00-08.00"]:
        veri[v] = 1 if form_vardiya == v else 0

    # --- Sonuç (selectbox -> her biri 1/0) ---
    for sn in ["DEVİR", "Taburcu", "Ölüm", "T. RED", "KDH"]:
        veri[sn] = 1 if form_sonuc == sn else 0

    return veri


def satir_olustur(veri_dict, headers):
    """
    Headers sırasına göre yeni_satir listesi oluşturur.
    SIFIR_LIST'tekiler otomatik "0", boş başlıklar "" olur.
    """
    yeni_satir = []
    for baslik in headers:
        b_stripped = baslik.strip()

        # Boş başlık -> boş string
        if not b_stripped:
            yeni_satir.append("")
            continue

        # İlk sütun (Veri Girişi ve Depolama) -> boş
        if b_stripped == "Veri Girişi ve Depolama":
            yeni_satir.append("")
            continue

        # SIFIR_LIST'teki başlıklar -> otomatik "0"
        if b_stripped in SIFIR_LIST:
            yeni_satir.append("0")
            continue

        # Dictionary'den değer al
        val = veri_dict.get(b_stripped, "")

        # Tarih formatla
        if hasattr(val, 'strftime'):
            val = val.strftime("%d.%m.%Y")

        yeni_satir.append(str(val))

    return yeni_satir


# ==========================================
# 10. KAYDET İŞLEMİ
# ==========================================
if kaydet_btn:
    try:
        veri_dict = form_verilerini_topla()
        yeni_satir = satir_olustur(veri_dict, headers)

        w_veri.append_row(yeni_satir)

        # Listeden hastayı sil
        silme_basarili = listeden_hasta_sil(secilen_ad, w_liste)

        if silme_basarili:
            st.success("✅ Kaydedildi ve listeden silindi!")
        else:
            st.success("✅ Kaydedildi! (Listeden silme yapılamadı, kontrol edin.)")

        st.balloons()

        # Session state temizle
        for key in list(st.session_state.keys()):
            if key.startswith("w_") or key.startswith("form_"):
                del st.session_state[key]

        sayfa_basina_kaydir()
        time.sleep(1.5)
        st.rerun()

    except Exception as e:
        st.error(f"❌ Kayıt Hatası: {e}")

# ==========================================
# 11. PAS GEÇ İŞLEMLERİ
# ==========================================
if pas_eksik_btn:
    try:
        w_atlanan.append_row([secilen_ad, datetime.now().strftime("%Y-%m-%d"), "Veri Eksik"])
        silme_basarili = listeden_hasta_sil(secilen_ad, w_liste)
        st.warning(f"⏩ {secilen_ad} atlandı. (Sebep: Veri Eksik)")
        sayfa_basina_kaydir()
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")

if pas_sevk_btn:
    try:
        w_atlanan.append_row([secilen_ad, datetime.now().strftime("%Y-%m-%d"), "Dışarıya Sevk"])
        silme_basarili = listeden_hasta_sil(secilen_ad, w_liste)
        st.warning(f"⏩ {secilen_ad} atlandı. (Sebep: Dışarıya Sevk)")
        sayfa_basina_kaydir()
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Hata: {e}")
