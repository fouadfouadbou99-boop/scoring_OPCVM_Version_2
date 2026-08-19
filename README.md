# OPCVM Scoring Dashboard

Application Streamlit de sélection et d'allocation des OPCVM.

## Source de données

Le calcul utilise uniquement la feuille :

```text
Base_OPCVM
```

Colonnes obligatoires :

```text
OPCVM
SDG
AN
Frais de gestion
Perf_YTD
Perf_1_ semaine
Perf_1_ mois
```

## Fonctionnalités

- Scoring multicritères
- Classement automatique
- Top 10 / Top 15 / Top 20
- Allocation sous contraintes
- Allocation minimum 5 %
- Allocation maximum 20 %
- Simulation d'investissement
- Radar
- Heatmap
- Export Excel

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

## Déploiement

Compatible :

```text
GitHub
+
Streamlit Cloud
```
