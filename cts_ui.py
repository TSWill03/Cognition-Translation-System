"""Cognition Translation System: text-only multilingual research demonstrator."""
from __future__ import annotations
import csv,io,json,time
from pathlib import Path
import streamlit as st
ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title="CTS | Cognition Translation System",page_icon="🌐",layout="wide")
st.title("Cognition Translation System")
st.caption("CTS Research Preview | Tradução de texto local e reproduzível")
st.warning("Protótipo de pesquisa, não é tradutor certificado. Reuniões e tradução de áudio ainda NÃO estão implementadas.")
tabs=st.tabs(["Tradutor de texto","Benchmark de 300 casos","Como funciona"])
with tabs[0]:
  try:
    import argostranslate.translate as trans
    installed={x.code:x for x in trans.get_installed_languages()}
  except Exception as e:
    installed={}
    st.error(f"Argos não disponível: {e}")
  available=[c for c in ["pt","es","fr","de","ja","zh","ar","eo","eu","ga","gl","ky","sw","ur","bn"] if c in installed]
  from benchmark300 import NAMES
  chosen=st.selectbox("Idioma de saída",available if available else ["pt"],format_func=lambda code:NAMES.get(code,code))
  source=st.text_area("Texto original em inglês",value="Selia Fastarrow met a traveler near Fallen Wall at sunrise.",height=130,max_chars=12000)
  if st.button("Traduzir localmente",type="primary",disabled=not available or not source.strip()):
    if "en" not in installed or chosen not in installed:st.error("Par de idiomas indisponível")
    else:
      try:
        engine=installed["en"].get_translation(installed[chosen])
        start=time.perf_counter()
        target=engine.translate(source)
        elapsed=(time.perf_counter()-start)*1000
        st.subheader("Resultado")
        st.text_area("Tradução",value=target,height=160)
        st.caption(f"{elapsed:.1f} ms de inferência, sem incluir instalação de modelo. Dados processados localmente.")
      except Exception as e:st.error(f"Falha de tradução: {type(e).__name__}: {e}")
with tabs[1]:
  path=ROOT/"results"
  if not (path/"manifest.json").exists():
    st.info("Os dados aparecem após executar benchmark300.py. Veja README.")
  else:
    manifest=json.loads((path/"manifest.json").read_text(encoding="utf-8"))
    cols=st.columns(3)
    cols[0].metric("Planejados",manifest.get("planned",0))
    cols[1].metric("Executados",manifest.get("observed",0))
    cols[2].metric("Sem erro de execução",manifest.get("success",0))
    if (path/"summary.json").exists():
      st.subheader("Resultados por idioma")
      st.dataframe(json.loads((path/"summary.json").read_text(encoding="utf-8")),use_container_width=True)
    if (path/"translations.csv").exists():
      raw=(path/"translations.csv").read_text(encoding="utf-8-sig")
      st.download_button("Baixar CSV original",raw,file_name="cts_translations.csv",mime="text/csv")
      with st.expander("Visualizar traduções individuais"):
        rows=list(csv.DictReader(io.StringIO(raw)))
        st.dataframe(rows[:300],use_container_width=True)
with tabs[2]:
  st.markdown("""
  **Estado atual:** laboratório de tradução texto→texto com Argos Translate e modelos instalados.
  O benchmark executa 20 entradas originais em inglês em 15 idiomas, registra resultado bruto,
  latência e erros reais. Não interpreta resultados automáticos como prova de fidelidade.
  
  **Próximas fases (não disponíveis):** glossário persistente por organização, revisão por falantes nativos,
  áudio bidirecional, aplicação de reuniões e integração opcional com Veredra.
  
  **Privacidade:** não há upload automático nem chamada de modelos online nesta interface.
  Os arquivos gerados pelo benchmark são locais até serem publicados manualmente.
  """)
