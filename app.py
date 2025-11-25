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
    page_title="SolarVizyon - Akıllı GES Hesaplayıcı", 
    layout="wide", 
    page_icon="☀️"
)

# --- VERİTABANI BAĞLANTISI (GOOGLE SHEETS) ---
def veritabanina_kaydet(ad, tel, email, sehir, fatura, notlar):
    try:
        # Sır Odasından (Secrets) anahtarı alıyoruz
        # json.loads ile string formatındaki anahtarı sözlüğe çeviriyoruz
        creds_dict = json.loads(st.secrets["gcp_service_account"]["json_file"])
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Dosyayı aç ve yaz
        sheet = client.open("SolarMusteriler").sheet1
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Satır ekle
        sheet.append_row([tarih, ad, tel, email, sehir, fatura, notlar])
        return True
    except Exception as e:
        st.error(f"Veritabanı Hatası: {e}")
        return False

# --- YARDIMCI FONKSİYON ---
def tr_fmt(sayi):
    if sayi is None: return "0"
    return f"{int(sayi):,.0f}".replace(",", ".")

# --- BAŞLIK VE GÖRSEL ---
c_header1, c_header2 = st.columns([1, 3])
with c_header1:
    st.image("https://images.unsplash.com/photo-1509391366360-2e959784a276?q=80&w=3264&auto=format&fit=crop", use_container_width=True)
with c_header2:
    st.title("☀️ SolarVizyon | Enerji ve Finansman Hesaplayıcı")
    st.markdown("""
    ### Geleceğinizi Garantiye Alın 🌍
    Aşağıdaki formu doldurun ve **HESAPLA** butonuna basın. Yapay zeka destekli analizimiz ile **yatırım getirinizi**, **kredi taksitlerinizi** ve **gerçekçi nakit akışınızı** anında hesaplayalım.
    """)

st.markdown("---")

# --- GİRİŞ PARAMETRELERİ ---
st.subheader("📝 Hesaplama Parametreleri")

col_form1, col_form2 = st.columns(2, gap="medium")

with col_form1:
    st.markdown("#### 🏠 Bina ve Tüketim")
    
    kurulum_yeri = st.radio("Kurulum Yeri", ["Çatı Üzeri", "Arazi / Bahçe"], horizontal=True)
    
    sehir = st.selectbox("📍 Şehir Seçiniz", ["İstanbul", "Ankara", "İzmir", "Antalya", "Kayseri", "Konya", "Gaziantep", "Van", "Adana", "Trabzon"])
    fatura = st.number_input("💰 Aylık Elektrik Faturanız (TL)", value=350, step=50)
    
    alan_etiketi = "🏠 Panel Kurulabilir Net Çatı Alanı (m²)" if kurulum_yeri == "Çatı Üzeri" else "🌱 Kullanılabilir Arazi Alanı (m²)"
    alan_ipucu = "Toplam alanı değil; baca, gölge ve engeller düşüldükten sonra kalan NET alanı giriniz."
    cati_alani = st.number_input(alan_etiketi, value=100, help=alan_ipucu)
    st.caption(f"ℹ️ *{alan_ipucu}*")
    
    st.markdown("#### 🎯 Sistem Hedefi")
    sistem_hedefi = st.radio("Amacınız nedir?", ["Sadece Faturamı Sıfırla (Ekonomik)", "Alanı Doldur & Elektrik Sat (Maksimum Kazanç)"])

with col_form2:
    st.markdown("#### ⚙️ Teknik Detaylar")
    if kurulum_yeri == "Çatı Üzeri":
        yon_secimi = st.selectbox("🧭 Çatınız Hangi Yöne Bakıyor?", ["Güney (En İyi)", "Güney-Doğu (İyi)", "Güney-Batı (İyi)", "Doğu (Orta)", "Batı (Orta)", "Kuzey (Tavsiye Edilmez)"])
    else:
        st.success("✅ **Arazi Avantajı:** Paneller arazide otomatik olarak tam **Güney** yönüne bakacak şekilde konumlandırılır.")
        yon_secimi = "Güney (En İyi)"

    panel_tipi = st.radio("Panel Kalitesi", ["Ekonomik Panel (Standart)", "Premium Panel (Daha Güçlü)"], horizontal=True)
    
    st.markdown("#### 📈 Enerji Fiyat Artış Öngörüsü")
    elektrik_zam_beklentisi = st.slider("Yıllık Ort. Artış Beklentisi (%)", 0, 100, 35)
    
    st.info("💡 **Referans Bilgi:** Ekim 2025 itibarıyla açıklanan yıllık enflasyon (TÜFE) **%32,87** seviyesindedir. Hesaplamalarınızda bu oranı veya kendi piyasa beklentinizi baz alabilirsiniz.")
    gelecek_fiyat = 100 * ((1+elektrik_zam_beklentisi/100)**10)
    st.caption(f"ℹ️ **Simülasyon:** Seçtiğiniz senaryoya göre, bugün 100 TL olan birim enerji maliyeti 10 yıl sonra tahminen **{int(gelecek_fiyat)} TL** seviyesinde simüle edilir.")

