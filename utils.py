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
import numpy as np
# from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment

# ======================
# FILE HANDLING
# ======================
def salva_file_input(file, path):
    """
    Ritorna SEMPRE un path su disco
    """
    # caso upload locale (UploadedFile)
    if hasattr(file, "read"):
        path = os.path.join(path, file.name)
        with open(path, "wb") as f:
            f.write(file.read())
        return path
    # caso file già su disco
    return file

# ======================
# PIPELINE - FUNZIONI NECESSARIE
# ======================

def leggi_ttl(path_ttl):
    text = ""
    g = Graph()
    g.parse(path_ttl, format="turtle")
    for s, p, o in g:
        text += f"{s} | {p} | {o}\n"
    return text

# def genera_html_grafo(json_data, file_name):
#     grafo = GenerazioneGrafo(json_data)
#     grafi_dir = os.path.join(RESULTS_DIR, "grafi")
#     os.makedirs(grafi_dir, exist_ok=True)
#     path_html = os.path.join(grafi_dir, f"Grafo_{file_name}.html")
#     grafo.write_html(path_html)
#     return path_html


def GenerazioneGrafo(data):
  net = Network(height="750px", width="100%", directed=True)
  # FASE 1 → spargimento con fisica
  net.set_options("""
  {
    "physics": {
      "enabled": true,
      "solver": "forceAtlas2Based",
      "forceAtlas2Based": {
        "gravitationalConstant": -120,
        "centralGravity": 0.01,
        "springLength": 180,
        "springConstant": 0.08
      },
      "stabilization": { "enabled": true, "iterations": 400 }
    },
    "nodes": {
      "margin": 10,
      "font": { "size": 16 }
    },
    "interaction": { "dragNodes": true }
  }
  """)
  class_names = [item.get("name") for item in data['classes'] if "name" in item]
  # ---------- NODI CLASSI (rettangoli) ----------
  for cls in data['classes']:
      if "description" in cls and cls["description"]:
        titolo = f"Class: {cls['name']}\n description: {cls['description']}"
      else:
        titolo = f"Class: {cls['name']}"
      net.add_node(
          cls['name'],
          label=cls['name'],
          shape="box",
          title=titolo,
          physics=True
      )
  # ----- Object Property --------
  # Aggiungi archi
  for obj in data['object_properties']:
      if obj["domain"] in class_names and obj["range"] in class_names:
          net.add_edge(obj["domain"], obj["range"], label=obj["label"])
      else:
          print(f"Attenzione: '{obj['range']}' o '{obj['domain']}' non è definito, salto l'arco.")
  # ---------- DATA PROPERTY ----------
  for dp in data['data_properties']:
      if dp['domain'] in class_names:
          net.add_node(
              dp['label'],
              label = dp['label'],
              shape = 'dot',
              color = 'orange',
              title = f"Data Property: {dp['label']}; range: {dp['range']}",
              physics = True
          )
          net.add_edge(dp['domain'], dp['label'], label = 'DataProp', color = 'orange')
  # FASE 2 → congelamento del grafo (nodi indipendenti)
  net.html = net.html.replace(
      "physics:{enabled:true",
      "physics:{enabled:false"
  )
  return net

def save_json(data, title, path, prefix=f"estrazione_"):
    os.makedirs(path, exist_ok=True)
    # Recupera tutti i file nella cartella che iniziano con il prefisso
    existing = [
        f for f in os.listdir(path)
        if f.startswith(prefix) and f.endswith(".json")
    ]
    #st.write("Existing files:", existing)
    # Se non ci sono file, partiamo da 0
    if not existing:
        next_index = 0
    else:
        # Estrarre la parte numerica da ogni file
        numbers = []
        for fname in existing:
            if title in fname:
                # es: output_003.json → "003"
                num_str = fname[len(prefix)+len(title)+1:-5]
                #st.write(f"Extracted number string from {fname}: {num_str}")
                if num_str.isdigit():
                    numbers.append(int(num_str))
        next_index = max(numbers) + 1 if numbers else 0
    # Formattazione con zeri: 3 cifre (000, 001, 002, ...)
    filename = f"{title}_{next_index:03d}"
    filepath = os.path.join(path, f"{prefix}{filename}.json")
    ########################################
    # filename = f"{prefix}{title}_{next_index:03d}.json"
    # filepath = os.path.join(path, filename)
    ##################################################
    # Salvataggio del file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return filename

