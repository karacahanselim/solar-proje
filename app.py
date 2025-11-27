import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime
import requests # API istekleri için

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="SolarVizyon - Profesyonel GES Analizi", 
    layout="wide", 
    page_icon="☀️"
)

# --- YARDIMCI FONKSİYONLAR ---
def tr_fmt(sayi):
    if sayi is None: return "0"
    return f"{int(sayi):,.0f}".replace(",", ".")

# --- PVGIS API FONKSİYONU (YENİ) ---
@st.cache_data(ttl=3600) # Verileri 1 saat önbellekte tut ki hızlansın
def get_pvgis_data(lat, lon, peak_power, loss, angle=35, aspect=0):
    """
    Avrupa Komisyonu PVGIS API'sinden yıllık üretim verisini çeker.
    lat: Enlem, lon: Boylam, peak_power: Kurulu Güç (kW), loss: Kayıp (%), angle: Eğim, aspect: Yön (Azimut)
    """
    try:
        url = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"
        params = {
            'lat': lat,
            'lon': lon,
            'peakpower': peak_power,
            'loss': loss,
            'angle': angle,   # Çatı eğimi (varsayılan 35)
            'aspect': aspect, # Cephe yönü (0:Güney, -90:Doğu, 90:Batı)
            'outputformat': 'json'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Yıllık toplam üretim (E_y) ve Aylık verileri al
            yearly_production = data['outputs']['totals']['fixed']['E_y']
            monthly_data = data['outputs']['monthly']['fixed']
            
            # Aylık dağılımı çek (Ocak'tan Aralık'a)
            monthly_production = [m['E_m'] for m in monthly_data]
            
            return yearly_production, monthly_production
        else:
            return None, None
    except Exception as e:
        st.error(f"PVGIS Bağlantı Hatası: {e}")
        return None, None

# --- VERİTABANI KAYIT FONKSİYONU ---
def veritabanina_kaydet(ad, firma, tel, email, sehir, sistem_tipi, tuketim_bilgisi, notlar):
    try:
        try:
            json_icerik = st.secrets["gcp_service_account"]["json_file"]
            creds_dict = json.loads(json_icerik)
        except:
            return False
        
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
    **Avrupa Komisyonu PVGIS uydularından** anlık alınan verilerle, bölgenize özel en hassas güneş enerjisi üretim analizini yapıyoruz.
    """)

st.markdown("---")

# --- GİRİŞ PARAMETRELERİ ---
st.subheader("📝 Teknik Veri Girişi")

col_form1, col_form2 = st.columns(2, gap="medium")

with col_form1:
    st.markdown("#### 🏠 Lokasyon ve Sistem Tipi")
    
    # ŞEHİR KOORDİNATLARI (PVGIS İÇİN GEREKLİ)
    sehirler_coords = {
        "İstanbul": (41.0082, 28.9784), "Ankara": (39.9334, 32.8597), "İzmir": (38.4192, 27.1287),
        "Antalya": (36.8969, 30.7133), "Kayseri": (38.7312, 35.4787), "Konya": (37.8667, 32.4833),
        "Gaziantep": (37.0662, 37.3833), "Van": (38.4891, 43.4089), "Adana": (37.0000, 35.3213),
        "Trabzon": (41.0027, 39.7168)
    }
    
    sehir = st.selectbox("📍 Şehir Seçiniz", list(sehirler_coords.keys()))
    
    sistem_tipi = st.radio("Sistem Tipi Nedir?", 
             ["On-Grid (Şebeke Bağlantılı)", "Off-Grid (Akü Depolamalı / Bağ Evi)"],
             help="On-Grid: Şehir şebekesi vardır, satış yapılabilir. Off-Grid: Şebeke yoktur, akü zorunludur.")

    if "Off-Grid" in sistem_tipi:
        aku_tipi = st.selectbox("🔋 Akü Teknolojisi Seçimi", 
                                ["Jel Akü (Ekonomik - Ömür ~4 Yıl)", "Lityum İyon (Premium - Ömür ~10 Yıl)"])
        st.caption("⚠️ **Mühendis Notu:** Jel aküler ucuzdur ama 4-5 yılda bir değişim gerektirir.")
    else:
        aku_tipi = "Yok" 

    st.markdown("#### 📊 Tüketim Verisi")
    hesap_yontemi = st.radio("Tüketimi Nasıl Gireceksiniz?", 
                             ["Aylık Fatura Tutarı (TL)", "Günlük Ortalama Tüketim (kWh)", "Aylık Toplam Tüketim (kWh)"])
    
    if "TL" in hesap_yontemi:
        girdi_deger = st.number_input("Aylık Ortalama Fatura (TL)", value=1000, step=50)
        elektrik_birim_fiyat = 2.60 
    elif "Günlük" in hesap_yontemi:
        girdi_deger = st.number_input("Günlük Ortalama Tüketim (kWh)", value=10.0, step=0.5)
        elektrik_birim_fiyat = 2.60
    else:
        girdi_deger = st.number_input("Aylık Toplam Tüketim (kWh)", value=300, step=50)
        elektrik_birim_fiyat = 2.60

with col_form2:
    st.markdown("#### ⚙️ Çatı ve Panel Detayları")
    
    alan_label = "🏠 Net Çatı Alanı (m²)" if "On-Grid" in sistem_tipi else "🌱 Kullanılabilir Arazi/Çatı Alanı (m²)"
    cati_alani = st.number_input(alan_label, value=80, help="Gölge düşmeyen, kullanılabilir net alan.")
    
    # PVGIS İÇİN YÖN SEÇİMİ (AZİMUT)
    # Güney=0, Doğu=-90, Batı=90 (PVGIS Standardı)
    yon_secimi_ui = st.selectbox("🧭 Alanın Cephesi", ["Güney (En İyi)", "Güney-Doğu", "Güney-Batı", "Doğu", "Batı", "Kuzey"])
    
    yon_to_azimuth = {
        "Güney (En İyi)": 0, "Güney-Doğu": -45, "Güney-Batı": 45,
        "Doğu": -90, "Batı": 90, "Kuzey": 180
    }
    azimuth_val = yon_to_azimuth[yon_secimi_ui]
    
    if "Off-Grid" in sistem_tipi:
        st.success("✅ **Off-Grid Avantajı:** Paneller arazide ise Güney (0°) varsayılacaktır.")
        azimuth_val = 0 # Arazideysen güneye çeviririz

    panel_tipi = st.radio("Panel Teknolojisi", ["Standart Panel (Poly)", "Premium Panel (Mono Perc)"], horizontal=True)
    
    st.markdown("#### 📈 Ekonomik Parametreler")
    elektrik_zam_beklentisi = st.slider("Yıllık Enerji Fiyat Artış Beklentisi (%)", 0, 100, 40)
    st.info("💡 **Referans Bilgi:** Ekim 2025 TÜİK TÜFE: **%32,87**")

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
if st.button("🚀 PVGIS İLE BİLİMSEL ANALİZİ BAŞLAT", type="primary", use_container_width=True):
    st.session_state.hesaplandi = True
else:
    if 'hesaplandi' not in st.session_state:
        st.session_state.hesaplandi = False

# --- HESAPLAMA MOTORU (PVGIS ENTEGRELİ) ---
if st.session_state.hesaplandi:
    
    # 1. TÜKETİMİ HESAPLA
    if "TL" in hesap_yontemi:
        aylik_tuketim_kwh = girdi_deger / elektrik_birim_fiyat
    elif "Günlük" in hesap_yontemi:
        aylik_tuketim_kwh = girdi_deger * 30
    else:
        aylik_tuketim_kwh = girdi_deger
    yillik_tuketim_kwh = aylik_tuketim_kwh * 12
    
    # 2. SİSTEM BOYUTLANDIRMA (TAHMİNİ)
    # Önce yaklaşık bir güç belirleyelim, sonra PVGIS'e soracağız
    verim_katsayisi = 0.21 if "Premium" in panel_tipi else 0.17
    panel_gucu_watt = 550 if "Premium" in panel_tipi else 400
    
    max_cati_guc_kw = cati_alani * verim_katsayisi
    
    # İhtiyaca göre güç belirleme (Basit yaklaşımla başlatıp PVGIS ile düzelteceğiz)
    # Türkiye ortalaması ile kabaca bir hedef güç bulalım
    hedef_guc_kw = (yillik_tuketim_kwh * 1.1) / (4.0 * 365 * 0.85) # Yaklaşık
    
    if "Off-Grid" in sistem_tipi:
        kurulu_guc_kw = min(hedef_guc_kw, max_cati_guc_kw)
        uyari_mesaji = f"⚠️ **Kapasite Sınırı:** {('Çatı' if kurulum_yeri == 'Çatı Üzeri' else 'Arazi')} alanınız kısıtlı olduğu için sistem gücü sınırlandırıldı." if max_cati_guc_kw < hedef_guc_kw else ""
    else:
        kurulu_guc_kw = min(hedef_guc_kw, max_cati_guc_kw)
        uyari_mesaji = "ℹ️ Alanın tamamını kullandık." if max_cati_guc_kw < hedef_guc_kw else "ℹ️ İhtiyacınız kadar kurulum hesaplandı."

    # Panel Sayısını Tam Sayıya Yuvarla
    panel_sayisi = max(1, int((kurulu_guc_kw * 1000) / panel_gucu_watt))
    gercek_kurulu_guc_kw = (panel_sayisi * panel_gucu_watt) / 1000
    
    # 3. PVGIS API'DEN GERÇEK ÜRETİMİ ÇEKME 📡
    lat, lon = sehirler_coords[sehir]
    sistem_kaybi = 14 # % (Kablo, inverter, sıcaklık kayıpları)
    
    with st.spinner(f'{sehir} için uydu verileri çekiliyor (PVGIS)...'):
        yillik_uretim_pvgis, aylik_uretim_pvgis = get_pvgis_data(lat, lon, gercek_kurulu_guc_kw, sistem_kaybi, angle=30, aspect=azimuth_val)
    
    if yillik_uretim_pvgis is None:
        st.error("PVGIS verisi alınamadı. Lütfen daha sonra tekrar deneyin.")
        st.stop()
        
    # 4. MALİYET ANALİZİ
    baz_maliyet_usd = 750 if "Premium" in panel_tipi else 600
    # Ölçek Ekonomisi
    if gercek_kurulu_guc_kw < 5: birim_maliyet_usd = baz_maliyet_usd * 1.3
    elif gercek_kurulu_guc_kw < 10: birim_maliyet_usd = baz_maliyet_usd * 1.1
    else: birim_maliyet_usd = baz_maliyet_usd
    
    donanim_maliyeti_usd = gercek_kurulu_guc_kw * birim_maliyet_usd
    aku_maliyeti_usd = 0
    
    if "Off-Grid" in sistem_tipi:
        gunluk_tuketim_kwh = aylik_tuketim_kwh / 30
        aku_kapasitesi_kwh = gunluk_tuketim_kwh * 1.5
        aku_birim_fiyat = 250 if "Jel" in aku_tipi else 600
        aku_maliyeti_usd = aku_kapasitesi_kwh * aku_birim_fiyat
        sistem_notu = f"🔋 **Off-Grid Sistem:** {aku_kapasitesi_kwh:.1f} kWh kapasiteli akü bankası eklendi."
    else:
        sistem_notu = "⚡ **On-Grid Sistem:** Şebeke bağlantılı, aküsüz sistem."

    toplam_yatirim_usd = donanim_maliyeti_usd + aku_maliyeti_usd
    yatirim_maliyeti_tl = toplam_yatirim_usd * dolar_kuru
    
    # 5. FİNANSAL GETİRİ
    # PVGIS'den gelen yıllık üretimi kullanıyoruz artık!
    aylik_ortalama_uretim_tl = (yillik_uretim_pvgis / 12) * elektrik_birim_fiyat

    # 6. DİNAMİK ROI
    amortisman_yil = 0
    kasa_bakiyesi = -yatirim_maliyeti_tl
    nakit_akisi_listesi = []
    zam_carpani = 1 + (elektrik_zam_beklentisi / 100)
    panel_degradasyon = 0.995
    
    inverter_degisim_maliyeti = gercek_kurulu_guc_kw * 150 * dolar_kuru
    aku_degisim_maliyeti = aku_maliyeti_usd * dolar_kuru
    aku_omru = 5 if "Off-Grid" in sistem_tipi and "Jel" in aku_tipi else 10
    
    for yil in range(1, 26):
        yillik_gelir = (yillik_uretim_pvgis * (panel_degradasyon**yil)) * (elektrik_birim_fiyat * (zam_carpani**yil))
        yillik_gider = 0
        if yil == 12: yillik_gider += inverter_degisim_maliyeti
        if "Off-Grid" in sistem_tipi and (yil % aku_omru == 0) and yil != 20:
            yillik_gider += aku_degisim_maliyeti
            
        kasa_bakiyesi = kasa_bakiyesi + yillik_gelir - yillik_gider
        nakit_akisi_listesi.append(kasa_bakiyesi)
        
        if kasa_bakiyesi > 0 and amortisman_yil == 0:
            onceki_bakiye = abs(kasa_bakiyesi - (yillik_gelir - yillik_gider))
            net_gelir = yillik_gelir - yillik_gider
            amortisman_yil = (yil - 1) + (onceki_bakiye / net_gelir)
            
    if amortisman_yil == 0: amortisman_yil = 25

    # --- ÇIKTI EKRANI ---
    st.divider()
    st.subheader(f"📍 {sehir} Analiz Raporu")
    st.success("✅ **Veriler Doğrulandı:** Hesaplamalar, Avrupa Komisyonu PVGIS uydusundan alınan gerçek ışınım verilerine dayanmaktadır.")
    st.info(sistem_notu)
    if uyari_mesaji: st.markdown(uyari_mesaji)
    
    if gercek_kurulu_guc_kw < 10:
        st.warning(f"💡 **Fiyat Notu:** Sisteminiz küçük ölçekli ({gercek_kurulu_guc_kw:.1f} kWp) olduğu için birim maliyet biraz yüksek hesaplanmıştır. (Ölçek Ekonomisi)")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Panel Sayısı", f"{panel_sayisi} Adet", help=f"Toplam Güç: {gercek_kurulu_guc_kw:.2f} kWp")
    c2.metric("Sistem Maliyeti", f"{tr_fmt(yatirim_maliyeti_tl)} TL")
    c3.metric("Aylık Kazanç (Ort.)", f"{tr_fmt(aylik_ortalama_uretim_tl)} TL", delta="Tasarruf")
    c4.metric("Amortisman (ROI)", f"{amortisman_yil:.1f} Yıl")

    # GRAFİKLER
    st.subheader("📉 Finansal Projeksiyon & Üretim")
    tab1, tab2 = st.tabs(["Nakit Akışı (20 Yıl)", "Aylık Üretim (PVGIS)"])
    
    with tab1:
        df_cash = pd.DataFrame({"Yıl": range(1, 26), "Kasa (TL)": nakit_akisi_listesi})
        df_cash["Kasa (TL)"] = df_cash["Kasa (TL)"].astype(int)
        df_cash["Tooltip"] = df_cash["Kasa (TL)"].apply(tr_fmt)
        
        chart = alt.Chart(df_cash).mark_area(color="#27ae60", opacity=0.6).encode(
            x='Yıl:O', y='Kasa (TL):Q', tooltip=['Yıl', alt.Tooltip('Tooltip', title='Bakiye (TL)')]
        ).interactive()
        st.altair_chart(chart, use_container_width=True)
        
        notlar = ["ℹ️ **Notlar:**", f"- 12. Yılda İnverter Değişimi ({tr_fmt(inverter_degisim_maliyeti)} TL) düşülmüştür."]
        if "Off-Grid" in sistem_tipi:
            notlar.append(f"- Her {aku_omru} yılda bir Akü Değişimi ({tr_fmt(aku_degisim_maliyeti)} TL) hesaba katılmıştır.")
        st.markdown("\n".join(notlar))

    with tab2:
        # PVGIS'den gelen gerçek aylık veriler
        aylar = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
        df_aylik = pd.DataFrame({"Ay": aylar, "Üretim (kWh)": aylik_uretim_pvgis})
        df_aylik["Üretim (kWh)"] = df_aylik["Üretim (kWh)"].astype(int)
        
        chart_bar = alt.Chart(df_aylik).mark_bar(color="#f39c12").encode(
            x=alt.X('Ay', sort=aylar), y='Üretim (kWh)', tooltip=['Ay', 'Üretim (kWh)']
        )
        st.altair_chart(chart_bar, use_container_width=True)
        st.info("Bu grafik, seçtiğiniz şehrin coğrafi konumuna ve güneş açısına göre PVGIS uydusundan alınan **gerçek üretim tahminidir.**")

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
                if veritabanina_kaydet(ad, firma, tel, email, sehir, sistem_tipi, f"{girdi_deger}", notlar):
                    st.success("Talebiniz başarıyla alındı!")
                    st.balloons()
                else:
                    st.error("Bağlantı hatası.")
            else:
                st.warning("Ad ve Telefon zorunludur.")import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime
import requests # API istekleri için

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="SolarVizyon - Profesyonel GES Analizi", 
    layout="wide", 
    page_icon="☀️"
)

# --- YARDIMCI FONKSİYONLAR ---
def tr_fmt(sayi):
    if sayi is None: return "0"
    return f"{int(sayi):,.0f}".replace(",", ".")

# --- PVGIS API FONKSİYONU (YENİ) ---
@st.cache_data(ttl=3600) # Verileri 1 saat önbellekte tut ki hızlansın
def get_pvgis_data(lat, lon, peak_power, loss, angle=35, aspect=0):
    """
    Avrupa Komisyonu PVGIS API'sinden yıllık üretim verisini çeker.
    lat: Enlem, lon: Boylam, peak_power: Kurulu Güç (kW), loss: Kayıp (%), angle: Eğim, aspect: Yön (Azimut)
    """
    try:
        url = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"
        params = {
            'lat': lat,
            'lon': lon,
            'peakpower': peak_power,
            'loss': loss,
            'angle': angle,   # Çatı eğimi (varsayılan 35)
            'aspect': aspect, # Cephe yönü (0:Güney, -90:Doğu, 90:Batı)
            'outputformat': 'json'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Yıllık toplam üretim (E_y) ve Aylık verileri al
            yearly_production = data['outputs']['totals']['fixed']['E_y']
            monthly_data = data['outputs']['monthly']['fixed']
            
            # Aylık dağılımı çek (Ocak'tan Aralık'a)
            monthly_production = [m['E_m'] for m in monthly_data]
            
            return yearly_production, monthly_production
        else:
            return None, None
    except Exception as e:
        st.error(f"PVGIS Bağlantı Hatası: {e}")
        return None, None

# --- VERİTABANI KAYIT FONKSİYONU ---
def veritabanina_kaydet(ad, firma, tel, email, sehir, sistem_tipi, tuketim_bilgisi, notlar):
    try:
        try:
            json_icerik = st.secrets["gcp_service_account"]["json_file"]
            creds_dict = json.loads(json_icerik)
        except:
            return False
        
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
    **Avrupa Komisyonu PVGIS uydularından** anlık alınan verilerle, bölgenize özel en hassas güneş enerjisi üretim analizini yapıyoruz.
    """)

