# llm-ontology-designer

## Main features
Starting from a domain-specific .txt file:

- Automatic extraction of:
  - **Classes**
  - **Object properties**
  - **Data properties**
- Generation of:
  - Structured **JSON ontology**
  - **Interactive HTML graph** representing ontological relations
- Explicit semantic constraints:
  - No classes or relations are invented
  - Only information explicitly present in the text is considered
  - ISA relations are expressed using `is_a`


## Project architecture

```text
.
├── data/
│   ├── input_text/         	# .txt files
│   ├── ontology/           	# .graphol file
│   └── validation_set/     	# .xlsx files
├── results/
│   ├── json/					# Ontology outputs (JSON)
│   ├── kg/						# Interactive HTML Knowledge Graphs
│   └── analysis/			# CSV with results analysis (Confusion Matrices)
└── WebApp_llm-ontology-designer.py 	# Streamlit application
└── README.md
```

## Requirements

Execute 'pip install -r requirements.txt' from terminal

### Main python libraries
- streamlit
- openai
- rdflib
- pyvis
- python-dotenv
- pandas

### Installation

1. Clone the repository:
```text
git clone <repository-url>
cd ontologIA
```
2. (Optional but recommended) Create a virtual environment and install dependencies:
```text 
pip install -r requirements.txt
```
3. Create a .env file in the project root:
OPENAI_API_KEY=your_api_key_here
4. Run the application:
From terminal:
```text
streamlit run WebApp_OntologIA.py
```
## WebApp
The interface guides the user step by step through:
- Selection of the process type (Direct / Inverse)
- Selection or upload of the input file
- Use or customization of the prompt
- Execution of the process
- Visualization and download of results

All files are saved with automatic versioning to prevent overwriting.

### Key design choices
State-driven pipeline to prevent inconsistent executions
Explicit and editable prompts for transparency in LLM usage
Clear separation between inputs, temporary files, and final results
Semantic visualization through interactive graphs
Controlled session state management

### Known limitations
JSON parsing assumes well-formed model output
No formal OWL/RDF validation is currently implemented
The project is intended for prototyping, research, and experimentation

### Possible future extensions
Automatic export to OWL / RDF
Ontology semantic validation
Multilingual support
Execution history tracking
Ontology comparison tools

This project was developed as an experimental tool for exploring and mediating between natural language and formal ontologies.