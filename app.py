import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO

# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="OPCVM Scoring Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 OPCVM Scoring Dashboard")

# =====================================================
# POIDS PAR DEFAUT
# =====================================================

DEFAULT_WEIGHTS = {
    "AN": 0.20,
    "FRAIS": 0.20,
    "YTD": 0.35,
    "SEMAINE": 0.25,
    "MOIS": 0.00
}

for k, v in DEFAULT_WEIGHTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("⚙️ Paramétrage")

if st.sidebar.button("🔄 Réinitialiser les poids"):
    for k, v in DEFAULT_WEIGHTS.items():
        st.session_state[k] = v
    st.rerun()

poids_an = st.sidebar.slider(
    "Actif Net",
    0.0,
    1.0,
    key="AN",
    step=0.05
)

poids_frais = st.sidebar.slider(
    "Frais de gestion",
    0.0,
    1.0,
    key="FRAIS",
    step=0.05
)

poids_ytd = st.sidebar.slider(
    "Performance YTD",
    0.0,
    1.0,
    key="YTD",
    step=0.05
)

poids_semaine = st.sidebar.slider(
    "Performance 1 semaine",
    0.0,
    1.0,
    key="SEMAINE",
    step=0.05
)

poids_mois = st.sidebar.slider(
    "Performance 1 mois",
    0.0,
    1.0,
    key="MOIS",
    step=0.05
)

montant = st.sidebar.number_input(
    "Montant à investir (MAD)",
    min_value=100000,
    value=10000000,
    step=100000
)

# =====================================================
# CHARGEMENT
# =====================================================

uploaded_file = st.file_uploader(
    "📂 Charger le fichier Excel",
    type=["xlsx"]
)

if uploaded_file:

    df = pd.read_excel(
        uploaded_file,
        sheet_name="Base_OPCVM"
    )

    # ====================================
    # Nettoyage
    # ====================================

    df.replace("-", np.nan, inplace=True)

    colonnes_num = [
        "AN",
        "Frais de gestion",
        "Perf_YTD",
        "Perf_1_ semaine",
        "Perf_1_ mois"
    ]

    for c in colonnes_num:
        df[c] = pd.to_numeric(
            df[c],
            errors="coerce"
        )

    # supprimer doublons OPCVM
    df = df.drop_duplicates(
        subset=["OPCVM"]
    )

    # conserver seulement OPCVM renseignés
    df = df.dropna(
        subset=[
            "Perf_YTD",
            "Perf_1_ semaine"
        ]
    )

    # ====================================
    # Filtre catégorie
    # ====================================

    categorie = st.selectbox(
        "Catégorie",
        [
            "Toutes",
            "Monétaire"
        ]
    )

    if categorie == "Monétaire":

        mots = [
            "CASH",
            "MONETAIRE",
            "MONÉTAIRE",
            "TRESOR",
            "TRESORERIE",
            "LIQUID"
        ]

        mask = (
            df["OPCVM"]
            .str.upper()
            .str.contains(
                "|".join(mots),
                na=False
            )
        )

        df = df[mask]

    # ====================================
    # Normalisation
    # ====================================

    def normalize(s):

        if s.max() == s.min():
            return np.ones(len(s))

        return (
            (s - s.min())
            /
            (s.max() - s.min())
        )

    df["AN_norm"] = normalize(df["AN"])

    df["Frais_norm"] = (
        (
            df["Frais de gestion"].max()
            -
            df["Frais de gestion"]
        )
        /
        (
            df["Frais de gestion"].max()
            -
            df["Frais de gestion"].min()
        )
    )

    df["YTD_norm"] = normalize(
        df["Perf_YTD"]
    )

    df["Semaine_norm"] = normalize(
        df["Perf_1_ semaine"]
    )

    df["Mois_norm"] = normalize(
        df["Perf_1_ mois"].fillna(0)
    )

    # ====================================
    # SCORE
    # ====================================

    total_poids = (
        poids_an
        + poids_frais
        + poids_ytd
        + poids_semaine
        + poids_mois
    )

    df["Score"] = (

        poids_an * df["AN_norm"]

        + poids_frais * df["Frais_norm"]

        + poids_ytd * df["YTD_norm"]

        + poids_semaine * df["Semaine_norm"]

        + poids_mois * df["Mois_norm"]

    ) / total_poids

    # ====================================
    # Classement
    # ====================================

    df = df.sort_values(
        "Score",
        ascending=False
    )

    df["Rang"] = range(
        1,
        len(df) + 1
    )

    st.subheader("🏆 Classement")

    st.dataframe(
        df[
            [
                "Rang",
                "OPCVM",
                "Score",
                "AN",
                "Perf_YTD"
            ]
        ],
        use_container_width=True
    )

    # ====================================
    # TOP 10 + ALLOCATION
    # ====================================

    top10 = df.head(10).copy()

    somme_score = top10["Score"].sum()

    top10["Allocation_%"] = (
        top10["Score"]
        /
        somme_score
        * 100
    )

    top10["Montant_MAD"] = (
        top10["Allocation_%"]
        /
        100
        * montant
    )

    st.subheader("📈 Allocation Top 10")

    st.dataframe(
        top10[
            [
                "Rang",
                "OPCVM",
                "Score",
                "Allocation_%",
                "Montant_MAD"
            ]
        ]
        .style.format({
            "Score": "{:.3f}",
            "Allocation_%": "{:.2f}%",
            "Montant_MAD": "{:,.0f}"
        }),
        use_container_width=True
    )

    # ====================================
    # Pie Chart
    # ====================================

    fig_pie = px.pie(
        top10,
        names="OPCVM",
        values="Allocation_%",
        title="Allocation proposée"
    )

    st.plotly_chart(
        fig_pie,
        use_container_width=True
    )

    # ====================================
    # Heatmap
    # ====================================

    st.subheader("🔥 Heatmap")

    heatmap_df = top10[
        [
            "OPCVM",
            "AN_norm",
            "Frais_norm",
            "YTD_norm",
            "Semaine_norm",
            "Mois_norm",
            "Score"
        ]
    ]

    st.dataframe(
        heatmap_df,
        use_container_width=True
    )

    # ====================================
    # Export Excel
    # ====================================

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Classement",
            index=False
        )

        top10.to_excel(
            writer,
            sheet_name="Allocation",
            index=False
        )

    st.download_button(
        label="📥 Télécharger Excel",
        data=output.getvalue(),
        file_name="Classement_OPCVM.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
