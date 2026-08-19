import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="OPCVM Scoring Dashboard",layout="wide")

def normalize(s):
    if s.max()==s.min():
        return pd.Series([1.0]*len(s),index=s.index)
    return (s-s.min())/(s.max()-s.min())

def constrained_weights(scores,min_w=0.05,max_w=0.20):
    w=scores/scores.sum()
    w=w.clip(lower=min_w,upper=max_w)
    for _ in range(200):
        diff=1-w.sum()
        if abs(diff)<1e-9: break
        free=(w>min_w)&(w<max_w)
        if free.sum()==0: break
        w.loc[free]+=diff/free.sum()
        w=w.clip(lower=min_w,upper=max_w)
    return w/w.sum()

st.title('OPCVM Scoring Dashboard')
file=st.file_uploader('Fichier Excel',type='xlsx')
if file:
    df=pd.read_excel(file,sheet_name='Base_OPCVM')
    p=pd.read_excel(file,sheet_name='Parametres')
    d={r['Critere']:float(r['Poids']) for _,r in p.iterrows()}
    pa=d.get('AN',0.2);pf=d.get('Frais de gestion',0.2);py=d.get('Perf_YTD',0.35);ps=d.get('Perf_1_ semaine',0.25);pm=d.get('Perf_1_ mois',0)
    s=df.copy()
    s['AN_norm']=normalize(s['AN'])
    s['Frais_norm']=normalize(s['Frais de gestion'].max()-s['Frais de gestion'])
    s['YTD_norm']=normalize(s['Perf_YTD'])
    s['Semaine_norm']=normalize(s['Perf_1_ semaine'])
    s['Mois_norm']=normalize(s['Perf_1_ mois'])
    total=pa+pf+py+ps+pm
    s['Score']=(s['AN_norm']*pa+s['Frais_norm']*pf+s['YTD_norm']*py+s['Semaine_norm']*ps+s['Mois_norm']*pm)/total
    s=s.sort_values('Score',ascending=False).reset_index(drop=True)
    s['Rang']=s.index+1
    s['Allocation_%']=(constrained_weights(s['Score'])*100).round(2)
    invest=st.sidebar.number_input('Montant à investir (MAD)',1000000,1000000000,10000000,1000000)
    s['Montant_Cible_MAD']=(invest*s['Allocation_%']/100).round(0)
    st.subheader('Top 10')
    st.dataframe(s[['Rang','OPCVM','Score','Allocation_%']].head(10),use_container_width=True)
    st.plotly_chart(px.bar(s.head(10),x='OPCVM',y='Score',color='Score'),use_container_width=True)
    sel=st.multiselect('Radar',s['OPCVM'].tolist(),default=s.head(3)['OPCVM'].tolist())
    if sel:
      fig=go.Figure()
      labs=['AN','Frais','YTD','Semaine','Mois']
      for _,r in s[s.OPCVM.isin(sel)].iterrows():
        vals=[r['AN_norm'],r['Frais_norm'],r['YTD_norm'],r['Semaine_norm'],r['Mois_norm']]
        fig.add_trace(go.Scatterpolar(r=vals+[vals[0]],theta=labs+[labs[0]],fill='toself',name=r['OPCVM']))
      st.plotly_chart(fig,use_container_width=True)
    heat=s.head(20).set_index('OPCVM')[['AN_norm','Frais_norm','YTD_norm','Semaine_norm','Mois_norm','Score']]
    st.plotly_chart(px.imshow(heat,text_auto='.2f',color_continuous_scale='RdYlGn'),use_container_width=True)
    st.subheader('Portefeuille cible')
    st.dataframe(s[['Rang','OPCVM','Allocation_%','Montant_Cible_MAD']],use_container_width=True)
    bio=BytesIO()
    with pd.ExcelWriter(bio,engine='xlsxwriter') as w: s.to_excel(w,index=False)
    st.download_button('Exporter Excel',bio.getvalue(),'Classement_OPCVM.xlsx')