st.markdown("---")

# --- GİRİŞ PARAMETRELERİ ---
st.subheader("📝 Teknik Veri Girişi")

col_form1, col_form2 = st.columns(2, gap="medium")

with col_form1:
    st.markdown("#### 🏠 Lokasyon ve Sistem Tipi")
    
    # ŞEHİR KOORDİNATLARI (PVGIS İÇİN GEREKLİ)
    sehirler_coords = {
        "İstanbul": (41.0082, 28.9784), "Ankara": (39.9334, 32.8597), "İzmir": (38.4192, 27.1287),
        "Antalya": (36.8969, 30.7133), "Kayseri": (38.7312, 35.4787), "Konya": (37.8667, 32.4833),
        "Gaziantep": (37.0662, 37.3833), "Van": (38.4891, 43.4089), "Adana": (37.0000, 35.3213),
        "Trabzon": (41.0027, 39.7168)
    }
    
    sehir = st.selectbox("📍 Şehir Seçiniz", list(sehirler_coords.keys()))
    
    sistem_tipi = st.radio("Sistem Tipi Nedir?", 
             ["On-Grid (Şebeke Bağlantılı)", "Off-Grid (Akü Depolamalı / Bağ Evi)"],
             help="On-Grid: Şehir şebekesi vardır, satış yapılabilir. Off-Grid: Şebeke yoktur, akü zorunludur.")

    if "Off-Grid" in sistem_tipi:
        aku_tipi = st.selectbox("🔋 Akü Teknolojisi Seçimi", 
                                ["Jel Akü (Ekonomik - Ömür ~4 Yıl)", "Lityum İyon (Premium - Ömür ~10 Yıl)"])
        st.caption("⚠️ **Mühendis Notu:** Jel aküler ucuzdur ama 4-5 yılda bir değişim gerektirir.")
    else:
        aku_tipi = "Yok" 

    st.markdown("#### 📊 Tüketim Verisi")
    hesap_yontemi = st.radio("Tüketimi Nasıl Gireceksiniz?", 
                             ["Aylık Fatura Tutarı (TL)", "Günlük Ortalama Tüketim (kWh)", "Aylık Toplam Tüketim (kWh)"])
    
    if "TL" in hesap_yontemi:
        girdi_deger = st.number_input("Aylık Ortalama Fatura (TL)", value=1000, step=50)
        elektrik_birim_fiyat = 2.60 
    elif "Günlük" in hesap_yontemi:
        girdi_deger = st.number_input("Günlük Ortalama Tüketim (kWh)", value=10.0, step=0.5)
        elektrik_birim_fiyat = 2.60
    else:
        girdi_deger = st.number_input("Aylık Toplam Tüketim (kWh)", value=300, step=50)
        elektrik_birim_fiyat = 2.60

