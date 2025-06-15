import streamlit as st
import geopandas as gpd
import pandas as pd
import requests
import zipfile
import io
from babel.dates import format_date
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

# Sprache wählen
lang = st.selectbox("Sprache wählen", ["de", "fr", "it", "en"])

# Daten laden
@st.cache_data
def load_data():
    url = "https://www.geo.apps.be.ch/pub/download/BAUGES.zip"
    r = requests.get(url)
    with zipfile.ZipFile(io.BytesIO(r.content)) as zip_ref:
        zip_ref.extractall("data")
    gdf = gpd.read_file("data/BAUGES.shp")
    gdf = gdf.to_crs(epsg=4326)  # WGS84 für Karte
    return gdf

gdf = load_data()

# Datumskonvertierung
gdf["DATUM_EIN"] = pd.to_datetime(gdf["DATUM_EIN"], errors="coerce")

# Filteroptionen
st.sidebar.markdown("### Filter")
date_from = st.sidebar.date_input("Von Datum", datetime.today() - timedelta(days=30))
gdf_filtered = gdf[gdf["DATUM_EIN"] >= pd.Timestamp(date_from)]

# Kartenanzeige
st.markdown("## Baugesuche Kanton Bern")
m = folium.Map(location=[46.948, 7.447], zoom_start=9)

for _, row in gdf_filtered.iterrows():
    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        popup=f"{row['BEZEICHNUN']} ({row['DATUM_EIN'].date()})"
    ).add_to(m)

st_data = st_folium(m, width=700, height=500)

# Datentabelle anzeigen
st.dataframe(gdf_filtered[["BEZEICHNUN", "DATUM_EIN", "GEMEINDE", "BAUHER", "VORHABEN"]])

# PDF-Export
def create_pdf(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica", 12)
    c.drawString(50, y, "Baugesuche Kanton Bern")
    y -= 30
    for _, row in data.iterrows():
        try:
            date_str = format_date(row["DATUM_EIN"], locale=lang)
        except:
            date_str = str(row["DATUM_EIN"])
        line = f"{row['BEZEICHNUN']} – {date_str} – {row['GEMEINDE']}"
        c.drawString(50, y, line)
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return buffer

if st.button("Exportiere als PDF"):
    pdf = create_pdf(gdf_filtered)
    st.download_button("Download PDF", data=pdf, file_name="baugesuche_bern.pdf", mime="application/pdf")



