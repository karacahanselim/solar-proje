import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="SolarVizyon - Profesyonel GES Analizi", 
    layout="wide", 
    page_icon="☀️"
)

# --- YARDIMCI FONKSİYON: TÜRKÇE PARA FORMATI ---
def tr_fmt(sayi):
    if sayi is None: return "0"
    return f"{int(sayi):,.0f}".replace(",", ".")

# --- VERİTABANI KAYIT FONKSİYONU ---
def veritabanina_kaydet(ad, firma, tel, email, sehir, sistem_tipi, tuketim_bilgisi, notlar):
    try:
        try:
            # Sır Odasından (Secrets) anahtarı al
            json_icerik = st.secrets["gcp_service_account"]["json_file"]
            creds_dict = json.loads(json_icerik)
        except:
            return False # Localde çalışırken sessizce geç
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("SolarMusteriler").sheet1
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
        # Kayıt Sırası: Tarih, Ad, Firma, Tel, Email, Şehir, Sistem Tipi, Tüketim, Notlar
        sheet.append_row([tarih, ad, firma, tel, email, sehir, sistem_tipi, tuketim_bilgisi, notlar])
        return True
    except:
        return False

# --- BAŞLIK VE GÖRSEL ---
c_header1, c_header2 = st.columns([1, 3])
with c_header1:
    st.image("https://images.unsplash.com/photo-1509391366360-2e959784a276?q=80&w=3264&auto=format&fit=crop", use_container_width=True)
with c_header2:
    st.title("☀️ SolarVizyon | Mühendislik Tabanlı GES Analizi")
    st.markdown("""
    ### Bilimsel Veri, Gerçekçi Sonuçlar 📐
    Sadece fatura tutarını değil, **enerji tüketiminizi (kWh)** ve **sistem altyapısını (On-Grid/Off-Grid)** analiz ederek en doğru fizibilite raporunu sunuyoruz.
    """)

st.markdown("---")

# --- GİRİŞ PARAMETRELERİ ---
st.subheader("📝 Teknik Veri Girişi")

col_form1, col_form2 = st.columns(2, gap="medium")

with col_form1:
    st.markdown("#### 🏠 Lokasyon ve Sistem Tipi")
    sehir = st.selectbox("📍 Şehir Seçiniz", ["İstanbul", "Ankara", "İzmir", "Antalya", "Kayseri", "Konya", "Gaziantep", "Van", "Adana", "Trabzon"])
    
    # Sistem Tipi
    sistem_tipi = st.radio("Sistem Tipi Nedir?", 
             ["On-Grid (Şebeke Bağlantılı)", "Off-Grid (Akü Depolamalı / Bağ Evi)"],
             help="On-Grid: Şehir şebekesi vardır, satış yapılabilir. Off-Grid: Şebeke yoktur, akü zorunludur.")

    # Akü Seçimi (Sadece Off-Grid ise görünür)
    if "Off-Grid" in sistem_tipi:
        aku_tipi = st.selectbox("🔋 Akü Teknolojisi Seçimi", 
                                ["Jel Akü (Ekonomik - Ömür ~4 Yıl)", "Lityum İyon (Premium - Ömür ~10 Yıl)"])
        st.caption("⚠️ **Mühendis Notu:** Jel aküler ucuzdur ama 4-5 yılda bir değişim gerektirir.")
    else:
        aku_tipi = "Yok" 

    st.markdown("#### 📊 Tüketim Verisi")
    # Tüketim Giriş Yöntemi
    hesap_yontemi = st.radio("Tüketimi Nasıl Gireceksiniz?", 
                             ["Aylık Fatura Tutarı (TL)", "Günlük Ortalama Tüketim (kWh)", "Aylık Toplam Tüketim (kWh)"])
    
    if "TL" in hesap_yontemi:
        girdi_deger = st.number_input("Aylık Ortalama Fatura (TL)", value=1000, step=50)
        elektrik_birim_fiyat = 2.60 # Varsayılan
    elif "Günlük" in hesap_yontemi:
        girdi_deger = st.number_input("Günlük Ortalama Tüketim (kWh)", value=10.0, step=0.5, help="Faturada 'Günlük Ort.' yazar.")
        elektrik_birim_fiyat = 2.60
    else:
        girdi_deger = st.number_input("Aylık Toplam Tüketim (kWh)", value=300, step=50)
        elektrik_birim_fiyat = 2.60

