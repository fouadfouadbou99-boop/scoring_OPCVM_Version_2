import streamlit as st
import pandas as pd, numpy as np
from io import BytesIO
import plotly.express as px

st.set_page_config(page_title="OPCVM V3",layout="wide")

def norm(s):
 s=s.fillna(0)
 return pd.Series([1]*len(s),index=s.index) if s.max()==s.min() else (s-s.min())/(s.max()-s.min())

def alloc(scores,min_w=0.05,max_w=0.20):
 w=scores/scores.sum(); w=w.clip(min_w,max_w); return w/w.sum()

st.title("OPCVM Scoring Dashboard V3")
up=st.file_uploader('Excel',type=['xlsx'])
if up:
 df=pd.read_excel(up,sheet_name='Base_OPCVM')
 df=df.replace('-',np.nan)
 df['OPCVM']=df['OPCVM'].astype(str).str.strip().str.upper()
 dups=df['OPCVM'].duplicated().sum()
 df=df.drop_duplicates(subset=['OPCVM']).reset_index(drop=True)
 for c in ['AN','Frais de gestion','Perf_YTD','Perf_1_ semaine','Perf_1_ mois']:
  df[c]=pd.to_numeric(df[c],errors='coerce')
 df[['Perf_YTD','Perf_1_ semaine','Perf_1_ mois']]=df[['Perf_YTD','Perf_1_ semaine','Perf_1_ mois']].fillna(0)
 df=df.dropna(subset=['AN','Frais de gestion'])
 df['AN_norm']=norm(df['AN'])
 df['Frais_norm']=norm(df['Frais de gestion'].max()-df['Frais de gestion'])
 df['YTD_norm']=norm(df['Perf_YTD'])
 df['Sem_norm']=norm(df['Perf_1_ semaine'])
 score=.2*df['AN_norm']+.2*df['Frais_norm']+.35*df['YTD_norm']+.25*df['Sem_norm']
 df['Score']=score
 df=df.sort_values('Score',ascending=False).reset_index(drop=True)
 df['Rang']=df.index+1
 top=df.head(10).copy()
 top['Allocation']=alloc(top['Score'])*100
 st.sidebar.metric('Doublons supprimés',int(dups))
 st.dataframe(df[['Rang','OPCVM','SDG','Score']],hide_index=True)
 st.plotly_chart(px.bar(top,x='OPCVM',y='Score'),use_container_width=True)
 bio=BytesIO()
 with pd.ExcelWriter(bio,engine='xlsxwriter') as w: df.to_excel(w,index=False,sheet_name='Classement'); top.to_excel(w,index=False,sheet_name='Portefeuille')
 st.download_button('Exporter Excel',bio.getvalue(),'OPCVM_V3.xlsx')