# --- GELİŞMİŞ AYARLAR ---
with st.expander("🛠️ Gelişmiş Ayarlar & Finansman (İsteğe Bağlı)"):
    c_adv1, c_adv2 = st.columns(2)
    with c_adv1:
        st.markdown("**📊 Piyasa Verileri**")
        dolar_kuru = st.number_input("Dolar Kuru ($)", value=34.50, step=0.1)
        elektrik_birim_fiyat = st.number_input("Elektrik Birim Fiyatı (TL)", value=2.60, step=0.1)
    with c_adv2:
        st.markdown("**🏦 Kredi Seçenekleri**")
        kredi_kullanimi = st.checkbox("Banka Kredisi Kullanacak mısınız?", value=False)
        if kredi_kullanimi:
            faiz_orani = st.number_input("Aylık Faiz Oranı (%)", value=3.5, step=0.1)
            vade_sayisi = st.slider("Vade (Ay)", 12, 48, 24, step=12)

st.markdown("---")

# --- HESAPLA BUTONU ---
if st.button("🚀 HESAPLA VE ANALİZ ET", type="primary", use_container_width=True):
    st.session_state.hesaplandi = True
else:
    if 'hesaplandi' not in st.session_state:
        st.session_state.hesaplandi = False

# --- HESAPLAMA VE SONUÇLAR ---
if st.session_state.hesaplandi:
    
    # 1. VERİ SETLERİ
    gunes_verileri = { "İstanbul": 3.8, "Ankara": 4.2, "İzmir": 4.6, "Antalya": 4.9, "Kayseri": 4.7, "Konya": 4.6, "Gaziantep": 4.8, "Van": 5.0, "Adana": 4.8, "Trabzon": 3.6 }
    mgm_verileri = { "İstanbul": 5.1, "Ankara": 6.7, "İzmir": 8.1, "Antalya": 8.1, "Kayseri": 7.0, "Konya": 7.4, "Gaziantep": 7.0, "Van": 7.9, "Adana": 7.6, "Trabzon": 4.5 }
    aylar_listesi = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    aylik_katsayilar = [0.60, 0.70, 0.90, 1.10, 1.20, 1.30, 1.35, 1.30, 1.15, 0.95, 0.80, 0.65] 
    yon_kayip_tablosu = { "Güney (En İyi)": 0, "Güney-Doğu (İyi)": 5, "Güney-Batı (İyi)": 5, "Doğu (Orta)": 15, "Batı (Orta)": 15, "Kuzey (Tavsiye Edilmez)": 35 }

    # 2. DEĞİŞKENLER
    secilen_yon_kaybi = yon_kayip_tablosu[yon_secimi]
    verim_katsayisi = 0.21 if "Premium" in panel_tipi else 0.17
    maliyet_usd_kw = 750 if "Premium" in panel_tipi else 600
    panel_gucu_watt = 550 if "Premium" in panel_tipi else 400

    # 3. SİSTEM BOYUTLANDIRMA
    aylik_tuketim_kwh = fatura / elektrik_birim_fiyat
    yillik_tuketim_kwh = aylik_tuketim_kwh * 12
    hedef_uretim = yillik_tuketim_kwh * 1.2
    
    gunluk_isinim = gunes_verileri[sehir]
    mgm_degeri = mgm_verileri[sehir]
    toplam_kayip_orani = 14 + secilen_yon_kaybi
    sistem_verimi = (100 - toplam_kayip_orani) / 100
    
    ihtiyac_olan_guc_kw = hedef_uretim / (gunluk_isinim * 365 * sistem_verimi)
    max_cati_guc_kw = (cati_alani * 0.85) * verim_katsayisi
    
    uyari_mesaji = ""
    if "Ekonomik" in sistem_hedefi:
        if max_cati_guc_kw > ihtiyac_olan_guc_kw:
            kurulu_guc_kw = ihtiyac_olan_guc_kw
            uyari_mesaji = "✅ **Ekonomik Mod:** Sadece faturanız kadar kurulum hesapladık."
        else:
            kurulu_guc_kw = max_cati_guc_kw
            uyari_mesaji = f"⚠️ **Kapasite Sınırı:** {('Çatı' if kurulum_yeri == 'Çatı Üzeri' else 'Arazi')} alanınız ihtiyacın tamamını karşılamaya yetmiyor."
    else:
        kurulu_guc_kw = max_cati_guc_kw
        tahmini_yillik_uretim = kurulu_guc_kw * gunluk_isinim * 365 * sistem_verimi
        if tahmini_yillik_uretim > yillik_tuketim_kwh:
            fazla_uretim = tahmini_yillik_uretim - yillik_tuketim_kwh
            satis_geliri = fazla_uretim * elektrik_birim_fiyat
            uyari_mesaji = f"🚀 **Kazanç Modu:** Fazla elektriği satarak yılda **{tr_fmt(satis_geliri)} TL** ek gelir elde edeceksiniz."
        else:
             uyari_mesaji = "ℹ️ Alanın tamamını kullandık."

    # 4. FİNANSAL HESAPLAR
    yillik_uretim_kwh = kurulu_guc_kw * gunluk_isinim * 365 * sistem_verimi
    aylik_ortalama_uretim = yillik_uretim_kwh / 12
    aylik_ekonomik_fayda_tl = aylik_ortalama_uretim * elektrik_birim_fiyat
    yatirim_maliyeti_tl = kurulu_guc_kw * maliyet_usd_kw * dolar_kuru
    tahmini_panel_sayisi = max(1, int(kurulu_guc_kw / (panel_gucu_watt / 1000)))
    
    co2_ton = (yillik_uretim_kwh * 0.5) / 1000
    agac_sayisi = int((yillik_uretim_kwh * 0.5) / 20)

    kredi_taksidi = 0
    if kredi_kullanimi:
        aylik_faiz = faiz_orani / 100
        kredi_taksidi = yatirim_maliyeti_tl * (aylik_faiz * (1 + aylik_faiz)**vade_sayisi) / ((1 + aylik_faiz)**vade_sayisi - 1)

    # 5. DİNAMİK ROI HESABI
    amortisman_yil = 0
    kasa_simulasyon = -yatirim_maliyeti_tl
    zam_carpani = 1 + (elektrik_zam_beklentisi / 100)
    nakit_akisi_listesi = []
    
    for i in range(1, 26):
        yillik_getiri_sim = (yillik_uretim_kwh * (0.995**i)) * (elektrik_birim_fiyat * (zam_carpani**i))
        gider_sim = 0
        if i == 12: gider_sim = yatirim_maliyeti_tl * 0.15
        kasa_simulasyon = kasa_simulasyon + yillik_getiri_sim - gider_sim
        nakit_akisi_listesi.append(kasa_simulasyon)
        
        if kasa_simulasyon > 0 and amortisman_yil == 0:
            onceki_bakiye = abs(kasa_simulasyon - (yillik_getiri_sim - gider_sim))
            net_gelir_bu_yil = yillik_getiri_sim - gider_sim
            yil_kesri = onceki_bakiye / net_gelir_bu_yil
            amortisman_yil = (i - 1) + yil_kesri
            
    if amortisman_yil == 0: amortisman_yil = 25

    # --- SONUÇLARI GÖSTERME ---
    st.divider()
    st.subheader(f"📍 {sehir} Analiz Raporu")
    
    st.info(f"ℹ️ **Mühendislik Bilgisi:** {sehir} için verimli güneş saati (PSH) **{gunluk_isinim} saat** alınmıştır. MGM verisi ({mgm_degeri} saat) tüm gün ışığını içerirken, biz sadece panelin tam güçte çalıştığı verimli saatleri kullanıyoruz.")
    
    if uyari_mesaji: st.markdown(uyari_mesaji)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tahmini Panel Sayısı", f"{tahmini_panel_sayisi} Adet", help=f"Toplam Güç: {kurulu_guc_kw:.2f} kWp")
    c2.metric("Sistem Maliyeti", f"{tr_fmt(yatirim_maliyeti_tl)} TL") 
    c3.metric("Aylık Ortalama Kazanç", f"{tr_fmt(aylik_ekonomik_fayda_tl)} TL", delta="Tasarruf")
    c4.metric("Amortisman (ROI)", f"{amortisman_yil:.1f} Yıl")

    st.markdown("---")
    st.subheader("🌍 Dünyaya Katkınız")
    ce1, ce2, ce3 = st.columns(3)
    ce1.metric("🌲 Ağaç Eşdeğeri", f"{agac_sayisi} Adet")
    ce2.metric("☁️ Engellenen CO2", f"{co2_ton:.1f} Ton")
    ce3.metric("🚗 Araba Sürüşü", f"{tr_fmt(int(co2_ton * 5000))} km")

    st.markdown("---")
    tab1, tab2 = st.tabs(["📉 Finansal Tablo (Nakit Akışı)", "📅 Aylık Üretim (Mevsimsellik)"])

    with tab1:
        st.subheader("20 Yıllık Birikimli Kazanç Tablosu")
        inverter_maliyeti = yatirim_maliyeti_tl * 0.15
        
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            df_chart = pd.DataFrame({
                "Yıl": list(range(1, 22)), 
                "Toplam Birikimli Kazanç (TL)": nakit_akisi_listesi[:21]
            })
            df_chart["Toplam Birikimli Kazanç (TL)"] = df_chart["Toplam Birikimli Kazanç (TL)"].astype(int)
            df_chart["Kasa Durumu"] = df_chart["Toplam Birikimli Kazanç (TL)"].apply(tr_fmt)
            
            chart_fin = alt.Chart(df_chart).mark_area(color="#FFD700", line={'color':'darkgoldenrod'}, opacity=0.6).encode(
                x=alt.X('Yıl:O', title='Yıl'),
                y=alt.Y('Toplam Birikimli Kazanç (TL):Q', title='Toplam Birikimli Kazanç (TL)'),
                tooltip=['Yıl', alt.Tooltip('Kasa Durumu', title='Kasa (TL)')]
            ).interactive()
            st.altair_chart(chart_fin, use_container_width=True)
            st.caption(f"ℹ️ **Not:** 12. yılda İnverter değişimi ({tr_fmt(inverter_maliyeti)} TL) düşülmüştür.")
        
        with col_f2:
            st.write(f"**⚡ Enflasyon Senaryosu:** Yıllık %{elektrik_zam_beklentisi}")
            if kredi_kullanimi:
                st.warning("🏦 **Kredi Durumu**")
                st.write(f"Taksit: **{tr_fmt(kredi_taksidi)} TL**")
                fark = aylik_ekonomik_fayda_tl - kredi_taksidi
                if fark > 0: st.success(f"Cebinize **{tr_fmt(fark)} TL** kalıyor!")
                else: st.error(f"Cebinizden **{tr_fmt(abs(fark))} TL** çıkıyor.")
            else:
                st.success("Nakit alımda sistem kendini daha hızlı amorti eder.")

    with tab2:
        st.subheader("📅 Aylık Üretim Tahmini")
        uretimler = []
        for oran in aylik_katsayilar: uretimler.append(aylik_ortalama_uretim * oran)
        
        df_aylik = pd.DataFrame({"Ay": aylar_listesi, "Üretim (kWh)": uretimler})
        df_aylik["Üretim (kWh)"] = df_aylik["Üretim (kWh)"].astype(int)
        
        chart = alt.Chart(df_aylik).mark_bar(color="#FF4B4B").encode(
            x=alt.X('Ay', sort=aylar_listesi), y='Üretim (kWh)', tooltip=['Ay', 'Üretim (kWh)']
        )
        st.altair_chart(chart, use_container_width=True)
        st.info("Not: Bu grafik Türkiye ortalaması mevsimsellik verilerine dayanır.")

    # --- İLETİŞİM FORMU (VERİTABANINA BAĞLI) ---
    st.markdown("---")
    st.subheader("📞 Ücretsiz Keşif ve Teklif Formu")
    with st.form("iletisim_formu"):
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            ad_soyad = st.text_input("Adınız Soyadınız")
            telefon = st.text_input("Telefon (5XX ...)")
        with c_i2:
            email = st.text_input("E-posta Adresiniz (Opsiyonel)")
            notlar = st.text_area("Notlarınız")
        
        submit_btn = st.form_submit_button("✅ GÖNDER", type="primary")
        
        if submit_btn:
            if ad_soyad and telefon:
                # Veritabanına Kaydetme İşlemi
                kayit_basarili = veritabanina_kaydet(ad_soyad, telefon, email, sehir, str(fatura), notlar)
                if kayit_basarili:
                    st.success(f"Teşekkürler {ad_soyad}! Bilgileriniz güvenle alındı. En kısa sürede {telefon} üzerinden dönüş yapılacaktır.")
                    st.balloons()
            else:
                st.error("Lütfen Ad Soyad ve Telefon alanlarını doldurunuz.")
