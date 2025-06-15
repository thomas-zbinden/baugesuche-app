# -*- coding: utf-8 -*-
"""
Created on Sun Jun 15 18:29:24 2025

@author: thoma
"""

# Öffentliche Baugesuche – Kanton Bern (Streamlit App)

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import warnings
import locale
from babel.dates import format_date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

# Seite konfigurieren
try:
    st.set_page_config(page_title="Baugesuche Kanton Bern", layout="wide")
except RuntimeError as e:
    if "can only be called once" in str(e):
        warnings.warn("⚠️ Streamlit set_page_config wurde bereits aufgerufen – wird übersprungen.")
    else:
        raise e

# Spracheinstellung
sprachen = {"Deutsch": "de", "Français": "fr"}
sprache = st.sidebar.radio("🌐 Sprache wählen", list(sprachen.keys()))
lang = sprachen[sprache]
locale.setlocale(locale.LC_TIME, f"{lang}_CH.UTF-8")

st.title("📋 " + ("Baugesuche Kanton Bern" if lang == "de" else "Mises à l'enquête – Canton de Berne"))

# Datumsauswahl & manuelles Refresh
datum_ab = st.date_input("📅 Zeige Baugesuche ab" if lang == "de" else "Afficher les mises à l'enquête dès", datetime(2025, 5, 1))
if st.button("🔄 Jetzt aktualisieren" if lang == "de" else "🔄 Actualiser maintenant"):
    st.cache_data.clear()
    st.experimental_rerun()

API_URL = "https://services7.arcgis.com/3m6RvGQbF9eE88hU/arcgis/rest/services/Baugesuche/FeatureServer/0/query"

def to_arcgis_timestamp(date_obj):
    return int(datetime.combine(date_obj, datetime.min.time()).timestamp() * 1000)

@st.cache_data
def lade_baugesuche(datum_ab):
    params = {
        "where": f"Eingangsdatum >= {to_arcgis_timestamp(datum_ab)}",
        "outFields": "*",
        "returnGeometry": True,
        "f": "json"
    }

    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        st.error("❌ Fehler beim Abrufen der Daten. Bitte versuche es später erneut." if lang == "de" else "❌ Erreur lors du chargement des données.")
        return pd.DataFrame()

    eintraege = []
    for f in data.get("features", []):
        a, g = f.get("attributes", {}), f.get("geometry", {})
        eintraege.append({
            "Projektname": a.get("Projektname", "Unbekannt"),
            "Ort": a.get("Ort", "Unbekannt"),
            "Parzelle": a.get("ParzellenNr", ""),
            "Bauherr": a.get("Gesuchsteller", ""),
            "Auflagefrist": datetime.fromtimestamp(a.get("AuflageFrist", 0) / 1000).date() if a.get("AuflageFrist") else None,
            "Eingangsdatum": datetime.fromtimestamp(a.get("Eingangsdatum", 0) / 1000).date() if a.get("Eingangsdatum") else None,
            "latitude": g.get("y"),
            "longitude": g.get("x")
        })

    df = pd.DataFrame(eintraege)
    df["Auflagefrist"] = pd.to_datetime(df["Auflagefrist"]).dt.date

    if "last_count" not in st.session_state:
        st.session_state.last_count = 0
    neue = len(df) - st.session_state.last_count
    if neue > 0:
        st.info(f"📢 {neue} neue Baugesuche seit dem letzten Besuch.")
    st.session_state.last_count = len(df)

    return df.sort_values(by="Eingangsdatum", ascending=False).reset_index(drop=True)

# Daten laden
with st.spinner("🔄 Lade Baugesuche..." if lang == "de" else "🔄 Chargement..."):
    df = lade_baugesuche(datum_ab)

if df.empty:
    st.warning("⚠️ Keine Baugesuche gefunden." if lang == "de" else "⚠️ Aucune mise à l'enquête trouvée.")
    st.stop()

# Filter
gemeinden = sorted(df["Ort"].dropna().unique())
gewaehlte_gemeinden = st.multiselect("🏨 Gemeinde filtern" if lang == "de" else "🏨 Commune", gemeinden)
if gewaehlte_gemeinden:
    df = df[df["Ort"].isin(gewaehlte_gemeinden)]

nur_laufende = st.checkbox("📅 Nur laufende Fristen" if lang == "de" else "📅 Frist en cours", value=False)
if nur_laufende:
    heute = datetime.today().date()
    df = df[df["Auflagefrist"].isna() | (df["Auflagefrist"] >= heute)]
    st.caption("🔎 Nur mit gültiger Auflagefrist." if lang == "de" else "🔎 Avec délai encore valable.")

# Sortierung
sortieroptionen = {
    "Eingangsdatum (neueste zuerst)": ("Eingangsdatum", False),
    "Eingangsdatum (älteste zuerst)": ("Eingangsdatum", True),
    "Auflagefrist (nächste zuerst)": ("Auflagefrist", True),
    "Auflagefrist (späteste zuerst)": ("Auflagefrist", False)
}
sortierung = st.selectbox("🔃 Sortierung", list(sortieroptionen.keys()))
spalte, aufsteigend = sortieroptionen[sortierung]
df = df.sort_values(by=spalte, ascending=aufsteigend)

# Suche
suchtext = st.text_input("🔎 Suche (Projektname, Ort, Bauherr)" if lang == "de" else "🔎 Recherche (nom, commune, maître d'œuvre)")
df_export = df.drop(columns=["latitude", "longitude"])
if suchtext:
    suchtext = suchtext.lower()
    df_export = df_export[df_export.astype(str).apply(lambda x: x.str.lower().str.contains(suchtext).any(), axis=1)]

st.success(f"✅ {len(df_export)} Baugesuche gefunden." if lang == "de" else f"✅ {len(df_export)} mises à l'enquête trouvées.")
st.dataframe(df_export, use_container_width=True)
