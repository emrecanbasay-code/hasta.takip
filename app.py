with st.form("dikey_form", clear_on_submit=False):
        st.write(f"### 📋 Kayıt Ekranı")
        
        for i, baslik in enumerate(headers):
            if not baslik: continue
            
            # --- 1. KRİTİK DÜZELTME: BAŞLIK TEMİZLİĞİ ---
            baslik_clean = baslik.strip().replace("\n", " ")
            baslik_lower = baslik_clean.replace("İ", "i").replace("I", "ı").lower()
            
            c1, c2 = st.columns([1.5, 3])
            c1.markdown(f"<div class='etiket-box'>{baslik_clean}:</div>", unsafe_allow_html=True)
            
            # Form bileşenleri için benzersiz key üretimi
            # ÖNEMLİ: 'form_isim_input' gibi sabit keyler yerine dinamik keyler kullanmak 
            # bazen Streamlit'in verileri getirdiğinde formu yenilememesine neden olabilir.
            # Ancak sizin durumunuzda session_state'den beslenmesini istediğiniz için 
            # value=st.session_state[...] kullanımı doğrudur.
            
            key_name = f"in_{i}_{baslik_clean}"
            
            with c2:
                # 1. CHECKBOX KONTROLÜ
                if baslik_clean in [x.strip() for x in CHECKBOX_LIST]: 
                    chk = st.checkbox("Evet / Var", key=key_name)
                    input_values[baslik] = 1 if chk else 0
                
                # 2. İSİM (Eşleşme kapsamı genişletildi)
                elif any(x in baslik_lower for x in ['isim', 'adı soyadı', 'hasta adı']):
                    # value kısmını session_state'den alıyoruz. Veri getirildiğinde burası güncellenir.
                    input_values[baslik] = st.text_input("İsim", 
                                                        key=f"isim_{i}", 
                                                        value=st.session_state.get('form_isim', ""), 
                                                        label_visibility="collapsed")
                
                # 3. TARİH
                elif "tarih" in baslik_lower:
                    input_values[baslik] = st.date_input("Tarih", 
                                                        key=f"tarih_{i}", 
                                                        value=st.session_state.get('form_tarih', datetime.date.today()), 
                                                        label_visibility="collapsed")
                
                # 4. YATIŞ KARAR SÜRESİ
                elif "karar" in baslik_lower and "süre" in baslik_lower:
                     input_values[baslik] = st.text_input("Süre", 
                                                         key=f"karar_{i}", 
                                                         value=st.session_state.get('form_karar', ""), 
                                                         label_visibility="collapsed")

                # 5. TRANSFER SÜRESİ
                elif ("transfer" in baslik_lower or "transver" in baslik_lower) and "süre" in baslik_lower:
                     input_values[baslik] = st.text_input("Süre", 
                                                         key=f"transfer_{i}", 
                                                         value=st.session_state.get('form_transfer', ""), 
                                                         label_visibility="collapsed")
                
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
