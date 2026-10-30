# 📄 Chat with PDF — RAG Application

A full-stack Retrieval-Augmented Generation (RAG) application that lets users upload PDF documents and have natural-language conversations with them. Built from scratch as a learning project, covering the entire RAG pipeline — from text extraction to LLM-powered answer generation.

---

## 🎯 Overview

Upload any PDF, and ask questions about its content in plain English. The app retrieves the most relevant sections of the document and uses an LLM to generate accurate, source-cited answers — grounded strictly in the document's actual content, with built-in hallucination prevention.

---

## ✨ Features

### Core RAG Pipeline

- PDF text extraction (PyMuPDF)
- Custom text chunking with overlap
- Local embeddings (Sentence Transformers)
- Vector storage & semantic search (ChromaDB)
- LLM-powered answer generation (Groq)
- Source citations with page numbers

### User Features

- 🔐 Authentication (signup/login/logout, hashed passwords)
- 📚 Multiple document support, scoped per user
- 💬 Persistent chat history (survives logout/refresh)
- 🗂️ Sidebar conversation history (like ChatGPT/Claude)
- 🔍 Keyword search within documents
- 📝 Whole-document summarization
- ⚡ Quick actions: Explain, Key Points, Generate Questions
- 📋 Copy-to-clipboard for answers
- 🗑️ Delete documents (removes chunks, history, and file)
- 📱 Responsive design (mobile-friendly)

---

## 🏗️ Architecture

                 USER
                   │
                   ▼
             ┌───────────┐
             │  Flask    │
             │  Backend  │
             └─────┬─────┘
                   │
          ┌────────┴─────────┐
          ▼                  ▼
     PDF Upload          User Question
          │                  │
          ▼                  ▼
     PyMuPDF            Embedding Model
          │                  │
          ▼                  ▼
      Text Chunks       Vector Search
          │                  │
          ▼                  ▼
     Embeddings          Relevant Chunks
          │                  │
          ▼                  │
      ChromaDB ◄─────────────┘
                              │
                              ▼
                         ┌─────────┐
                         │   LLM   │
                         │ (Groq)  │
                         └────┬────┘
                              │
                              ▼
                    Answer + Citations
                              │
                              ▼
                         Frontend

## 🧰 Tech Stack

| Layer                | Technology                                 |
| -------------------- | ------------------------------------------ |
| Backend              | Python, Flask                              |
| PDF Processing       | PyMuPDF                                    |
| Embeddings           | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Vector Database      | ChromaDB                                   |
| LLM                  | Groq API (`openai/gpt-oss-20b`)            |
| Application Database | SQLite                                     |
| Frontend             | HTML, CSS, JavaScript (vanilla)            |
| Authentication       | Flask sessions + Werkzeug password hashing |

---

## 📁 Project Structure

```
chat-with-pdf-rag/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py             # Central configuration
│   ├── db.py                 # SQLite setup
│   ├── logger.py             # Logging setup
│   ├── rag/                  # Core RAG logic
│   │   ├── loader.py          # PDF text extraction
│   │   ├── splitter.py        # Text chunking
│   │   ├── embedder.py        # Embedding generation
│   │   ├── vectorstore.py     # ChromaDB operations
│   │   ├── retriever.py       # Semantic retrieval
│   │   └── generator.py       # LLM answer generation
│   ├── routes/                # API endpoints
│   ├── services/              # Business logic (auth, chat, files)
│   └── models/
├── static/                    # CSS & JavaScript
├── templates/                 # HTML pages
├── uploads/                   # Uploaded PDFs (gitignored)
├── vectorstore/                # ChromaDB data (gitignored)
├── database/                   # SQLite database (gitignored)
├── requirements.txt
├── .env.example
└── app.py
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- A free [Groq API key](https://console.groq.com)

### Installation

1. Clone the repository

```bash
git clone https://github.com/aminashujaat123-maker/chat-with-pdf-rag.git
cd chat-with-pdf-rag
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Set up environment variables

```bash
cp .env.example .env
```

Then edit `.env` and add your Groq API key and a random secret key:

```
LLM_API_KEY=your_groq_api_key_here
SECRET_KEY=any_random_string_here
```

4. Run the application

```bash
python app.py
```

5. Open your browser at `http://127.0.0.1:5000`

---

## 🗺️ Roadmap

- [x] **Phase 1 — MVP:** Core RAG pipeline, basic chat UI
- [x] **Phase 2 — Professional:** Auth, multi-document support, history, search, summaries, responsive UI
- [ ] **Phase 3 — Advanced:** Multi-document comparison, RAG analytics, hybrid search, streaming responses

---

## 📄 License

This project was built for learning purposes.

---

## 🙋 About

Built step-by-step as a hands-on learning project to understand the full RAG (Retrieval-Augmented Generation) architecture — from PDF parsing to LLM-grounded answer generation.
