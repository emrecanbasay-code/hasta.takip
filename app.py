with st.form("dikey_form", clear_on_submit=False):
        st.write(f"### 📋 Kayıt Ekranı")
        
        for i, baslik in enumerate(headers):
            if not baslik: continue
            
            # --- 1. KRİTİK DÜZELTME: BAŞLIK TEMİZLİĞİ ---
            # Excel'deki alt satırları (newline) boşluğa çevir
            baslik_clean = baslik.strip().replace("\n", " ")
            
            # Türkçe karakter sorununu çözmek için özel lower() işlemi
            # İ -> i, I -> ı dönüşümü yapıp sonra küçültüyoruz
            baslik_lower = baslik_clean.replace("İ", "i").replace("I", "ı").lower()
            
            # Görsel olarak ekrana temiz halini yaz
            c1, c2 = st.columns([1.5, 3])
            c1.markdown(f"<div class='etiket-box'>{baslik_clean}:</div>", unsafe_allow_html=True)
            
            key_name = f"in_{i}_{baslik_clean}"
            
            with c2:
                # 1. CHECKBOX KONTROLÜ
                if baslik_clean in [x.strip() for x in CHECKBOX_LIST]: 
                    chk = st.checkbox("Evet / Var", key=key_name)
                    input_values[baslik] = 1 if chk else 0
                
                # 2. İSİM (Eşleşme kapsamı genişletildi)
                elif any(x in baslik_lower for x in ['isim', 'adı soyadı', 'hasta adı']):
                    input_values[baslik] = st.text_input("İsim", key="form_isim_input", value=st.session_state['form_isim'], label_visibility="collapsed")
                
                # 3. TARİH
                elif "tarih" in baslik_lower:
                    input_values[baslik] = st.date_input("Tarih", key="form_tarih_input", value=st.session_state['form_tarih'], label_visibility="collapsed")
                
                # 4. YATIŞ KARAR SÜRESİ (Nokta vs. hatalarına karşı esnek arama)
                # "karar" VE "süre" kelimeleri geçiyorsa buraya girer
                elif "karar" in baslik_lower and "süre" in baslik_lower:
                     input_values[baslik] = st.text_input("Süre", key="form_karar_input", value=st.session_state['form_karar'], label_visibility="collapsed")

                # 5. TRANSFER SÜRESİ
                # "transfer" veya "transver" (yazım hatası ihtimali) VE "süre" geçiyorsa
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
                
                # 9. Diğerleri (Eşleşmeyenler buraya düşer ve 0 yazar)
                else:
                    input_values[baslik] = st.text_input("Sonuç", value="0", key=key_name, label_visibility="collapsed")
            
            st.markdown("<div class='row-container'></div>", unsafe_allow_html=True)

        st.markdown("---")
        
        col_submit, col_pass = st.columns([3, 1])
        kaydet_btn = col_submit.form_submit_button("✅ KAYDET", type="primary", use_container_width=True)
