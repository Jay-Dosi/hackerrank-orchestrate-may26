# HackerRank Orchestrate 2026: Multi-Domain Support Triage Agent

This directory contains the source code for a highly resilient, terminal-based AI support triage agent. The agent is designed to autonomously handle support tickets across three distinct product ecosystems: **HackerRank**, **Claude**, and **Visa**.

## 🎯 Objective & Philosophy

The primary objective of this project is to create an agent that is not just smart, but **safe**. Generative AI in customer support often suffers from "hallucinations" (e.g., advising a Visa customer to check their HackerRank dashboard). 

To solve this, our agent employs a **Strict Domain Isolation Architecture**. It physically partitions knowledge contexts and uses a Gatekeeper node to intercept out-of-scope or high-risk queries *before* they ever reach the generation phase.

---

## 🏗️ System Architecture

Our solution is built using LangChain and orchestrated via a structured pipeline.

### 1. Ingestion & Local Vectorization (`ingest.py`)
To prevent API rate-limit exhaustion during data ingestion, this pipeline completely bypasses cloud embedding APIs.
- **Data Parsing:** Reads raw Markdown files from the `data/` directory.
- **Chunking:** Uses `RecursiveCharacterTextSplitter` to break documents into manageable context windows.
- **Metadata Tagging:** *Crucially*, it tags every single chunk with its source domain (`hackerrank`, `claude`, or `visa`). 
- **Local Embeddings:** Utilizes the lightweight, open-source HuggingFace model `all-MiniLM-L6-v2` to embed tens of thousands of chunks entirely on the CPU.
- **Storage:** Persists the vectors locally using `ChromaDB`.

### 2. The Triage Agent (`agent.py`)
The core logic evaluates tickets through a 4-node decision graph:

*   **Node 1: Router Classification**
    - Uses an LLM to parse the raw ticket text and return a strict JSON payload.
    - Extracts: `domain`, `request_type`, `product_area`, `risk_score`, and a concise `justification`.
*   **Node 2: Gatekeeper Check**
    - Evaluates the output of Node 1.
    - If the `domain` is unrecognizable ("unknown") or the `risk_score` is "High" (e.g., fraud, stolen cards, abusive language, malicious system commands), the Gatekeeper **aborts the process and immediately ESCALATES** the ticket to a human.
*   **Node 3: Isolated Retrieval**
    - If the ticket passes the Gatekeeper, the agent queries ChromaDB.
    - **Security Feature:** It applies a strict `filter={"domain": identified_domain}` to the vector search. This makes it mathematically impossible for the agent to retrieve Claude policies while answering a Visa ticket.
*   **Node 4: Grounded Generation**
    - The LLM is fed the user ticket alongside the domain-isolated context snippets.
    - It operates under a strict prompt directive: if the context does not contain the exact answer, output "ESCALATE". Otherwise, generate a polite, factual resolution (`REPLY`).

### 3. Orchestration & Resiliency (`main.py`)
The orchestrator drives the evaluation while navigating strict API quotas:
- Iterates over `support_tickets.csv`.
- Maps inputs and formats the output dictionary to strictly align with the Hackathon's requested schema (`issue, subject, company, response, product_area, status, request_type, justification`).
- **Resiliency:** Wraps the agent calls in a `tenacity` exponential backoff loop to catch transient API failures.
- **Pacing:** Enforces an artificial `time.sleep(4)` between tickets to respect strict "Requests Per Minute" limits on free-tier LLM endpoints.
- Auto-compiles the final `output.csv` and packages the submission zip via `utils.py`.

---

## 💻 Technology Stack

* **Language:** Python 3.11+
* **LLM API (Generation):** Groq API. 
  - *Pivot Rationale:* Initially attempted with Gemini API, but strict free-tier quotas (0-20 requests/day for advanced models) proved insufficient for processing large ticket batches. We pivoted to Groq and the `openai/gpt-oss-120b` model for ultra-fast, high-allowance inference.
* **Embeddings:** HuggingFace `all-MiniLM-L6-v2` (Local inference)
* **Vector Database:** ChromaDB
* **Frameworks:** LangChain, Pandas, Tenacity

---

## 🚀 Setup & Execution

### 1. Environment Variables
Create a `.env` file in the root directory and add your Groq API Key:
```env
GROQ_API_KEY=gsk_your_actual_api_key_here
```

### 2. Install Dependencies
Initialize your virtual environment and install the required packages:
```bash
pip install -r code/requirements.txt
```

### 3. Run the Pipeline

**Step 1: Build the Knowledge Base**
```bash
python code/ingest.py
```
*Note: This will download the HuggingFace model weights locally. The warning about unauthenticated HuggingFace requests is expected and safe to ignore.*

**Step 2: Process the Support Tickets**
```bash
python code/main.py
```
This will process the tickets, generate `support_tickets/output.csv`, and automatically bundle this code directory into the required `submission.zip` artifact for grading.