with col_form2:
    st.markdown("#### ⚙️ Çatı ve Panel Detayları")
    
    alan_label = "🏠 Net Çatı Alanı (m²)" if "On-Grid" in sistem_tipi else "🌱 Kullanılabilir Arazi/Çatı Alanı (m²)"
    cati_alani = st.number_input(alan_label, value=80, help="Gölge düşmeyen, kullanılabilir net alan.")
    
    # PVGIS İÇİN YÖN SEÇİMİ (AZİMUT)
    # Güney=0, Doğu=-90, Batı=90 (PVGIS Standardı)
    yon_secimi_ui = st.selectbox("🧭 Alanın Cephesi", ["Güney (En İyi)", "Güney-Doğu", "Güney-Batı", "Doğu", "Batı", "Kuzey"])
    
    yon_to_azimuth = {
        "Güney (En İyi)": 0, "Güney-Doğu": -45, "Güney-Batı": 45,
        "Doğu": -90, "Batı": 90, "Kuzey": 180
    }
    azimuth_val = yon_to_azimuth[yon_secimi_ui]
    
    if "Off-Grid" in sistem_tipi:
        st.success("✅ **Off-Grid Avantajı:** Paneller arazide ise Güney (0°) varsayılacaktır.")
        azimuth_val = 0 # Arazideysen güneye çeviririz

    panel_tipi = st.radio("Panel Teknolojisi", ["Standart Panel (Poly)", "Premium Panel (Mono Perc)"], horizontal=True)
    
    st.markdown("#### 📈 Ekonomik Parametreler")
    elektrik_zam_beklentisi = st.slider("Yıllık Enerji Fiyat Artış Beklentisi (%)", 0, 100, 40)
    st.info("💡 **Referans Bilgi:** Ekim 2025 TÜİK TÜFE: **%32,87**")

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
if st.button("🚀 PVGIS İLE BİLİMSEL ANALİZİ BAŞLAT", type="primary", use_container_width=True):
    st.session_state.hesaplandi = True
