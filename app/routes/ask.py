"""
Ask route.
Handles the /ask endpoint: receives a user's question, retrieves
the most relevant chunks from the vector store, sends them to the
LLM to generate a grounded natural-language answer, and returns
the answer along with source citations (page numbers).
"""

from flask import Blueprint, request, jsonify, session
from app.rag.retriever import retrieve_relevant_chunks
from app.rag.generator import generate_answer
from app.services.auth_service import login_required
from app.services.chat_service import save_message
from app.logger import get_logger

logger = get_logger(__name__)

ask_bp = Blueprint("ask", __name__)


@ask_bp.route("/ask", methods=["POST"])
@login_required
def ask_question():
    data = request.get_json(silent=True)

    if not data or "question" not in data:
        return jsonify({"error": "Request body must include a 'question' field."}), 400

    question = data["question"].strip()

    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400

    # The active document is set in the session when a PDF is uploaded
    # (see upload.py). Scoping retrieval to it prevents answers from
    # being pulled from unrelated documents uploaded earlier.
    active_document_id = session.get("active_document_id")

    if not active_document_id:
        return jsonify({
            "question": question,
            "answer": "Please upload a PDF before asking a question.",
            "sources": []
        }), 200

    # 1. Retrieve the most relevant chunks for this question, restricted
    #    to the currently active document
    try:
        chunks = retrieve_relevant_chunks(question, document_id=active_document_id)
    except Exception as e:
        logger.error(f"Failed to retrieve relevant chunks: {e}")
        return jsonify({"error": "Failed to search the document(s) for an answer."}), 500

    if not chunks:
        return jsonify({
            "question": question,
            "answer": "No documents have been uploaded yet, so there is nothing to search.",
            "sources": []
        }), 200

    # 2. Generate a grounded answer from the LLM using those chunks
    try:
        answer = generate_answer(question, chunks)
    except Exception as e:
        logger.error(f"Failed to generate an answer from the LLM: {e}")
        return jsonify({"error": "Failed to generate an answer."}), 500

    # 3. Build a simple, de-duplicated list of sources (document + page)
    #    for citation purposes.
    seen = set()
    sources = []
    for chunk in chunks:
        key = (chunk["document_name"], chunk["page_number"])
        if key not in seen:
            seen.add(key)
            sources.append({
                "document_name": chunk["document_name"],
                "page_number": chunk["page_number"]
            })

    # 4. Save this exchange to the chat history, so it can be restored
    #    later (e.g. after a page refresh). Saving failure should not
    #    break the response the user is waiting for.
    try:
        save_message(
            user_id=session["user_id"],
            document_id=active_document_id,
            document_name=session.get("active_document_name", ""),
            question=question,
            answer=answer,
            sources=sources
        )
    except Exception as e:
        logger.error(f"Failed to save chat message: {e}")

    return jsonify({
        "question": question,
        "answer": answer,
        "sources": sources
    }), 200