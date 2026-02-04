import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- AYARLAR ---
SHEET_ADI = "Hasta_Takip_Sistemi"

st.set_page_config(page_title="Pro Hasta Takip", layout="wide", page_icon="🏥")
st.title("🏥 Excel Tarzı Hızlı Veri Girişi")

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_data():
    try:
        client = get_connection()
        sh = client.open(SHEET_ADI)
        w_veri = sh.worksheet("Veri")
        w_liste = sh.worksheet("Liste")
        
        # Başlıklar
        data_veri = w_veri.get_all_values()
        headers = []
        if len(data_veri) > 1:
            headers = data_veri[1] # 2. Satır başlıklar
        
        # Liste verileri
        data_liste = w_liste.get_all_values()
        
        # En son kaydedilen ismi bul
        son_kayit_isim = None
        if len(data_veri) > 2:
            son_satir = data_veri[-1]
            if len(son_satir) > 4:
                son_kayit_isim = str(son_satir[4]).strip()
        
        return w_veri, headers, data_liste, son_kayit_isim
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None, [], [], None

# --- PROGRAM ---
w_veri, headers, tum_veriler, son_kayit_isim = get_data()

if w_veri:
    
    # 1. HASTA LİSTESİNİ HAZIRLA (Önceki mantıkla aynı)
    temiz_liste = []
    for row in tum_veriler[3:]: # İlk 3 satır çöp
        if len(row) > 6:
            isim = str(row[4]).strip()
            tarih = str(row[6]).strip()
            if len(isim) > 2 and "Sütun" not in isim:
                temiz_liste.append({"isim": isim, "tarih": tarih})
    
    # Kimi seçelim?
    aday_listesi = []
    if son_kayit_isim:
        bulunan_index = -1
        for i, h in enumerate(temiz_liste):
            if h["isim"] == son_kayit_isim:
                bulunan_index = i
                break
        
        if bulunan_index != -1:
            start = max(0, bulunan_index - 5)
            end = min(len(temiz_liste), bulunan_index + 10)
            aday_listesi = temiz_liste[start:end]
            st.info(f"Son kayıt: **{son_kayit_isim}**. Liste buna göre sıralandı.")
        else:
            aday_listesi = temiz_liste[:15]
    else:
        aday_listesi = temiz_liste[:15]

    # Seçim Kutusu
    secenekler = [f"{h['isim']} | {h['tarih']}" for h in aday_listesi]
    if not secenekler:
        st.error("Liste boş.")
        st.stop()
        
    secilen_str = st.selectbox("👇 Hasta Seçiniz:", secenekler)
    secilen_isim = secilen_str.split(" | ")[0]
    secilen_tarih = secilen_str.split(" | ")[1]

    st.markdown("---")

    # 2. TABLO İÇİN TEK SATIRLIK VERİ HAZIRLA
    # Pandas DataFrame oluşturacağız. Bu Excel'deki bir satır gibidir.
    
    row_data = {}
    
    for baslik in headers:
        if not baslik.strip(): continue
        
        # -- OTOMATİK DOLDURMA KURALLARI --
        
        # İSİM
        if "isim" in baslik.lower() or "ad soyad" in baslik.lower():
            row_data[baslik] = secilen_isim
            
        # TARİH (Formatı koru)
        elif "tarih" in baslik.lower():
            row_data[baslik] = secilen_tarih
            
        # CİNSİYET (Boş başlasın)
        elif "cinsiyet" in baslik.lower():
            row_data[baslik] = ""
            
        # CHECKBOX (Hastalıklar -> False/True olur tabloda)
        elif baslik in ["HT", "DM", "KOAH", "KBY", "KAH", "AF", "SVH", "Malignite"]:
            row_data[baslik] = False
            
        # SAYISAL DEĞERLER (0 olarak gelsin)
        # Laboratuvarlar, Ateş, Nabız vs.
        elif any(x in baslik.lower() for x in ['yaş', 'ateş', 'nabız', 'tansiyon', 'spo2']) or "sütun" not in baslik.lower():
            # Eğer not/açıklama ise boş kalsın
            if any(x in baslik.lower() for x in ['bölüm', 'yatış', 'açıklama', 'not']):
                row_data[baslik] = ""
            else:
                # Geri kalan her şey (Lab sonuçları) 0 olsun
                row_data[baslik] = "0"
        
        else:
             row_data[baslik] = ""

    # Tek satırlık DataFrame oluştur
    df = pd.DataFrame([row_data])

    # 3. TABLOYU GÖSTER VE DÜZENLE (Excel Gibi)
    st.write("📝 **Verileri aşağıdaki tabloda düzenleyin:** (Hücreye çift tıklayıp yazabilirsiniz)")
    
    # column_config ile onay kutuları ve metinleri özelleştiriyoruz
    edited_df = st.data_editor(
        df,
        num_rows="fixed", # Yeni satır eklenmesin, sadece bu hasta
        hide_index=True,  # Yandaki 0 numarasını gizle
        use_container_width=True
    )

    st.markdown("---")
    
    # 4. KAYDET BUTONU
    if st.button("✅ BU SATIRI KAYDET", type="primary"):
        try:
            # Düzenlenmiş veriyi al
            kaydedilecek_veri = edited_df.iloc[0].to_dict()
            
            yeni_satir = []
            
            # Başlık sırasına göre verileri dizele
            for baslik in headers:
                if not baslik.strip():
                    yeni_satir.append("")
                else:
                    deger = kaydedilecek_veri.get(baslik, "")
                    
                    # True/False (Checkbox) ise 1/0 yap
                    if isinstance(deger, bool):
                        deger = 1 if deger else 0
                    
                    yeni_satir.append(str(deger))
            
            # Google Sheets'e gönder
            w_veri.append_row(yeni_satir)
            st.success(f"✅ Başarılı! **{secilen_isim}** verileri kaydedildi.")
            st.balloons()
            
            # 2 saniye sonra sayfayı yenile ki yeni seçim yapabilesin
            import time
            time.sleep(2)
            st.rerun()
            
        except Exception as e:
            st.error(f"Kayıt Hatası: {e}")

else:
    st.warning("Veritabanına bağlanılamadı.")
