import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# ========================================
# CONFIGURATION
# ========================================

st.set_page_config(
    page_title="OPCVM Scoring Dashboard V3",
    page_icon="📈",
    layout="wide"
)

# ========================================
# FONCTIONS
# ========================================

def normalize(series):

    series = series.fillna(0)

    if series.max() == series.min():
        return pd.Series(
            [1] * len(series),
            index=series.index
        )

    return (
        series - series.min()
    ) / (
        series.max() - series.min()
    )



def constrained_allocation(
        scores,
        min_weight=0.05,
        max_weight=0.20):

    w = scores / scores.sum()

    for _ in range(100):

        violation = False

        exc = w[w > max_weight]

        if not exc.empty:

            violation = True

            surplus = (
                exc - max_weight
            ).sum()

            w[exc.index] = max_weight

            free = w[w < max_weight]

            if len(free) > 0:

                w[free.index] += (
                    surplus
                    *
                    free
                    /
                    free.sum()
                )

        low = w[w < min_weight]

        if not low.empty:

            violation = True

            deficit = (
                min_weight - low
            ).sum()

            w[low.index] = min_weight

            free = w[w > min_weight]

            if len(free) > 0:

                w[free.index] -= (
                    deficit
                    *
                    free
                    /
                    free.sum()
                )

        if not violation:
            break

    return w / w.sum()


def notation(score):

    if score >= 0.80:
        return "A+"

    elif score >= 0.65:
        return "A"

    elif score >= 0.50:
        return "B"

    elif score >= 0.35:
        return "C"

    else:
        return "D"


# ========================================
# TITRE
# ========================================

st.title("📈 OPCVM Scoring Dashboard V3")

st.markdown(
    "Version institutionnelle - Allocation et sélection OPCVM"
)

# ========================================
# CHARGEMENT
# ========================================

uploaded_file = st.file_uploader(
    "Charger le fichier Excel",
    type=["xlsx"]
)

if uploaded_file is None:

    st.info(
        "Veuillez charger votre fichier."
    )

    st.stop()

# ========================================
# LECTURE
# ========================================

df = pd.read_excel(
    uploaded_file,
    sheet_name="Base_OPCVM"
)

# ========================================
# NETTOYAGE
# ========================================

df.columns = df.columns.str.strip()

df["OPCVM"] = (
    df["OPCVM"]
    .astype(str)
    .str.strip()
    .str.upper()
)

df["SDG"] = (
    df["SDG"]
    .astype(str)
    .str.strip()
)

df = df.replace("-", np.nan)

numeric_columns = [
    "AN",
    "Frais de gestion",
    "Perf_YTD",
    "Perf_1_ semaine",
    "Perf_1_ mois"
]

for col in numeric_columns:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

# ========================================
# ANOMALIES
# ========================================

anomalies = pd.DataFrame()

missing_rows = df[
    df[numeric_columns]
    .isnull()
    .any(axis=1)
]

if len(missing_rows):

    anomalies = pd.concat(
        [anomalies, missing_rows]
    )

# Remplacement des NA

for col in [
    "Perf_YTD",
    "Perf_1_ semaine",
    "Perf_1_ mois"
]:

    df[col] = df[col].fillna(0)

# Suppression si AN ou Frais manquent

df = df.dropna(
    subset=[
        "AN",
        "Frais de gestion"
    ]
)

# ========================================
# DOUBLONS
# ========================================

nb_before = len(df)

df = df.drop_duplicates(
    subset=["OPCVM"],
    keep="first"
)

nb_after = len(df)

doublons_supprimes = (
    nb_before - nb_after
)

# ========================================
# FILTRE AN
# ========================================

st.sidebar.header("⚙️ Paramètres")

an_min = st.sidebar.number_input(
    "AN minimum",
    value=100_000_000,
    step=100_000_000
)

df = df[
    df["AN"] >= an_min
]

# ========================================
# POIDS
# ========================================

poids_an = st.sidebar.slider(
    "AN",
    0.0,
    1.0,
    0.20,
    0.05
)

