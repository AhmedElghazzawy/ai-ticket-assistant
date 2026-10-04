# ai-ticket-assistant
AI support ticket assistant: classification, RAG, and escalation

## Setup

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env   # then put your Gemini API key in .env
```

Get a key at https://aistudio.google.com/apikey.

## Run

Open the web UI (classify tickets, browse the dataset, run the evaluation):

```sh
streamlit run src/app.py
```

Or run the pieces from the terminal:

```sh
python src/tickets.py      # check the dataset and show statistics
python src/classifier.py   # classify every labeled ticket and show mismatches
```

## Layout

```
data/knowledge_base/   documents the assistant answers from (RAG)
data/tickets/          sample support tickets
eval/                  evaluation scripts and results
src/                   application code
```
