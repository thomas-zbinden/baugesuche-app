import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import locale
from babel.dates import format_date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

# Sprachwahl
lang = st.selectbox("Sprache wählen", ["de", "fr", "it", "en"])

# 🌍 Locale setzen – robust gegen Fehler
try:
    locale.setlocale(locale.LC_TIME, f"{lang}_CH.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, f"{lang}_DE.UTF-8")
    except locale.Error:
        locale.setlocale(locale.LC_TIME, "")  # Fallback

# Daten abrufen
@st.cache_data
def get_data():
    url = "https://data.stadt-zuerich.ch/api/explore/v2.1/catalog/datasets/arcgis_baugesuche/exports/csv"
    return pd.read_csv(url)

df = get_data()

# Datum umwandeln
df["gesuchsdatum"] = pd.to_datetime(df["gesuchsdatum"], errors="coerce")

# Filters
today = pd.Timestamp.now()
df_filtered = df[df["gesuchsdatum"] >= today - pd.Timedelta(days=30)]

# Anzeigen
st.title("Baugesuche Stadt Zürich")
st.dataframe(df_filtered[["gesuchsnummer", "gesuchsdatum", "strasse", "vorhaben", "bauherrschaft"]])

# PDF Export
def create_pdf(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica", 12)
    c.drawString(50, y, "Baugesuche Stadt Zürich")
    y -= 30
    for i, row in data.iterrows():
        date_str = format_date(row["gesuchsdatum"], locale=lang)
        c.drawString(50, y, f"{row['gesuchsnummer']} – {date_str} – {row['strasse']}")
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return buffer

if st.button("Exportiere als PDF"):
    pdf = create_pdf(df_filtered)
    st.download_button("Download PDF", data=pdf, file_name="baugesuche.pdf", mime="application/pdf")
    