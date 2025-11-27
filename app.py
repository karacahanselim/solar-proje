import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime
import requests 

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

# --- PVGIS API FONKSİYONU ---
@st.cache_data(ttl=3600) 
def get_pvgis_data(lat, lon, peak_power, loss, angle=35, aspect=0):
    try:
        url = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"
        params = {
            'lat': lat,
            'lon': lon,
            'peakpower': peak_power,
            'loss': loss,
            'angle': angle,   
            'aspect': aspect, 
            'outputformat': 'json'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            yearly_production = data['outputs']['totals']['fixed']['E_y']
            monthly_data = data['outputs']['monthly']['fixed']
            monthly_production = [m['E_m'] for m in monthly_data]
            return yearly_production, monthly_production
        else:
            return None, None
    except Exception as e:
        st.error(f"PVGIS Hatası: {e}")
        return None, None

# --- VERİTABANI KAYIT FONKSİYONU ---
def veritabanina_kaydet(ad, firma, tel, email, sehir, ilce, sistem_tipi, tuketim_bilgisi, notlar):
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
        konum_tam = f"{sehir} / {ilce}"
        sheet.append_row([tarih, ad, firma, tel, email, konum_tam, sistem_tipi, tuketim_bilgisi, notlar])
        return True
    except:
        return False

# --- BAŞLIK ---
c_header1, c_header2 = st.columns([1, 3])
with c_header1:
    st.image("https://images.unsplash.com/photo-1509391366360-2e959784a276?q=80&w=3264&auto=format&fit=crop", use_container_width=True)
with c_header2:
    st.title("☀️ SolarVizyon | Mühendislik Tabanlı GES Analizi")
    st.markdown("### Bilimsel Veri, Gerçekçi Sonuçlar 📐")
    st.markdown("**Avrupa Komisyonu PVGIS uydularından** alınan verilerle, **anahtar teslim** (Her şey dahil) maliyet ve getiri analizi.")

st.markdown("---")

# --- GİRİŞ PARAMETRELERİ ---
st.subheader("📝 Teknik Veri Girişi")
col_form1, col_form2 = st.columns(2, gap="medium")

with col_form1:
    st.markdown("#### 🏠 Lokasyon ve Sistem Tipi")
    
    # ŞEHİR VE İLÇE VERİTABANI
    sehir_ilce_coords = {
        "Kayseri": { "Merkez": (38.7312, 35.4787), "Talas": (38.6917, 35.5550), "Develi": (38.3922, 35.4908), "Hacılar": (38.6417, 35.4500), "İncesu": (38.6278, 35.1778), "Bünyan": (38.8444, 35.8611), "Yahyalı": (38.1000, 35.3667) },
        "İstanbul": { "Avrupa Yakası": (41.0082, 28.9784), "Anadolu Yakası": (40.9833, 29.1167), "Silivri": (41.0736, 28.2472), "Şile": (41.1744, 29.6125), "Çatalca": (41.1436, 28.4600) },
        "Ankara": { "Merkez": (39.9334, 32.8597), "Gölbaşı": (39.7889, 32.8028), "Polatlı": (39.5756, 32.1461), "Beypazarı": (40.1686, 31.9203), "Sincan": (39.9600, 32.5800) },
        "İzmir": { "Merkez": (38.4192, 27.1287), "Çeşme": (38.3233, 26.3042), "Urla": (38.3228, 26.7625), "Bergama": (39.1217, 27.1806), "Ödemiş": (38.2289, 27.9769) },
        "Antalya": { "Merkez": (36.8969, 30.7133), "Alanya": (36.5444, 31.9956), "Manavgat": (36.7867, 31.4422), "Kaş": (36.2000, 29.6333), "Kemer": (36.6019, 30.5606) },
        "Konya": { "Merkez": (37.8667, 32.4833), "Ereğli": (37.5117, 34.0536), "Akşehir": (38.3564, 31.4164), "Beyşehir": (37.6778, 31.7250) },
        "Gaziantep": { "Merkez": (37.0662, 37.3833), "Nizip": (37.0100, 37.7950), "İslahiye": (37.0261, 36.6306) },
        "Van": { "Merkez": (38.4891, 43.4089), "Erciş": (39.0283, 43.3581), "Edremit": (38.4250, 43.2583) },
        "Adana": { "Merkez": (37.0000, 35.3213), "Ceyhan": (37.0289, 35.8158), "Kozan": (37.4556, 35.8156) },
        "Trabzon": { "Merkez": (41.0027, 39.7168), "Akçaabat": (41.0208, 39.5703), "Of": (40.9469, 40.2706) }
    }
    
    sehir = st.selectbox("📍 İl Seçiniz", list(sehir_ilce_coords.keys()))
    ilce = st.selectbox("📍 İlçe Seçiniz", list(sehir_ilce_coords[sehir].keys()))
    
    sistem_tipi = st.radio("Sistem Tipi", ["On-Grid (Şebeke Bağlantılı)", "Off-Grid (Akü Depolamalı)"])

    if "Off-Grid" in sistem_tipi:
        aku_tipi = st.selectbox("🔋 Akü Tipi", ["Jel Akü (Ekonomik)", "Lityum İyon (Premium)"])
        st.caption("⚠️ Off-Grid sistemlerde akü maliyeti toplam fiyatı artırır.")
    else:
        aku_tipi = "Yok" 

    st.markdown("#### 📊 Tüketim Verisi")
    hesap_yontemi = st.radio("Tüketim Girişi", ["Aylık Fatura (TL)", "Günlük Tüketim (kWh)", "Aylık Tüketim (kWh)"])
    
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
    st.markdown("#### ⚙️ Çatı ve Panel")
    alan_label = "🏠 Net Çatı Alanı (m²)" if "On-Grid" in sistem_tipi else "🌱 Kullanılabilir Alan (m²)"
    cati_alani = st.number_input(alan_label, value=80)
    
    yon_secimi_ui = st.selectbox("🧭 Cephe Yönü", ["Güney (En İyi)", "Güney-Doğu", "Güney-Batı", "Doğu", "Batı", "Kuzey"])
    yon_to_azimuth = { "Güney (En İyi)": 0, "Güney-Doğu": -45, "Güney-Batı": 45, "Doğu": -90, "Batı": 90, "Kuzey": 180 }
    azimuth_val = 0 if "Off-Grid" in sistem_tipi else yon_to_azimuth[yon_secimi_ui]
    if "Off-Grid" in sistem_tipi: st.success("✅ Arazi kurulumunda paneller Tam Güney'e çevrilir.")

    panel_tipi = st.radio("Panel Kalitesi", ["Standart Panel (Poly)", "Premium Panel (Mono Perc)"], horizontal=True)
    
    st.markdown("#### 📈 Piyasa")
    elektrik_zam_beklentisi = st.slider("Yıllık Enerji Zammı Beklentisi (%)", 0, 100, 35)
    st.caption(f"Referans: Ekim 2025 Yıllık TÜFE %32,87")

with st.expander("🛠️ Gelişmiş Ayarlar (Döviz & Finansman)"):
    c1, c2 = st.columns(2)
    dolar_kuru = c1.number_input("Dolar Kuru ($)", value=34.50, step=0.1)
    if "TL" not in hesap_yontemi: elektrik_birim_fiyat = c2.number_input("Birim Fiyat (TL/kWh)", value=2.60, step=0.1)
    
    kredi_kullanimi = st.checkbox("Kredi Kullanılacak mı?", value=False)
    if kredi_kullanimi:
        faiz_orani = st.number_input("Aylık Faiz (%)", value=3.5, step=0.1)
        vade_sayisi = st.slider("Vade (Ay)", 12, 48, 24)

st.markdown("---")

if st.button("🚀 ANALİZİ BAŞLAT", type="primary", use_container_width=True):
    st.session_state.hesaplandi = True
else:
    if 'hesaplandi' not in st.session_state: st.session_state.hesaplandi = False

# --- HESAPLAMA ---
if st.session_state.hesaplandi:
    
    # 1. Tüketim
    if "TL" in hesap_yontemi: aylik_tuketim_kwh = girdi_deger / elektrik_birim_fiyat
    elif "Günlük" in hesap_yontemi: aylik_tuketim_kwh = girdi_deger * 30
    else: aylik_tuketim_kwh = girdi_deger
    yillik_tuketim_kwh = aylik_tuketim_kwh * 12
    
    # 2. Sistem Tasarımı
    verim_katsayisi = 0.21 if "Premium" in panel_tipi else 0.17
    panel_gucu_watt = 550 if "Premium" in panel_tipi else 400
    max_cati_guc_kw = cati_alani * verim_katsayisi
    
    # Hedef Güç (İhtiyaç)
    # Off-Grid ise kışın en kötü gününe göre hesaplanır, On-Grid ise ortalamaya göre
    faktor = 4.0 # Ortalama PSH
    hedef_guc_kw = (yillik_tuketim_kwh * 1.1) / (faktor * 365 * 0.85)
    
    kurulu_guc_kw = min(hedef_guc_kw, max_cati_guc_kw)
    
    # Panel Sayısı Revizyonu
    panel_sayisi = max(1, int((kurulu_guc_kw * 1000) / panel_gucu_watt))
    gercek_kurulu_guc_kw = (panel_sayisi * panel_gucu_watt) / 1000
    
    # 3. PVGIS Verisi
    lat, lon = sehir_ilce_coords[sehir][ilce]
    with st.spinner(f'{ilce} için uydu verileri çekiliyor...'):
        yillik_uretim, aylik_uretim = get_pvgis_data(lat, lon, gercek_kurulu_guc_kw, 14, angle=30, aspect=azimuth_val)
    
    if yillik_uretim is None:
        st.error("Veri alınamadı, tekrar deneyin.")
        st.stop()

    # 4. Maliyet Analizi (DETAYLI)
    # Birim Fiyatlar (Anahtar Teslim)
    base_panel_cost = 700 if "Premium" in panel_tipi else 600
    
    # Ölçek Çarpanı
    scale_factor = 1.0
    if gercek_kurulu_guc_kw < 3: scale_factor = 1.4 # Çok küçük sistem pahalı
    elif gercek_kurulu_guc_kw < 5: scale_factor = 1.3
    elif gercek_kurulu_guc_kw < 10: scale_factor = 1.1
    
    donanim_maliyeti = gercek_kurulu_guc_kw * base_panel_cost * scale_factor
    aku_maliyeti = 0
    
    if "Off-Grid" in sistem_tipi:
        # Akü Maliyeti
        gunluk_kwh = aylik_tuketim_kwh / 30
        aku_kapasite = gunluk_kwh * 1.5 # 1.5 gün otonomi
        aku_birim = 250 if "Jel" in aku_tipi else 600
        aku_maliyeti = aku_kapasite * aku_birim
    
    toplam_maliyet_usd = donanim_maliyeti + aku_maliyeti
    toplam_maliyet_tl = toplam_maliyet_usd * dolar_kuru
    
    # --- MALİYET KIRILIMI PASTASI (YENİ) ---
    # Bu oranlar yaklaşık piyasa ortalamasıdır
    maliyet_data = pd.DataFrame({
        'Kalem': ['Panel & İnverter', 'Konstrüksiyon & Kablo', 'İşçilik & Mühendislik', 'Resmi İşlemler & Nakliye'],
        'Deger': [donanim_maliyeti*0.50, donanim_maliyeti*0.20, donanim_maliyeti*0.20, donanim_maliyeti*0.10]
    })
    if "Off-Grid" in sistem_tipi:
        # Off-Grid ise Aküyü ekle
        new_row = pd.DataFrame({'Kalem': ['Akü Grubu'], 'Deger': [aku_maliyeti]})
        maliyet_data = pd.concat([maliyet_data, new_row], ignore_index=True)

    # 5. Finansal
    aylik_kazanc = (yillik_uretim / 12) * elektrik_birim_fiyat
    
    # ROI
    amortisman = 0
    kasa = -toplam_maliyet_tl
    nakit_akisi = []
    zam_carpani = 1 + (elektrik_zam_beklentisi/100)
    
    inv_degisim = gercek_kurulu_guc_kw * 150 * dolar_kuru
    aku_degisim = aku_maliyeti * dolar_kuru
    aku_omru = 5 if "Off-Grid" in sistem_tipi and "Jel" in aku_tipi else 10
    
    for i in range(1, 26):
        gelir = (yillik_uretim * (0.995**i)) * (elektrik_birim_fiyat * (zam_carpani**i))
        gider = 0
        if i == 12: gider += inv_degisim
        if "Off-Grid" in sistem_tipi and (i % aku_omru == 0) and i != 20: gider += aku_degisim
        
        kasa = kasa + gelir - gider
        nakit_akisi.append(kasa)
        
        if kasa > 0 and amortisman == 0:
            onceki = abs(kasa - (gelir - gider))
            amortisman = (i - 1) + (onceki / (gelir - gider))
            
    if amortisman == 0: amortisman = 25

    # --- SONUÇ EKRANI ---
    st.divider()
    st.subheader(f"📍 {sehir} / {ilce} Sonuç Raporu")
    st.success("✅ Hesaplamalar **Anahtar Teslim (Turnkey)** kurulum maliyetleri üzerinden yapılmıştır.")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sistem Gücü", f"{gercek_kurulu_guc_kw:.2f} kWp", f"{panel_sayisi} Panel")
    c2.metric("Anahtar Teslim Fiyat", f"{tr_fmt(toplam_maliyet_tl)} TL")
    c3.metric("Aylık Tasarruf", f"{tr_fmt(aylik_kazanc)} TL")
    c4.metric("Amortisman", f"{amortisman:.1f} Yıl")

    st.markdown("---")
    
    # GRAFİK ALANI (3 SEKME)
    t1, t2, t3 = st.tabs(["📉 Nakit Akışı", "💰 Maliyet Nereye Gidiyor?", "📅 Üretim"])
    
    with t1:
        df_cash = pd.DataFrame({"Yıl": range(1, 26), "Kasa": nakit_akisi})
        c = alt.Chart(df_cash).mark_area(color="#27ae60", opacity=0.6).encode(x='Yıl', y='Kasa')
        st.altair_chart(c, use_container_width=True)
        st.caption("12. Yılda inverter, Off-Grid ise belirli aralıklarla akü değişimi dahildir.")
    
    with t2:
        # MALİYET PASTASI (YENİ)
        st.markdown("##### Paranız Nereye Harcanıyor?")
        base = alt.Chart(maliyet_data).encode(theta=alt.Theta("Deger", stack=True))
        pie = base.mark_arc(outerRadius=120).encode(
            color=alt.Color("Kalem"),
            order=alt.Order("Deger", sort="descending"),
            tooltip=["Kalem", alt.Tooltip("Deger", format=",.0f")]
        )
        text = base.mark_text(radius=140).encode(
            text=alt.Text("Deger", format=",.0f"),
            order=alt.Order("Deger", sort="descending"),
            color=alt.value("black")
        )
        st.altair_chart(pie + text, use_container_width=True)
        st.info("Bu grafik, sadece paneli değil; işçilik, proje, kablolama ve montaj gibi **gizli giderleri** de içerdiğini gösterir.")

    with t3:
        df_m = pd.DataFrame({"Ay": ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"], "Üretim": aylik_uretim})
        st.bar_chart(df_m.set_index("Ay"), color="#f39c12")

    # İLETİŞİM
    st.markdown("---")
    st.subheader("📞 Teklif Alın")
    with st.form("contact"):
        col1, col2 = st.columns(2)
        ad = col1.text_input("Ad Soyad")
        firma = col1.text_input("Firma (Opsiyonel)")
        tel = col2.text_input("Telefon")
        email = col2.text_input("E-posta")
        notlar = st.text_area("Notlar")
        if st.form_submit_button("✅ GÖNDER", type="primary"):
            if ad and tel:
                if veritabanina_kaydet(ad, firma, tel, email, sehir, ilce, sistem_tipi, f"{girdi_deger}", notlar):
                    st.success("Alındı!")
                    st.balloons()
                else: st.error("Hata")
            else: st.warning("Ad ve Telefon giriniz.")
