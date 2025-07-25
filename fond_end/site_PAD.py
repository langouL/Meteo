import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import folium
from streamlit_folium import st_folium
from datetime import datetime
from alerte import get_weather_icon
import uuid
import time


st.set_page_config(page_title="Météo Douala", layout="wide")
st.title("🌦️ Tableau de bord MeteoMarine – Port Autonome de Doula")

# --- Chargement données ---
API_URL = "https://data-real-time-2.onrender.com/donnees?limit=50000000000"
data = requests.get(API_URL).json()
df = pd.DataFrame(data)

df["DateTime"] = pd.to_datetime(df["DateTime"])
df = df.sort_values("DateTime", ascending=False)

# --- Filtre date ---
st.sidebar.header("📅 Filtrer par date")
min_date = df["DateTime"].min().date()
max_date = df["DateTime"].max().date()
start_date, end_date = st.sidebar.date_input("Plage de dates", [min_date, max_date])
df = df[(df["DateTime"].dt.date >= start_date) & (df["DateTime"].dt.date <= end_date)]

# --- Aperçu météo ---
st.subheader("📍 Aperçu MeteoMarinePAD – données en Direct")
for _, row in df.head(3).iterrows():
    date_heure = row["DateTime"].strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(f"""
    #### 📍 Station {row['Station']}
    - 🕒 Observation : {date_heure}
    - 🌡️ Température : {row['AIR TEMPERATURE']}°C {get_weather_icon(float(row['AIR TEMPERATURE']))}
    - 💧 Humidité : {row['HUMIDITY']}% {"🔴" if float(row['HUMIDITY']) > 98 else "💧"}
    - 💨 Vent : {row['WIND SPEED']} m/s
    - 🧭 Pression : {row['AIR PRESSURE']} hPa
    """)
    if "TIDE HEIGHT" in row:
        st.markdown(f"- 🌊 Marée : {row['TIDE HEIGHT']} m")
    if "SURGE" in row:
        st.markdown(f"- ⚠️ SURGE : {row['SURGE']} m")

# --- Carte interactive ---
st.subheader("🗺️ Carte interactive des stations météo")

m = folium.Map(location=[4.05, 9.68], zoom_start=10)

# On affiche uniquement les dernières données par station
stations_grouped = df.groupby("Station").first().reset_index()

for _, row in stations_grouped.iterrows():
    last_date = row["DateTime"].strftime("%Y-%m-%d %H:%M:%S")

    popup_html = f"""
    <div style="width: 250px; font-size: 13px; background-color: #f8f9fa;
                border: 1px solid #ddd; border-radius: 8px; padding: 10px;">
        <h4 style="margin-top: 0; color: #007bff;">📍 {row['Station']}</h4>
        <p><b>📅 Date :</b> {last_date}</p>
        <p><b>🌡️ Température :</b> {row['AIR TEMPERATURE']} °C</p>
        <p><b>💨 Vent :</b> {row['WIND SPEED']} m/s</p>
        <p><b>💧 Humidité :</b> {row['HUMIDITY']} %</p>
        <p><b>🧭 Pression :</b> {row['AIR PRESSURE']} hPa</p>
        {f"<p><b>🌊 Marée :</b> {row['TIDE HEIGHT']} m</p>" if "TIDE HEIGHT" in row else ""}
        {f"<p><b>⚠️ SURGE :</b> {row['SURGE']} m</p>" if "SURGE" in row else ""}
    </div>
    """

    popup = folium.Popup(popup_html, max_width=300)

    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],
        popup=popup,
        tooltip=row["Station"],
        icon=folium.Icon(color="blue", icon="cloud")
    ).add_to(m)

# Affichage dans Streamlit
st_folium(m, width=900, height=500)



# --- Graphiques et comparaisons ---
st.subheader("📈 Graphique par station et paramètre")

station_selected = st.selectbox("Station", df["Station"].unique())
params = ["AIR TEMPERATURE", "HUMIDITY", "WIND SPEED", "AIR PRESSURE"]

if "TIDE HEIGHT" in df.columns:
    params.append("TIDE HEIGHT")
if "SURGE" in df.columns:
    params.append("SURGE")

param = st.selectbox("Paramètre", params)

df_station = df[df["Station"] == station_selected].copy()

# Conversion en numérique
df_station[param] = pd.to_numeric(df_station[param], errors='coerce')

# Supprimer les valeurs NaN
df_station = df_station.dropna(subset=[param])

# Supprimer les très petites valeurs de TIDE HEIGHT
if param == "TIDE HEIGHT":
    df_station = df_station[df_station[param] >= 0.3]  # seuil ajusté ici

# Filtrage par date
df_station = df_station[
    (df_station["DateTime"].dt.date >= start_date) &
    (df_station["DateTime"].dt.date <= end_date)
]

# Génération du graphique
fig = px.line(df_station, x="DateTime", y=param, title=f"{param} à {station_selected}")

# ✅ Ajout d'une clé unique basée sur station + paramètre
st.plotly_chart(fig, use_container_width=True, key=f"{station_selected}_{param}")


# === 📊 Comparaison entre stations ===
st.subheader("📊 Comparaison multistation")

# Copie pour conversion numérique
df_numeric = df.copy()
for p in params:
    df_numeric[p] = pd.to_numeric(df_numeric[p], errors='coerce')

for p in params:
    df_plot = df_numeric.dropna(subset=[p])
    df_plot = df_plot[(df_plot["DateTime"].dt.date >= start_date) & (df_plot["DateTime"].dt.date <= end_date)]

    fig = px.line(df_plot, x="DateTime", y=p, color="Station", title=f"Comparaison – {p}")
    if p == "TIDE HEIGHT":
        max_val = df_plot[p].max()
        if pd.notnull(max_val):
            fig.update_yaxes(range=[0, max_val + 0.5])
    st.plotly_chart(fig, use_container_width=True)

