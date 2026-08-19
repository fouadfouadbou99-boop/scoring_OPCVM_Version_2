import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(
    page_title="OPCVM Scoring Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 OPCVM Scoring Dashboard")

# ---------------------------------------------------
# FONCTIONS
# ---------------------------------------------------

def normalize(series):

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


def allocation_contrainte(scores,
                           min_weight=0.05,
                           max_weight=0.20):

    w = scores / scores.sum()

    w = w.clip(
        lower=min_weight,
        upper=max_weight
    )

    for _ in range(200):

        diff = 1 - w.sum()

        if abs(diff) < 0.000001:
            break

        libres = (
            (w > min_weight)
            &
            (w < max_weight)
        )

        if libres.sum() == 0:
            break

        w.loc[libres] += (
            diff / libres.sum()
        )

        w = w.clip(
            lower=min_weight,
            upper=max_weight
        )

    return w / w.sum()

# ---------------------------------------------------
# CHARGEMENT
# ---------------------------------------------------

uploaded_file = st.file_uploader(
    "Charger le fichier Excel",
    type="xlsx"
)

if uploaded_file:

    df = pd.read_excel(
        uploaded_file,
        sheet_name="Base_OPCVM"
    )

    st.success("Fichier chargé")

    # Nettoyage
    df = df.replace("-", np.nan)

    for col in [
        "AN",
        "Frais de gestion",
        "Perf_YTD",
        "Perf_1_ semaine",
        "Perf_1_ mois"
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna(
        subset=[
            "AN",
            "Frais de gestion",
            "Perf_YTD"
        ]
    )

    # ------------------------------------------------
    # PARAMETRES
    # ------------------------------------------------

    st.sidebar.header("⚙️ Poids")

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
        "Perf 1 semaine",
        0.0,
        1.0,
        0.25,
        0.05
    )

    poids_month = st.sidebar.slider(
        "Perf 1 mois",
        0.0,
        1.0,
        0.00,
        0.05
    )

    top_n = st.sidebar.selectbox(
        "Nombre d'OPCVM retenus",
        [10, 15, 20],
        index=0
    )

    montant = st.sidebar.number_input(
        "Montant à investir (MAD)",
        value=100000000
    )

    total_poids = (
        poids_an
        + poids_frais
        + poids_ytd
        + poids_week
        + poids_month
    )

    # ------------------------------------------------
    # NORMALISATION
    # ------------------------------------------------

    score_df = df.copy()

    score_df["AN_norm"] = normalize(
        score_df["AN"]
    )

    score_df["Frais_norm"] = normalize(
        score_df["Frais de gestion"].max()
        -
        score_df["Frais de gestion"]
    )

    score_df["YTD_norm"] = normalize(
        score_df["Perf_YTD"]
    )

    score_df["Semaine_norm"] = normalize(
        score_df["Perf_1_ semaine"]
    )

    score_df["Mois_norm"] = normalize(
        score_df["Perf_1_ mois"]
    )

    # ------------------------------------------------
    # SCORE
    # ------------------------------------------------

    score_df["Score"] = (

        score_df["AN_norm"] * poids_an

        + score_df["Frais_norm"] * poids_frais

        + score_df["YTD_norm"] * poids_ytd

        + score_df["Semaine_norm"] * poids_week

        + score_df["Mois_norm"] * poids_month

    ) / total_poids

    score_df = score_df.sort_values(
        "Score",
        ascending=False
    )

    score_df["Rang"] = range(
        1,
        len(score_df) + 1
    )

    # ------------------------------------------------
    # TOP N
    # ------------------------------------------------

    portefeuille = score_df.head(
        top_n
    ).copy()

    portefeuille["Allocation"] = (
        allocation_contrainte(
            portefeuille["Score"]
        ) * 100
    )

    portefeuille["Volume"] = (
        montant
        *
        portefeuille["Allocation"]
        / 100
    )

    # ------------------------------------------------
    # KPI
    # ------------------------------------------------

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "OPCVM analysés",
        len(score_df)
    )

    c2.metric(
        "Top retenus",
        top_n
    )

    c3.metric(
        "Montant",
        f"{montant:,.0f} MAD"
    )

    # ------------------------------------------------
    # CLASSEMENT
    # ------------------------------------------------

    st.subheader(
        "🏆 Classement général"
    )

    st.dataframe(
        score_df[
            [
                "Rang",
                "OPCVM",
                "SDG",
                "Score"
            ]
        ],
        use_container_width=True
    )

    # ------------------------------------------------
    # TOP N
    # ------------------------------------------------

    st.subheader(
        "🎯 Portefeuille cible"
    )

    st.dataframe(
        portefeuille[
            [
                "Rang",
                "OPCVM",
                "Score",
                "Allocation",
                "Volume"
            ]
        ],
        use_container_width=True
    )

    # ------------------------------------------------
    # BAR CHART
    # ------------------------------------------------

    fig_bar = px.bar(
        portefeuille,
        x="OPCVM",
        y="Score",
        color="Score",
        text="Score"
    )

    st.plotly_chart(
        fig_bar,
        use_container_width=True
    )

    # ------------------------------------------------
    # RADAR
    # ------------------------------------------------

    st.subheader("🕸 Radar")

    radar_selection = st.multiselect(
        "Comparer",
        portefeuille["OPCVM"],
        default=list(
            portefeuille.head(3)["OPCVM"]
        )
    )

    if radar_selection:

        fig = go.Figure()

        for _, row in portefeuille[
            portefeuille["OPCVM"]
            .isin(radar_selection)
        ].iterrows():

            values = [
                row["AN_norm"],
                row["Frais_norm"],
                row["YTD_norm"],
                row["Semaine_norm"],
                row["Mois_norm"]
            ]

            fig.add_trace(
                go.Scatterpolar(
                    r=values + [values[0]],
                    theta=[
                        "AN",
                        "Frais",
                        "YTD",
                        "Semaine",
                        "Mois",
                        "AN"
                    ],
                    fill="toself",
                    name=row["OPCVM"]
                )
            )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ------------------------------------------------
    # HEATMAP
    # ------------------------------------------------

    st.subheader("🔥 Heatmap")

    heatmap_df = portefeuille.set_index(
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

    fig_heat = px.imshow(
        heatmap_df,
        text_auto=".2f",
        color_continuous_scale="RdYlGn",
        aspect="auto"
    )

    st.plotly_chart(
        fig_heat,
        use_container_width=True
    )

    # ------------------------------------------------
    # EXPORT
    # ------------------------------------------------

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter"
    ) as writer:

        portefeuille.to_excel(
            writer,
            sheet_name="Portefeuille",
            index=False
        )

    st.download_button(
        "📥 Télécharger Excel",
        data=output.getvalue(),
        file_name="Portefeuille_OPCVM.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:

    st.info(
        "Chargez le fichier Excel."
    )