def save_html_grafo(json_data, filename_title, path, prefix=f"Grafo_"):
    os.makedirs(path, exist_ok=True)
    grafo = GenerazioneGrafo(json_data)
    # Recupera tutti i file nella cartella che iniziano con il prefisso
    existing = [
        f for f in os.listdir(path)
        if f.startswith(prefix) and f.endswith(".html")
    ]
    nome_file_grafo = f"{prefix}{filename_title}.html"
    path_html = os.path.join(path, nome_file_grafo)
    grafo.write_html(path_html)
    return nome_file_grafo



def save_txt(testo_da_salvare, titolo_del_testo, path, prefix=f"DescrizioneOntologia_"):
    os.makedirs(path, exist_ok=True)
    # Recupera tutti i file nella cartella che iniziano con il prefisso
    existing = [
        f for f in os.listdir(path)
        if f.startswith(prefix) and f.endswith(".txt")
    ]
    #st.write("Existing files:", existing)
    # Se non ci sono file, partiamo da 0
    if not existing:
        next_index = 0
    else:
        # Estrarre la parte numerica da ogni file
        numbers = []
        for fname in existing:
            if titolo_del_testo in fname:
                # es: DescrizioneOntologia_Demanio_v05_000.txt → "000"
                num_str = fname[len(prefix)+len(titolo_del_testo)+1:-4]
                #st.write(f"Extracted number string from {fname}: {num_str}")
                if num_str.isdigit():
                    numbers.append(int(num_str))
        next_index = max(numbers) + 1 if numbers else 0
    # Formattazione con zeri: 3 cifre (000, 001, 002, ...)
    filename = f"{prefix}{titolo_del_testo}_{next_index:03d}.txt"
    filepath = os.path.join(path, filename)
    # Salvataggio del file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(testo_da_salvare)
    return filepath

# ============================================================================
#   ANALYSIS FUNCTION
# =============================================================================
# from sentence_transformers import SentenceTransformer
# model = SentenceTransformer('all-MiniLM-L6-v2')
# def compute_embeddings(labels):
#     return model.encode(labels, normalize_embeddings=True)



# ==========================================================================
# FUNZIONI PER ANALISI BASE CON MATRICE DI SIMILARITÀ (Coseno)
# ==========================================================================

def analyze_predictions(y_true, y_pred, threshold=0.7):
    emb_true = compute_embeddings(y_true)
    emb_pred = compute_embeddings(y_pred)

    sim_matrix = cosine_similarity(emb_true, emb_pred)

    used_pred = set()

    tp = []
    fn = []
    
    for i, true_label in enumerate(y_true):
        j = np.argmax(sim_matrix[i])
        score = sim_matrix[i, j]

        if score >= threshold and j not in used_pred:
            tp.append({
                "true": true_label,
                "pred": y_pred[j],
                "similarity": float(score)
            })
            used_pred.add(j)
        else:
            fn.append({
                "true": true_label,
                "best_pred": y_pred[j],
                "similarity": float(score)
            })

    fp = []
    for j, pred_label in enumerate(y_pred):
        if j not in used_pred:
            fp.append(pred_label)

    return {
        "TP": tp,
        "FN": fn,
        "FP": fp
    }


# =========================================================================
# FUNZIONI PER ANALISI con assegnamento OTTIMO (Hungarian) - per evitare problemi di "doppioni" e "best match" che non sono reali
# =========================================================================

def analyze_predictions_hungarian(y_true, y_pred, threshold=0.7):
    emb_true = compute_embeddings(y_true)
    emb_pred = compute_embeddings(y_pred)

    sim_matrix = cosine_similarity(emb_true, emb_pred)

    # Hungarian vuole una matrice di costo
    cost_matrix = 1 - sim_matrix

    # matching ottimo globale
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    tp = []
    fn = []
    matched_pred = set()

    for i, j in zip(row_ind, col_ind):
        score = sim_matrix[i, j]

        if score >= threshold:
            tp.append({
                "true": y_true[i],
                "pred": y_pred[j],
                "similarity": float(score)
            })
            matched_pred.add(j)
        else:
            fn.append({
                "true": y_true[i],
                "best_pred": y_pred[j],
                "similarity": float(score)
            })

    # y_true non assegnati (caso len(y_true) > len(y_pred))
    assigned_true = set(row_ind)
    for i in range(len(y_true)):
        if i not in assigned_true:
            fn.append({
                "true": y_true[i],
                "best_pred": None,
                "similarity": None
            })

    # FP = pred non usati
    fp = []
    for j, pred_label in enumerate(y_pred):
        if j not in matched_pred:
            fp.append(pred_label)

    return {
        "TP": tp,
        "FN": fn,
        "FP": fp,
        "similarity_matrix": sim_matrix
    }


def compute_metrics(results):
    TP = len(results["TP"])
    FN = len(results["FN"])
    FP = len(results["FP"])

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

