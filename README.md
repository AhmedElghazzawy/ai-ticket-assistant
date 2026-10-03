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

```sh
python src/hello_model.py
```

## Layout

```
data/knowledge_base/   documents the assistant answers from (RAG)
data/tickets/          sample support tickets
eval/                  evaluation scripts and results
src/                   application code
```