with col_form2:
    st.markdown("#### ⚙️ Çatı ve Panel Detayları")
    
    # Alan Sorusu (Dinamik Etiket)
    alan_label = "🏠 Net Çatı Alanı (m²)" if "On-Grid" in sistem_tipi else "🌱 Kullanılabilir Arazi/Çatı Alanı (m²)"
    cati_alani = st.number_input(alan_label, value=80, help="Gölge düşmeyen, kullanılabilir net alan.")
    
    # Yön Seçimi
    if "On-Grid" in sistem_tipi:
        yon_secimi = st.selectbox("🧭 Alanın Cephesi", ["Güney (En İyi)", "Güney-Doğu (İyi)", "Güney-Batı (İyi)", "Doğu (Orta)", "Batı (Orta)", "Kuzey (Tavsiye Edilmez)"])
    else:
        st.success("✅ **Off-Grid Avantajı:** Paneller güneye bakacak şekilde konumlandırılır.")
        yon_secimi = "Güney (En İyi)"
    
    panel_tipi = st.radio("Panel Teknolojisi", ["Standart Panel (Poly)", "Premium Panel (Mono Perc)"], horizontal=True)
    
    st.markdown("#### 📈 Ekonomik Parametreler")
    elektrik_zam_beklentisi = st.slider("Yıllık Enerji Fiyat Artış Beklentisi (%)", 0, 100, 40)
    
    # Bilgi Notu (Güncel)
    st.info("💡 **Bilgi:** Ekim 2025 TÜİK verilerine göre yıllık enflasyon **%32,87** seviyesindedir. Hesabınızı buna göre veya kendi beklentinize göre yapabilirsiniz.")

# --- GELİŞMİŞ AYARLAR ---
with st.expander("🛠️ Gelişmiş Ayarlar (Döviz & Birim Fiyat)"):
    c1, c2 = st.columns(2)
    dolar_kuru = c1.number_input("Dolar Kuru ($)", value=34.50, step=0.1)
    if "TL" not in hesap_yontemi:
        elektrik_birim_fiyat = c2.number_input("Elektrik Birim Fiyatı (TL/kWh)", value=2.60, step=0.1)
    
    st.markdown("**🏦 Finansman**")
    kredi_kullanimi = st.checkbox("Kredi Kullanılacak mı?", value=False)
    if kredi_kullanimi:
        faiz_orani = st.number_input("Aylık Faiz (%)", value=3.5, step=0.1)
        vade_sayisi = st.slider("Vade (Ay)", 12, 48, 24)

st.markdown("---")

# --- HESAPLA BUTONU ---
if st.button("🚀 ANALİZİ BAŞLAT", type="primary", use_container_width=True):
    st.session_state.hesaplandi = True
else:
    if 'hesaplandi' not in st.session_state:
        st.session_state.hesaplandi = False