else:
    if 'hesaplandi' not in st.session_state:
        st.session_state.hesaplandi = False

# --- HESAPLAMA MOTORU (PVGIS ENTEGRELİ) ---
if st.session_state.hesaplandi:
    
    # 1. TÜKETİMİ HESAPLA
    if "TL" in hesap_yontemi:
        aylik_tuketim_kwh = girdi_deger / elektrik_birim_fiyat
    elif "Günlük" in hesap_yontemi:
        aylik_tuketim_kwh = girdi_deger * 30
    else:
        aylik_tuketim_kwh = girdi_deger
    yillik_tuketim_kwh = aylik_tuketim_kwh * 12
    
    # 2. SİSTEM BOYUTLANDIRMA (TAHMİNİ)
    # Önce yaklaşık bir güç belirleyelim, sonra PVGIS'e soracağız
    verim_katsayisi = 0.21 if "Premium" in panel_tipi else 0.17
    panel_gucu_watt = 550 if "Premium" in panel_tipi else 400
    
    max_cati_guc_kw = cati_alani * verim_katsayisi
    
    # İhtiyaca göre güç belirleme (Basit yaklaşımla başlatıp PVGIS ile düzelteceğiz)
    # Türkiye ortalaması ile kabaca bir hedef güç bulalım
    hedef_guc_kw = (yillik_tuketim_kwh * 1.1) / (4.0 * 365 * 0.85) # Yaklaşık
    
    if "Off-Grid" in sistem_tipi:
        kurulu_guc_kw = min(hedef_guc_kw, max_cati_guc_kw)
        uyari_mesaji = f"⚠️ **Kapasite Sınırı:** {('Çatı' if kurulum_yeri == 'Çatı Üzeri' else 'Arazi')} alanınız kısıtlı olduğu için sistem gücü sınırlandırıldı." if max_cati_guc_kw < hedef_guc_kw else ""
    else:
        kurulu_guc_kw = min(hedef_guc_kw, max_cati_guc_kw)
        uyari_mesaji = "ℹ️ Alanın tamamını kullandık." if max_cati_guc_kw < hedef_guc_kw else "ℹ️ İhtiyacınız kadar kurulum hesaplandı."

    # Panel Sayısını Tam Sayıya Yuvarla
    panel_sayisi = max(1, int((kurulu_guc_kw * 1000) / panel_gucu_watt))
    gercek_kurulu_guc_kw = (panel_sayisi * panel_gucu_watt) / 1000
    
    # 3. PVGIS API'DEN GERÇEK ÜRETİMİ ÇEKME 📡
    lat, lon = sehirler_coords[sehir]
    sistem_kaybi = 14 # % (Kablo, inverter, sıcaklık kayıpları)
    
    with st.spinner(f'{sehir} için uydu verileri çekiliyor (PVGIS)...'):
        yillik_uretim_pvgis, aylik_uretim_pvgis = get_pvgis_data(lat, lon, gercek_kurulu_guc_kw, sistem_kaybi, angle=30, aspect=azimuth_val)
    
    if yillik_uretim_pvgis is None:
        st.error("PVGIS verisi alınamadı. Lütfen daha sonra tekrar deneyin.")
        st.stop()
        
    # 4. MALİYET ANALİZİ
    baz_maliyet_usd = 750 if "Premium" in panel_tipi else 600
    # Ölçek Ekonomisi
    if gercek_kurulu_guc_kw < 5: birim_maliyet_usd = baz_maliyet_usd * 1.3
    elif gercek_kurulu_guc_kw < 10: birim_maliyet_usd = baz_maliyet_usd * 1.1
    else: birim_maliyet_usd = baz_maliyet_usd
    
    donanim_maliyeti_usd = gercek_kurulu_guc_kw * birim_maliyet_usd
    aku_maliyeti_usd = 0
    
    if "Off-Grid" in sistem_tipi:
        gunluk_tuketim_kwh = aylik_tuketim_kwh / 30
        aku_kapasitesi_kwh = gunluk_tuketim_kwh * 1.5
        aku_birim_fiyat = 250 if "Jel" in aku_tipi else 600
        aku_maliyeti_usd = aku_kapasitesi_kwh * aku_birim_fiyat
        sistem_notu = f"🔋 **Off-Grid Sistem:** {aku_kapasitesi_kwh:.1f} kWh kapasiteli akü bankası eklendi."
    else:
        sistem_notu = "⚡ **On-Grid Sistem:** Şebeke bağlantılı, aküsüz sistem."

    toplam_yatirim_usd = donanim_maliyeti_usd + aku_maliyeti_usd
    yatirim_maliyeti_tl = toplam_yatirim_usd * dolar_kuru
    
    # 5. FİNANSAL GETİRİ
    # PVGIS'den gelen yıllık üretimi kullanıyoruz artık!
    aylik_ortalama_uretim_tl = (yillik_uretim_pvgis / 12) * elektrik_birim_fiyat

    # 6. DİNAMİK ROI
    amortisman_yil = 0
    kasa_bakiyesi = -yatirim_maliyeti_tl
    nakit_akisi_listesi = []
    zam_carpani = 1 + (elektrik_zam_beklentisi / 100)
    panel_degradasyon = 0.995
    
    inverter_degisim_maliyeti = gercek_kurulu_guc_kw * 150 * dolar_kuru
    aku_degisim_maliyeti = aku_maliyeti_usd * dolar_kuru
    aku_omru = 5 if "Off-Grid" in sistem_tipi and "Jel" in aku_tipi else 10
    
    for yil in range(1, 26):
        yillik_gelir = (yillik_uretim_pvgis * (panel_degradasyon**yil)) * (elektrik_birim_fiyat * (zam_carpani**yil))
        yillik_gider = 0
        if yil == 12: yillik_gider += inverter_degisim_maliyeti
        if "Off-Grid" in sistem_tipi and (yil % aku_omru == 0) and yil != 20:
            yillik_gider += aku_degisim_maliyeti
            
        kasa_bakiyesi = kasa_bakiyesi + yillik_gelir - yillik_gider
        nakit_akisi_listesi.append(kasa_bakiyesi)
        
        if kasa_bakiyesi > 0 and amortisman_yil == 0:
            onceki_bakiye = abs(kasa_bakiyesi - (yillik_gelir - yillik_gider))
            net_gelir = yillik_gelir - yillik_gider
            amortisman_yil = (yil - 1) + (onceki_bakiye / net_gelir)
            
    if amortisman_yil == 0: amortisman_yil = 25

    # --- ÇIKTI EKRANI ---
    st.divider()
    st.subheader(f"📍 {sehir} Analiz Raporu")
    st.success("✅ **Veriler Doğrulandı:** Hesaplamalar, Avrupa Komisyonu PVGIS uydusundan alınan gerçek ışınım verilerine dayanmaktadır.")
    st.info(sistem_notu)
    if uyari_mesaji: st.markdown(uyari_mesaji)
    
    if gercek_kurulu_guc_kw < 10:
        st.warning(f"💡 **Fiyat Notu:** Sisteminiz küçük ölçekli ({gercek_kurulu_guc_kw:.1f} kWp) olduğu için birim maliyet biraz yüksek hesaplanmıştır. (Ölçek Ekonomisi)")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Panel Sayısı", f"{panel_sayisi} Adet", help=f"Toplam Güç: {gercek_kurulu_guc_kw:.2f} kWp")
    c2.metric("Sistem Maliyeti", f"{tr_fmt(yatirim_maliyeti_tl)} TL")
    c3.metric("Aylık Kazanç (Ort.)", f"{tr_fmt(aylik_ortalama_uretim_tl)} TL", delta="Tasarruf")
    c4.metric("Amortisman (ROI)", f"{amortisman_yil:.1f} Yıl")

    # GRAFİKLER
    st.subheader("📉 Finansal Projeksiyon & Üretim")
    tab1, tab2 = st.tabs(["Nakit Akışı (20 Yıl)", "Aylık Üretim (PVGIS)"])
    
    with tab1:
        df_cash = pd.DataFrame({"Yıl": range(1, 26), "Kasa (TL)": nakit_akisi_listesi})
        df_cash["Kasa (TL)"] = df_cash["Kasa (TL)"].astype(int)
        df_cash["Tooltip"] = df_cash["Kasa (TL)"].apply(tr_fmt)
        
        chart = alt.Chart(df_cash).mark_area(color="#27ae60", opacity=0.6).encode(
            x='Yıl:O', y='Kasa (TL):Q', tooltip=['Yıl', alt.Tooltip('Tooltip', title='Bakiye (TL)')]
        ).interactive()
        st.altair_chart(chart, use_container_width=True)
        
        notlar = ["ℹ️ **Notlar:**", f"- 12. Yılda İnverter Değişimi ({tr_fmt(inverter_degisim_maliyeti)} TL) düşülmüştür."]
        if "Off-Grid" in sistem_tipi:
            notlar.append(f"- Her {aku_omru} yılda bir Akü Değişimi ({tr_fmt(aku_degisim_maliyeti)} TL) hesaba katılmıştır.")
        st.markdown("\n".join(notlar))

    with tab2:
        # PVGIS'den gelen gerçek aylık veriler
        aylar = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
        df_aylik = pd.DataFrame({"Ay": aylar, "Üretim (kWh)": aylik_uretim_pvgis})
        df_aylik["Üretim (kWh)"] = df_aylik["Üretim (kWh)"].astype(int)
        
        chart_bar = alt.Chart(df_aylik).mark_bar(color="#f39c12").encode(
            x=alt.X('Ay', sort=aylar), y='Üretim (kWh)', tooltip=['Ay', 'Üretim (kWh)']
        )
        st.altair_chart(chart_bar, use_container_width=True)
        st.info("Bu grafik, seçtiğiniz şehrin coğrafi konumuna ve güneş açısına göre PVGIS uydusundan alınan **gerçek üretim tahminidir.**")

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
                if veritabanina_kaydet(ad, firma, tel, email, sehir, sistem_tipi, f"{girdi_deger}", notlar):
                    st.success("Talebiniz başarıyla alındı!")
                    st.balloons()
                else:
                    st.error("Bağlantı hatası.")
            else:
                st.warning("Ad ve Telefon zorunludur.")
