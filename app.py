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

# --- YARDIMCI FONKSİYON ---
def tr_fmt(sayi):
    if sayi is None: return "0"
    return f"{int(sayi):,.0f}".replace(",", ".")

# --- VERİTABANI KAYIT (GÜNCELLENDİ) ---
def veritabanina_kaydet(ad, firma, tel, email, sehir, sistem_tipi, tuketim_bilgisi, notlar):
    try:
        try:
            json_icerik = st.secrets["gcp_service_account"]["json_file"]
            creds_dict = json.loads(json_icerik)
        except:
            return False # Sessizce geç, hata verme (Local çalışırken)
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("SolarMusteriler").sheet1
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
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
    
    # 1. SİSTEM TİPİ SEÇİMİ (YENİ)
    sistem_tipi = st.radio("Sistem Tipi Nedir?", 
             ["On-Grid (Şebeke Bağlantılı)", "Off-Grid (Akü Depolamalı / Bağ Evi)"],
             help="On-Grid: Şehir şebekesi vardır, satış yapılabilir. Off-Grid: Şebeke yoktur, akü zorunludur.")

    if "Off-Grid" in sistem_tipi:
        aku_tipi = st.selectbox("🔋 Akü Teknolojisi Seçimi", 
                                ["Jel Akü (Ekonomik - Ömür ~4 Yıl)", "Lityum İyon (Premium - Ömür ~10 Yıl)"])
        st.caption("⚠️ **Mühendis Notu:** Jel aküler ucuzdur ama sık değişim gerektirir. Lityum pahalıdır ama uzun ömürlüdür.")
    else:
        aku_tipi = "Yok" # On-Grid'de akü yok varsayıyoruz

    st.markdown("#### 📊 Tüketim Verisi")
    # 2. GİRİŞ YÖNTEMİ (YENİ)
    hesap_yontemi = st.radio("Nasıl Hesaplayalım?", ["Aylık Fatura Tutarı (TL)", "Aylık Tüketim Miktarı (kWh)"], horizontal=True)
    
    if "TL" in hesap_yontemi:
        girdi_deger = st.number_input("Aylık Ortalama Fatura (TL)", value=1000, step=50)
        elektrik_birim_fiyat = 2.60 # Varsayılan
    else:
        girdi_deger = st.number_input("Aylık Tüketim (kWh)", value=400, step=50, help="Faturanızın üzerindeki 'Tüketim Endeksi' kısmında yazar. En doğru hesap budur.")
        elektrik_birim_fiyat = 2.60 # Tasarruf hesabı için yine lazım

with col_form2:
    st.markdown("#### ⚙️ Çatı ve Panel Detayları")
    alan_etiketi = "🏠 Panel Kurulabilir Net Alan (m²)"
    alan_ipucu = "Gölge düşmeyen, bacasız, saf net alan."
    cati_alani = st.number_input(alan_etiketi, value=80, help=alan_ipucu)
    
    yon_secimi = st.selectbox("🧭 Alanın Cephesi (Yönü)", ["Güney (En İyi)", "Güney-Doğu (İyi)", "Güney-Batı (İyi)", "Doğu (Orta)", "Batı (Orta)", "Kuzey (Tavsiye Edilmez)"])
    
    panel_tipi = st.radio("Panel Teknolojisi", ["Standart Panel (Poly)", "Premium Panel (Mono Perc)"], horizontal=True)
    
    st.markdown("#### 📈 Ekonomik Parametreler")
    elektrik_zam_beklentisi = st.slider("Yıllık Enerji Fiyat Artış Beklentisi (%)", 0, 100, 40)
    st.caption("TÜİK verileri veya kendi piyasa öngörünüzü baz alabilirsiniz.")

# --- GELİŞMİŞ AYARLAR ---
with st.expander("🛠️ Gelişmiş Ayarlar (Döviz & Birim Fiyat)"):
    c1, c2 = st.columns(2)
    dolar_kuru = c1.number_input("Dolar Kuru ($)", value=34.50, step=0.1)
    if "TL" not in hesap_yontemi:
        elektrik_birim_fiyat = c2.number_input("Elektrik Birim Fiyatı (TL/kWh)", value=2.60, step=0.1)