# --- MÜHENDİSLİK HESAPLAMALARI (CORE ENGINE) ---
if st.session_state.hesaplandi:
    
    # 1. TÜKETİM ANALİZİ (kWh Hesabı)
    if "TL" in hesap_yontemi:
        aylik_tuketim_kwh = girdi_deger / elektrik_birim_fiyat
    elif "Günlük" in hesap_yontemi:
        aylik_tuketim_kwh = girdi_deger * 30
    else:
        aylik_tuketim_kwh = girdi_deger
    
    yillik_tuketim_kwh = aylik_tuketim_kwh * 12
    
    # 2. LOKASYON VE VERİM VERİLERİ
    gunes_verileri = { "İstanbul": 3.8, "Ankara": 4.2, "İzmir": 4.6, "Antalya": 4.9, "Kayseri": 4.7, "Konya": 4.6, "Gaziantep": 4.8, "Van": 5.0, "Adana": 4.8, "Trabzon": 3.6 }
    mgm_verileri = { "İstanbul": 5.1, "Ankara": 6.7, "İzmir": 8.1, "Antalya": 8.1, "Kayseri": 7.0, "Konya": 7.4, "Gaziantep": 7.0, "Van": 7.9, "Adana": 7.6, "Trabzon": 4.5 }
    yon_kayip_tablosu = { "Güney (En İyi)": 0, "Güney-Doğu (İyi)": 5, "Güney-Batı (İyi)": 5, "Doğu (Orta)": 15, "Batı (Orta)": 15, "Kuzey (Tavsiye Edilmez)": 35 }
    
    gunluk_isinim = gunes_verileri[sehir]
    secilen_yon_kaybi = yon_kayip_tablosu[yon_secimi]
    
    # Panel Özellikleri
    verim_katsayisi = 0.21 if "Premium" in panel_tipi else 0.17 # m2 başına kW
    panel_gucu_watt = 550 if "Premium" in panel_tipi else 400   # Tek panel gücü
    
    # 3. SİSTEM BOYUTLANDIRMA
    # Hedef: Tüketimi karşılamak (+%20 marj)
    hedef_guc = (yillik_tuketim_kwh * 1.2) / (gunluk_isinim * 365 * 0.85) # Değişken ismi düzeltildi
    max_cati_guc = cati_alani * verim_katsayisi
    
    # Mantık: Çatıyı aşamazsın. Off-Grid ise ihtiyacı aşma (akü maliyeti).
    if "Off-Grid" in sistem_tipi:
        kurulu_guc_kw = min(hedef_guc, max_cati_guc)
    else:
        # On-Grid'de çatı büyükse ve müşteri isterse doldurabiliriz ama şimdilik optimizasyon yapalım
        kurulu_guc_kw = min(hedef_guc, max_cati_guc) # Ekonomik mod varsayılan

    # Panel Sayısı (Tamsayı olmak zorunda)
    # Formül: (Kurulu Güç * 1000) / Panel Watt Gücü
    panel_sayisi = max(1, int((kurulu_guc_kw * 1000) / panel_gucu_watt))
    # Gücü panel sayısına göre revize et (Gerçekçi olsun)
    kurulu_guc_kw = (panel_sayisi * panel_gucu_watt) / 1000

    # 4. MALİYET ANALİZİ
    baz_maliyet_usd = 750 if "Premium" in panel_tipi else 600
    
    # Ölçek Ekonomisi (Küçük sistem pahalıdır)
    if kurulu_guc_kw < 5: birim_maliyet_usd = baz_maliyet_usd * 1.3
    elif kurulu_guc_kw < 10: birim_maliyet_usd = baz_maliyet_usd * 1.1
    else: birim_maliyet_usd = baz_maliyet_usd
    
    donanim_maliyeti_usd = kurulu_guc_kw * birim_maliyet_usd
    aku_maliyeti_usd = 0
    
    if "Off-Grid" in sistem_tipi:
        # Akü Hesabı: Günlük tüketim * 1.5 gün otonomi
        gunluk_tuketim_kwh = aylik_tuketim_kwh / 30
        aku_kapasitesi_kwh = gunluk_tuketim_kwh * 1.5
        aku_birim_fiyat = 250 if "Jel" in aku_tipi else 600
        aku_maliyeti_usd = aku_kapasitesi_kwh * aku_birim_fiyat
        sistem_notu = f"🔋 **Off-Grid Sistem:** {aku_kapasitesi_kwh:.1f} kWh kapasiteli akü bankası dahil edilmiştir."
    else:
        sistem_notu = "⚡ **On-Grid Sistem:** Şebeke bağlantılı, aküsüz sistem."

    toplam_yatirim_usd = donanim_maliyeti_usd + aku_maliyeti_usd
    yatirim_maliyeti_tl = toplam_yatirim_usd * dolar_kuru

    # 5. ÜRETİM VE TASARRUF
    yillik_uretim_kwh = kurulu_guc_kw * gunluk_isinim * 365 * ((100-secilen_yon_kaybi)/100) * 0.85
    aylik_ortalama_uretim_tl = (yillik_uretim_kwh / 12) * elektrik_birim_fiyat

    # 6. DİNAMİK ROI VE NAKİT AKIŞI (ENFLASYONLU)
    amortisman_yil = 0
    kasa_bakiyesi = -yatirim_maliyeti_tl
    nakit_akisi_listesi = []
    
    # Parametreler
    zam_carpani = 1 + (elektrik_zam_beklentisi / 100)
    panel_degradasyon = 0.995 # Her yıl %0.5 verim kaybı
    
    # Bakım Giderleri
    inverter_degisim_maliyeti = kurulu_guc_kw * 150 * dolar_kuru # 12. Yıl
    aku_degisim_maliyeti = aku_maliyeti_usd * dolar_kuru # 5 veya 10 yılda bir
    aku_omru = 5 if "Off-Grid" in sistem_tipi and "Jel" in aku_tipi else 10
    
    for yil in range(1, 26):
        # Gelir (Enflasyon ve Eskime Dahil)
        yillik_gelir = (yillik_uretim_kwh * (panel_degradasyon**yil)) * (elektrik_birim_fiyat * (zam_carpani**yil))
        
        # Giderler
        yillik_gider = 0
        if yil == 12: yillik_gider += inverter_degisim_maliyeti # İnverter
        if "Off-Grid" in sistem_tipi and (yil % aku_omru == 0) and yil != 20: # Akü
            yillik_gider += aku_degisim_maliyeti
            
        kasa_bakiyesi = kasa_bakiyesi + yillik_gelir - yillik_gider
        nakit_akisi_listesi.append(kasa_bakiyesi)
        
        # ROI Bulma (İlk kez artıya geçtiği an)
        if kasa_bakiyesi > 0 and amortisman_yil == 0:
            onceki_bakiye = abs(kasa_bakiyesi - (yillik_gelir - yillik_gider))
            net_gelir = yillik_gelir - yillik_gider
            amortisman_yil = (yil - 1) + (onceki_bakiye / net_gelir)
            
    if amortisman_yil == 0: amortisman_yil = 25

    # --- ÇIKTI EKRANI ---
    st.divider()
    st.subheader("🔍 Mühendislik Analiz Sonuçları")
    st.info(sistem_notu)
    
    # 4 ANA METRİK
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Panel Sayısı", f"{panel_sayisi} Adet", help=f"Toplam Güç: {kurulu_guc_kw:.2f} kWp ({panel_gucu_watt}W paneller)")
    c2.metric("Tahmini Maliyet", f"{tr_fmt(yatirim_maliyeti_tl)} TL")
    c3.metric("Aylık Kazanç (Ort.)", f"{tr_fmt(aylik_ortalama_uretim_tl)} TL", delta="Tasarruf")
    c4.metric("Amortisman (ROI)", f"{amortisman_yil:.1f} Yıl")

    # GRAFİKLER
    st.subheader("📉 Finansal Projeksiyon")
    
    tab1, tab2 = st.tabs(["Nakit Akışı (20 Yıl)", "Aylık Üretim Dağılımı"])
    
    with tab1:
        # Nakit Akışı Grafiği
        df_cash = pd.DataFrame({"Yıl": range(1, 26), "Kasa (TL)": nakit_akisi_listesi})
        df_cash["Kasa (TL)"] = df_cash["Kasa (TL)"].astype(int)
        df_cash["Tooltip"] = df_cash["Kasa (TL)"].apply(tr_fmt)
        
        chart = alt.Chart(df_cash).mark_area(color="#27ae60", opacity=0.6).encode(
            x='Yıl:O', y='Kasa (TL):Q', tooltip=['Yıl', alt.Tooltip('Tooltip', title='Bakiye (TL)')]
        ).interactive()
        st.altair_chart(chart, use_container_width=True)
        
        # Uyarılar
        notlar = ["ℹ️ **Notlar:**"]
        notlar.append(f"- 12. Yılda İnverter Değişimi ({tr_fmt(inverter_degisim_maliyeti)} TL) düşülmüştür.")
        if "Off-Grid" in sistem_tipi:
            notlar.append(f"- Her {aku_omru} yılda bir Akü Değişimi ({tr_fmt(aku_degisim_maliyeti)} TL) hesaba katılmıştır.")
        st.markdown("\n".join(notlar))

    with tab2:
        # Aylık Üretim Grafiği
        aylar = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
        oranlar = [0.6, 0.7, 0.9, 1.1, 1.2, 1.3, 1.35, 1.3, 1.15, 0.95, 0.8, 0.65]
        aylik_uretimler = [(yillik_uretim_kwh/12) * x for x in oranlar]
        
        df_aylik = pd.DataFrame({"Ay": aylar, "Üretim (kWh)": aylik_uretimler})
        df_aylik["Üretim (kWh)"] = df_aylik["Üretim (kWh)"].astype(int)
        
        chart_bar = alt.Chart(df_aylik).mark_bar(color="#f39c12").encode(
            x=alt.X('Ay', sort=aylar), y='Üretim (kWh)', tooltip=['Ay', 'Üretim (kWh)']
        )
        st.altair_chart(chart_bar, use_container_width=True)

    # --- İLETİŞİM FORMU ---
    st.markdown("---")
    st.subheader("📞 Detaylı Teklif Alın")
    with st.form("iletisim"):
        c1, c2 = st.columns(2)
        ad = c1.text_input("Ad Soyad")
        firma = c1.text_input("Firma Adı (Opsiyonel)")
        tel = c2.text_input("Telefon")
        email = c2.text_input("E-posta (Opsiyonel)")
        notlar = st.text_area("Notlar (Çatı tipi, özel istekler vb.)")
        
        if st.form_submit_button("✅ ÜCRETSİZ TEKLİF İSTE", type="primary"):
            if ad and tel:
                if veritabanina_kaydet(ad, firma, tel, email, sehir, sistem_tipi, f"{girdi_deger} Birim", notlar):
                    st.success("Talebiniz başarıyla alındı! Uzmanlarımız en kısa sürede dönüş yapacaktır.")
                    st.balloons()
                else:
                    st.error("Bağlantı hatası oluştu. Lütfen daha sonra tekrar deneyiniz.")
            else:
                st.warning("Lütfen Ad Soyad ve Telefon alanlarını doldurunuz.")