# === 🌐 Mini-carte météo Windy ===
st.subheader("🌐 Carte météo animée – Windy")
st.components.v1.html('''
<iframe width="100%" height="450" src="https://embed.windy.com/embed2.html?lat=4.05&lon=9.68&detailLat=4.05&detailLon=9.68&zoom=9&type=wind" frameborder="0"></iframe>
''', height=450)

# === 🆕 GESTION DEMANDES DE TÉLÉCHARGEMENT ===

if "demandes" not in st.session_state:
    st.session_state["demandes"] = []

st.subheader("💾 Demande de téléchargement des données météo")

with st.form("form_demande"):
    nom = st.text_input("Votre nom")
    structure = st.text_input("Structure")
    email = st.text_input("Votre email")
    raison = st.text_area("Raison de la demande")
    submit = st.form_submit_button("Envoyer la demande")

if submit:
    if not nom or not structure or not email or not raison:
        st.error("Tous les champs sont requis.")
    else:
        demande_id = str(uuid.uuid4())
        st.session_state["demandes"].append({
            "id": demande_id,
            "nom": nom,
            "structure": structure,
            "email": email,
            "raison": raison,
            "statut": "en attente",
            "token": None,
            "timestamp": None
        })
        st.success("Demande envoyée. En attente de validation par l'administrateur.")

# Vérifie si une demande acceptée existe et si le temps n'a pas expiré
user_demande = None
for d in st.session_state["demandes"]:
    if d["email"] == email and d["statut"] == "acceptée":
        if d["timestamp"] and time.time() - d["timestamp"] <= 60:
            user_demande = d
        else:
            d["statut"] = "expirée"

if user_demande:
    st.success("✅ Votre demande est acceptée. Vous avez 60 secondes pour télécharger.")
    
    # Colonnes dans l'ordre souhaité
    cols_order = [
        "Station",
        "Latitude",
        "Longitude",
        "DateTime",
        "TIDE HEIGHT",
        "WIND SPEED",
        "WIND DIR",
        "AIR PRESSURE",
        "AIR TEMPERATURE",
        "DEWPOINT",
        "HUMIDITY", 
    ]

    # Ajouter TIDE HEIGHT si présente
    if "TIDE HEIGHT" in df.columns:
        cols_order.append("TIDE HEIGHT")

    # Créer DataFrame pour export avec colonnes ordonnées
    df_export = df[cols_order]

    # Convertir en CSV
    csv = df_export.to_csv(index=False).encode("utf-8")

    # Bouton de téléchargement
    st.download_button(
        label="📥 Télécharger les données météo",
        data=csv,
        file_name="MeteoMarinePAD.csv",
        mime="text/csv"
    )

else:
    if any(d["email"] == email and d["statut"] == "expirée" for d in st.session_state["demandes"]):
        st.warning("⏱️ Le lien a expiré. Veuillez refaire une demande.")

# --- Admin ---
st.sidebar.header("🔐 Admin")

admin_password = st.sidebar.text_input("Mot de passe admin", type="password")
if admin_password == "LANGOUL":  # Change ce mot de passe !
    st.sidebar.success("Accès admin autorisé")

    # --- Demandes en attente ---
    demandes_attente = [d for d in st.session_state["demandes"] if d["statut"] == "en attente"]
    st.sidebar.markdown("### 📥 Demandes en attente")

    for d in demandes_attente:
        st.sidebar.markdown(f"**{d['nom']} ({d['email']})**")
        st.sidebar.markdown(f"Structure : {d['structure']}")
        st.sidebar.markdown(f"Raison : {d['raison']}")
        col1, col2 = st.sidebar.columns(2)
        if col1.button(f"✅ Accepter {d['id']}", key=f"acc_{d['id']}"):
            d["statut"] = "acceptée"
            d["token"] = str(uuid.uuid4())
            d["timestamp"] = time.time()
            st.sidebar.success(f"Demande acceptée pour {d['nom']}")
        if col2.button(f"❌ Refuser {d['id']}", key=f"ref_{d['id']}"):
            d["statut"] = "refusée"
            d["timestamp"] = time.time()
            st.sidebar.warning(f"Demande refusée pour {d['nom']}")

    # --- Historique des décisions (acceptées et refusées) ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Historique des décisions")

    demandes_traitees = [d for d in st.session_state["demandes"] if d["statut"] in ["acceptée", "refusée"]]
    st.sidebar.markdown(f"**Total traité :** {len(demandes_traitees)}")

    for d in demandes_traitees:
        heure = datetime.fromtimestamp(d["timestamp"]).strftime("%Y-%m-%d %H:%M:%S") if d["timestamp"] else "Non défini"
        couleur = "🟢" if d["statut"] == "acceptée" else "🔴"
        st.sidebar.markdown(f"""
        {couleur} **{d['nom']}**  
        📧 {d['email']}  
        🏢 {d['structure']}  
        📌 Raison : {d['raison']}  
        🕒 {heure}
        """)

    # --- Export CSV des décisions traitées ---
    if demandes_traitees:
        df_export = pd.DataFrame(demandes_traitees)
        df_export["Horodatage"] = df_export["timestamp"].apply(
            lambda ts: datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""
        )
        df_export = df_export[["nom", "email", "structure", "raison", "statut", "Horodatage"]]

        st.sidebar.download_button(
            label="📤 Exporter tout l’historique CSV",
            data=df_export.to_csv(index=False).encode("utf-8"),
            file_name="historique_acces_complet.csv",
            mime="text/csv"
        )


elif admin_password != "":
    st.sidebar.error("Mot de passe incorrect.")