st.markdown("---")

# --- HESAPLA BUTONU ---
if st.button("🚀 ANALİZİ BAŞLAT", type="primary", use_container_width=True):
    st.session_state.hesaplandi = True
else:
    if 'hesaplandi' not in st.session_state:
        st.session_state.hesaplandi = False

# --- MÜHENDİSLİK HESAPLAMALARI ---
if st.session_state.hesaplandi:
    
    # 1. TÜKETİMİ KWH'E ÇEVİRME (HOCANIN İSTEDİĞİ KISIM)
    if "TL" in hesap_yontemi:
        aylik_tuketim_kwh = girdi_deger / elektrik_birim_fiyat
    else:
        aylik_tuketim_kwh = girdi_deger # Zaten kWh girildi
    
    yillik_tuketim_kwh = aylik_tuketim_kwh * 12
    
    # 2. ÜRETİM PARAMETRELERİ
    gunluk_isinim_ort = 4.2 # Türkiye ortalaması (Şimdilik basit tutalım, sonra şehre bağlarız)
    # Şehir bazlı hassas veri için dictionary kullanılabilir ama şu an mantığı oturtuyoruz.
    
    yon_kayip_tablosu = { "Güney (En İyi)": 0, "Güney-Doğu (İyi)": 5, "Güney-Batı (İyi)": 5, "Doğu (Orta)": 15, "Batı (Orta)": 15, "Kuzey (Tavsiye Edilmez)": 35 }
    secilen_yon_kaybi = yon_kayip_tablosu[yon_secimi]
    
    verim_katsayisi = 0.21 if "Premium" in panel_tipi else 0.17
    
    # 3. SİSTEM BOYUTLANDIRMA
    # Off-Grid ise sadece tüketime odaklan, On-Grid ise çatıyı doldurabilirsin.
    hedef_guc = (yillik_tuketim_kwh * 1.2) / (gunluk_isinim_ort * 365 * 0.85) # %20 güvenlik marjı
    max_cati_guc = cati_alani * verim_katsayisi
    
    kurulu_guc_kw = min(hedef_guc, max_cati_guc)
    
    # 4. MALİYET ANALİZİ (ON-GRID vs OFF-GRID)
    # On-Grid Maliyet: ~700 $/kW
    # Off-Grid Maliyet: ~1500 $/kW (Akü ve Şarj Kontrol Eklenir)
    
    if "Off-Grid" in sistem_tipi:
        # Off-Grid Maliyet Hesabı
        # Akü Kapasitesi (kWh) = Günlük Tüketim * Otonomi Günü (1.5 gün)
        gunluk_tuketim = aylik_tuketim_kwh / 30
        aku_kapasitesi_kwh = gunluk_tuketim * 1.5 
        
        # Akü Fiyatları (Örnek)
        aku_birim_fiyat = 250 if "Jel" in aku_tipi else 600 # $/kWh
        aku_maliyeti_usd = aku_kapasitesi_kwh * aku_birim_fiyat
        
        panel_inverter_maliyet_usd = kurulu_guc_kw * 700
        toplam_yatirim_usd = panel_inverter_maliyet_usd + aku_maliyeti_usd
        
        sistem_notu = f"🔋 **Off-Grid Sistem:** Şebekeden bağımsız yaşamak için **{aku_kapasitesi_kwh:.1f} kWh** kapasiteli akü bankası eklendi."
    else:
        # On-Grid Maliyet
        toplam_yatirim_usd = kurulu_guc_kw * 700 # Standart maliyet
        sistem_notu = "⚡ **On-Grid Sistem:** Şebeke ile entegre, aküsüz sistem."

    yatirim_maliyeti_tl = toplam_yatirim_usd * dolar_kuru

    # 5. FİNANSAL GETİRİ (TASARRUF)
    yillik_uretim_kwh = kurulu_guc_kw * gunluk_isinim_ort * 365 * ((100-secilen_yon_kaybi)/100) * 0.85
    aylik_ortalama_uretim = yillik_uretim_kwh / 12
    aylik_tasarruf_tl = aylik_ortalama_uretim * elektrik_birim_fiyat

    # --- SONUÇ EKRANI ---
    st.divider()
    st.subheader("🔍 Mühendislik Analiz Sonuçları")
    st.info(sistem_notu)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sistem Gücü", f"{kurulu_guc_kw:.2f} kWp")
    c2.metric("Tahmini Maliyet", f"{tr_fmt(yatirim_maliyeti_tl)} TL")
    c3.metric("Aylık Tasarruf", f"{tr_fmt(aylik_tasarruf_tl)} TL")
    
    # ROI Hesabı (Basit)
    if aylik_tasarruf_tl > 0:
        roi_yil = yatirim_maliyeti_tl / (aylik_tasarruf_tl * 12)
        c4.metric("Amortisman (ROI)", f"{roi_yil:.1f} Yıl")
    else:
        c4.metric("Amortisman", "--")

    # --- NAKİT AKIŞI GRAFİĞİ (AKÜ DEĞİŞİMİ DAHİL) ---
    st.subheader("📉 20 Yıllık Nakit Akışı ve Bakım Giderleri")
    
    nakit_akisi = []
    kasa = -yatirim_maliyeti_tl
    zam_carpani = 1 + (elektrik_zam_beklentisi / 100)
    
    aku_degisim_maliyeti = 0
    inverter_degisim_maliyeti = kurulu_guc_kw * 150 * dolar_kuru # 150$/kW
    
    if "Off-Grid" in sistem_tipi:
        aku_degisim_maliyeti = aku_maliyeti_usd * dolar_kuru
        aku_omru = 5 if "Jel" in aku_tipi else 10
    else:
        aku_omru = 100 # Asla değişmez (çünkü yok)

    for i in range(1, 21):
        # Gelir
        yillik_getiri = (yillik_uretim_kwh * 0.99) * (elektrik_birim_fiyat * (zam_carpani**i)) # %1 degradasyon
        
        # Giderler
        gider = 0
        # İnverter Değişimi (12. Yıl)
        if i == 12: 
            gider += inverter_degisim_maliyeti
        
        # Akü Değişimi (Off-Grid ise)
        if "Off-Grid" in sistem_tipi and (i % aku_omru == 0) and i != 20:
            gider += aku_degisim_maliyeti
        
        kasa = kasa + yillik_getiri - gider
        nakit_akisi.append(kasa)

    df_chart = pd.DataFrame({"Yıl": list(range(1, 21)), "Kasa (TL)": nakit_akisi})
    chart = alt.Chart(df_chart).mark_area(color="#2ecc71", line={'color':'darkgreen'}, opacity=0.5).encode(
        x='Yıl:O', y='Kasa (TL):Q', tooltip=['Yıl', 'Kasa (TL)']
    )
    st.altair_chart(chart, use_container_width=True)
    
    if "Off-Grid" in sistem_tipi:
        st.warning(f"⚠️ **Bakım Uyarısı:** Seçtiğiniz **{aku_tipi}** teknolojisi nedeniyle, grafikte her **{aku_omru} yılda bir** akü yenileme maliyeti (Ani düşüşler) hesaba katılmıştır.")
    else:
        st.caption("ℹ️ **Not:** 12. Yılda inverter değişimi maliyeti düşülmüştür.")

    # --- İLETİŞİM FORMU ---
    st.markdown("---")
    st.subheader("📞 Detaylı Teklif Alın")
    with st.form("iletisim"):
        c1, c2 = st.columns(2)
        ad = c1.text_input("Ad Soyad")
        tel = c2.text_input("Telefon")
        notlar = st.text_area("Notlar")
        if st.form_submit_button("Gönder"):
            if veritabanina_kaydet(ad, "Bireysel", tel, "", sehir, sistem_tipi, f"{girdi_deger}", notlar):
                st.success("Talebiniz alındı!")
            else:
                st.error("Hata oluştu.")
