import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
import zipfile
import io
from datetime import datetime
from babel.dates import format_date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

st.set_page_config(page_title="Baugesuche Kanton Bern", layout="wide")

# Sprachwahl
lang = st.selectbox("Sprache wählen", ["de", "fr", "it", "en"])

# Funktion: Lade und entpacke Baugesuche ZIP
@st.cache_data
def load_data():
    url = "https://www.geo.apps.be.ch/pub/download/BAUGES.zip"
    r = requests.get(url)
    with zipfile.ZipFile(io.BytesIO(r.content)) as zip_ref:
        zip_ref.extractall("data")
    gdf = gpd.read_file("data/BAUGES.shp")
    return gdf

# Daten laden
with st.spinner("Lade Baugesuche des Kantons Bern..."):
    gdf = load_data()

# Datum umwandeln
gdf["DATUM"] = pd.to_datetime(gdf["DATUM"], errors="coerce")

# Filter: Nur letzte 30 Tage
today = pd.Timestamp.now()
df_filtered = gdf[gdf["DATUM"] >= today - pd.Timedelta(days=30)]

# Spaltenauswahl zur Anzeige
columns_to_show = ["AKTENNUMM", "DATUM", "VORHABEN", "BAUHERR", "STRASSE", "PLZ", "ORTSCHAFT"]
st.title("Baugesuche Kanton Bern (letzte 30 Tage)")
st.dataframe(df_filtered[columns_to_show])

# Funktion: PDF generieren
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
            date_str = format_date(row["DATUM"], locale=lang)
        except:
            date_str = row["DATUM"].strftime("%Y-%m-%d")
        line = f"{row['AKTENNUMM']} – {date_str} – {row['STRASSE']} {row['PLZ']} {row['ORTSCHAFT']}"
        c.drawString(50, y, line[:110])  # kürzen, falls zu lang
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return buffer

# PDF-Button
if st.button("Exportiere als PDF"):
    pdf = create_pdf(df_filtered)
    st.download_button("Download PDF", data=pdf, file_name="baugesuche_be.pdf", mime="application/pdf")