poids_frais = st.sidebar.slider(
    "Frais",
    0.0,
    1.0,
    0.20,
    0.05
)

poids_ytd = st.sidebar.slider(
    "Perf YTD",
    0.0,
    1.0,
    0.35,
    0.05
)

poids_week = st.sidebar.slider(
    "Perf semaine",
    0.0,
    1.0,
    0.25,
    0.05
)

poids_month = st.sidebar.slider(
    "Perf mois",
    0.0,
    1.0,
    0.00,
    0.05
)

top_n = st.sidebar.selectbox(
    "Top OPCVM",
    [5, 10, 15, 20],
    index=1
)

montant = st.sidebar.number_input(
    "Montant à investir",
    value=100_000_000
)

# ========================================
# NORMALISATION
# ========================================

df["AN_norm"] = normalize(df["AN"])

df["Frais_norm"] = normalize(
    df["Frais de gestion"].max()
    -
    df["Frais de gestion"]
)

df["YTD_norm"] = normalize(
    df["Perf_YTD"]
)

df["Semaine_norm"] = normalize(
    df["Perf_1_ semaine"]
)

df["Mois_norm"] = normalize(
    df["Perf_1_ mois"]
)

# ========================================
# SCORE
# ========================================

total = (
    poids_an
    + poids_frais
    + poids_ytd
    + poids_week
    + poids_month
)

df["Score"] = (

    df["AN_norm"] * poids_an

    + df["Frais_norm"] * poids_frais

    + df["YTD_norm"] * poids_ytd

    + df["Semaine_norm"] * poids_week

    + df["Mois_norm"] * poids_month

) / total

df = df.sort_values(
    "Score",
    ascending=False
)

df["Rang"] = range(
    1,
    len(df) + 1
)

df["Note"] = df["Score"].apply(
    notation
)

# ========================================
# TOP
# ========================================

portefeuille = (
    df.head(top_n)
    .copy()
)

portefeuille["Allocation"] = (

    constrained_allocation(
        portefeuille["Score"]
    )

    * 100

)

portefeuille["Volume"] = (

    montant

    * portefeuille["Allocation"]

    / 100

)

# ========================================
# KPI
# ========================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "OPCVM",
    len(df)
)

c2.metric(
    "Doublons supprimés",
    doublons_supprimes
)

c3.metric(
    "Top retenu",
    top_n
)

c4.metric(
    "Allocation totale",
    f"{portefeuille['Allocation'].sum():.2f}%"
)

# ========================================
# CLASSEMENT
# ========================================

st.subheader(
    "🏆 Classement général"
)

st.dataframe(
    df[
        [
            "Rang",
            "OPCVM",
            "SDG",
            "Score",
            "Note"
        ]
    ],
    hide_index=True,
    use_container_width=True
)

# ========================================
# PORTEFEUILLE
# ========================================

st.subheader(
    "🎯 Portefeuille cible"
)

st.dataframe(
    portefeuille[
        [
            "Rang",
            "OPCVM",
            "Score",
            "Note",
            "Allocation",
            "Volume"
        ]
    ],
    hide_index=True,
    use_container_width=True
)

# ========================================
# TOP 10 BAR
# ========================================

fig_bar = px.bar(
    portefeuille,
    x="OPCVM",
    y="Score",
    color="Score"
)

st.plotly_chart(
    fig_bar,
    use_container_width=True
)

# ========================================
# HEATMAP
# ========================================

st.subheader(
    "🔥 Heatmap"
)

heat = portefeuille.set_index(
    "OPCVM"
)[
[
"AN_norm",
"Frais_norm",
"YTD_norm",
"Semaine_norm",
"Mois_norm",
"Score"
]
]

st.plotly_chart(
    px.imshow(
        heat,
        text_auto=".2f",
        color_continuous_scale="RdYlGn"
    ),
    use_container_width=True
)

# ========================================
# SDG
# ========================================

st.subheader(
    "🏦 Répartition par SDG"
)

sdg = (
    portefeuille
    .groupby("SDG")
    ["Allocation"]
    .sum()
  
