import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import gc
import ast
from itertools import zip_longest
from rdflib import Graph
import streamlit as st
from pyvis.network import Network
import streamlit.components.v1 as components
# per lanciare streamlit:           python -m streamlit run WebApp_llm-ontology-designer.py
# per lanciare da terminale VSC:    streamlit run WebApp_llm-ontology-designer.py

import utils

# ======================
# CONFIG
# ======================

# INPUT_DIR = "data"
TEMP_INPUT_DIR = "temp_input"
RESULTS_DIR = "results"
JSON_DIR = os.path.join(RESULTS_DIR, "json")
GRAFI_DIR = os.path.join(RESULTS_DIR, "kg")
INPUT_TEXT_DIR = "data/input_text"

os.makedirs(TEMP_INPUT_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(GRAFI_DIR, exist_ok=True)
os.makedirs(INPUT_TEXT_DIR, exist_ok=True)

OPENAI_MODEL = "gpt-5-mini"

default_systemprompt = """Sei un assistente esperto di ontologie, modellazione semantica e tecnologie legate al web semantico 
(OWL, RDF, RDFS).
Il tuo compito è analizzare un testo di dominio ed estrarre una lista di classes, object properties e data properties nel linguaggio owl adottando le seguenti regole:
- Considera solo i concetti semanticamente rilevanti.
- Per ogni concetto riporta la sua descrizione in linguaggio naturale solo se presente nel testo.
- Evidenzia le relazioni di ISA tra i concetti.
- Non inventare nè classi nè descrizioni se non sono presenti nel testo.
- Non includere suggerimenti aggiuntivi, opzioni alternative, esempi o frasi condizionali. Produci solo la descrizione discorsiva dell'ontologia in italiano, come se fosse un documento ufficiale. Non aggiungere nulla che non sia richiesto esplicitamente."""

default_instruction = """Analizza il seguente testo di dominio"""

fixed_system_prompt = """
Restituisci l’output esclusivamente in formato JSON in conformità alle regole fornite nel system prompt.
Esempio di output atteso:
{
    "classes": [
        {
            "name": "Persona",
            "description": "Essere umano"
        },
		{
            "name": "Citta",
            "description": "Luogo"
        }
    ],
    "object_properties": [
        {
            "label": "Vive_in",
            "domain": "Persona",
            "range": "Citta"
        }
    ],
    "data_properties": [
        {
            "label": "Nome_città",
            "domain": "Citta",
            "range": "string (alfanumerico, 15 caratteri)"
        }
    ]
}
Nel caso di eventuali sottoclassi, includile nella lista delle classi con la loro relazione ISA specificata tramite una object property denominata `is_a`.
"""

SYSTEM_PROMPT = default_systemprompt + fixed_system_prompt

USER_INSTRUCTIONS = default_instruction

# ======================
# SESSION STATE INIT
# ======================

def init_state():
    defaults = {
        "step": 0,
        "file_input": None,
        "file_name": None,
        "prompt": None,
        "risultati": None,
        "run_dir": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ======================
# STEP 1 — SCELTA FILE
# ======================

def step_scelta_file(estensione):
    st.header(f"1 Selezione file .{estensione}")

    sorgente = st.radio(
        "Origine file",
        ["Da locale", "Da cartella input"]
    )
    file = None
    INPUT_DIR = INPUT_TEXT_DIR
    if sorgente == "Da locale":
        file = st.file_uploader( f"Carica file .{estensione}",type=[estensione])
        if file:
            st.session_state.file_name = file.name
    else:
        files = [f for f in os.listdir(INPUT_DIR) if f.endswith(f".{estensione}")]
        if files:
            nome = st.selectbox("Seleziona file", files)
            if nome:
                file = os.path.join(INPUT_DIR, nome)
                st.session_state.file_name = nome
        else:
            st.warning("Nessun file disponibile nella cartella input")
    if st.button("Carica file"):
        if file:
            path = utils.salva_file_input(file, path=TEMP_INPUT_DIR)
            st.session_state.file_input = path
            st.session_state.step = 1
            st.rerun()
        else:
            st.warning("Seleziona un file prima di cliccare Carica")

# ======================
# STEP 2 — PROMPT
# ======================

def step_prompt():
    st.header("2 Prompt")
    default_prompt = SYSTEM_PROMPT
    default_instruction = USER_INSTRUCTIONS
    scelta = st.radio("Configurazione prompt", ["Usa prompt predefinito", "Modifica prompt"])
    if scelta == "Modifica prompt":
        prompt = st.text_area("Prompt", value=default_prompt, height=300)
        user_instruction = st.text_area("User Instruction", value=default_prompt, height=300)
    else:
        prompt = default_prompt
        user_instruction = default_instruction
        st.code(prompt)

    if st.button("Conferma prompt"):
        st.session_state.prompt = prompt
        st.session_state.user_instruction = user_instruction
        st.session_state.step = 2
        st.rerun()


# ======================
# STEP 3 — ESECUZIONE
# ======================

def step_esecuzione():
    st.header("3 Esecuzione processo")
    st.info(f"File: **{st.session_state.file_name}**")

    if st.button("Avvia processo"):
        with st.spinner("Elaborazione in corso..."):
            risultati = run_pipeline()
        st.session_state.risultati = risultati
        # st.session_state.run_dir = salva_results(risultati)
        # log_excel()
        st.session_state.step = 3
        st.rerun()

# ======================
# STEP 4 — DOWNLOAD
# ======================

def step_download():
    st.header("4 Risultati")
    risultati = st.session_state.risultati

    if risultati.get("json_file"):
        st.success(f"JSON salvato: {risultati['json_file']}")
        json_path = os.path.join(JSON_DIR, risultati["json_file"])
        st.download_button("Scarica JSON", data=open(json_path,"r",encoding="utf-8").read(), file_name=os.path.basename(json_path))

    if risultati.get("html_path"):
        html_path = risultati["html_path"]
        with open(html_path, "r", encoding="utf-8") as f:
            source_code = f.read()
        st.subheader("Anteprima grafo")
        components.html(source_code, height=1200, width=1000)
        st.success(f"HTML salvato: {risultati['html_path']}")
        st.download_button("Scarica HTML grafo", data=source_code, file_name=os.path.basename(html_path))



# ======================
# PIPELINE 
# ======================

def run_pipeline():
    path = st.session_state.file_input
    prompt = st.session_state.prompt
    user_instruction = st.session_state.user_instruction
    title = os.path.splitext(st.session_state.file_name)[0]
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    # print("API key caricata:", api_key is not None)
    client = OpenAI(api_key=api_key)
    # LETTURA FILE
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
     
    resp = client.responses.create(
        model=OPENAI_MODEL,
        instructions= prompt,
        input=user_instruction + "/n" + text + "/n")
    
    raw_output = resp.output_text

    json_out = json.loads(raw_output)
    json_file = utils.save_json(json_out, title, path=JSON_DIR)
    html_path = utils.save_html_grafo(json_out, title, path=GRAFI_DIR)
    return {"json_file": json_file, "html_path": html_path}


# ======================
# MAIN
# ======================

def main():
    init_state()
    
    if st.session_state.step == 0:
        est = "txt"
        step_scelta_file(est)

    elif st.session_state.step == 1:
        step_prompt()

    elif st.session_state.step == 2:
        step_esecuzione()

    elif st.session_state.step == 3:
        step_download()


if __name__ == "__main__":
    main()