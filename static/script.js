// Chat with PDF — front-end logic.

const pdfInput = document.getElementById("pdf-input");
const uploadLabel = document.getElementById("upload-label");
const uploadLabelText = document.getElementById("upload-label-text");
const uploadStatus = document.getElementById("upload-status");
const documentInfo = document.getElementById("document-info");
const docNameEl = document.getElementById("doc-name");
const docMetaEl = document.getElementById("doc-meta");
const historyListEl = document.getElementById("history-list");
const searchInput = document.getElementById("search-input");
const searchResultsEl = document.getElementById("search-results");
const summarizeButton = document.getElementById("summarize-button");
const quickActionButtons = document.querySelectorAll(".quick-action-btn");

const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const questionInput = document.getElementById("question-input");
const sendButton = document.getElementById("send-button");

const logoutButton = document.getElementById("logout-button");

let hasUploadedDocument = false;

// ---------------- Network-aware fetch wrapper ----------------
// Wraps the native fetch() so every API call in this file gets:
//   1. A friendly message instead of a raw browser error when the
//      network is down or the server can't be reached.
//   2. Automatic redirect to the login page if the session has
//      expired (401), instead of showing a confusing error in place.

async function apiFetch(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (networkError) {
    throw new Error(
      "Can't reach the server. Please check your connection and try again.",
    );
  }

  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Session expired.");
  }

  return response;
}

// ---------------- Summarize whole document ----------------

summarizeButton.addEventListener("click", async () => {
  if (!hasUploadedDocument) return;

  addUserMessage("Summarize this document");
  setInputEnabled(false);
  summarizeButton.disabled = true;

  const typingBubble = addTypingIndicator();

  try {
    const response = await apiFetch("/summarize", { method: "POST" });
    const data = await response.json();
    typingBubble.remove();

    if (!response.ok) {
      throw new Error(data.error || "Failed to generate a summary.");
    }

    addAssistantMessage(data.answer, data.sources);
    loadDocumentList();
  } catch (error) {
    typingBubble.remove();
    addAssistantMessage(error.message, [], true);
  }

  setInputEnabled(true);
  summarizeButton.disabled = false;
});

// ---------------- Quick actions (Explain, Key Points, Questions) ----------------

quickActionButtons.forEach((btn) => {
  btn.addEventListener("click", () => runQuickAction(btn.dataset.action, btn));
});

async function runQuickAction(action, buttonEl) {
  if (!hasUploadedDocument) return;

  quickActionButtons.forEach((b) => (b.disabled = true));
  summarizeButton.disabled = true;
  setInputEnabled(false);

  const typingBubble = addTypingIndicator();

  try {
    const response = await apiFetch("/quick-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });

    const data = await response.json();
    typingBubble.remove();

    if (!response.ok) {
      throw new Error(data.error || "Failed to generate a response.");
    }

    addUserMessage(data.question);
    addAssistantMessage(data.answer, data.sources);
    loadDocumentList();
  } catch (error) {
    typingBubble.remove();
    addAssistantMessage(error.message, [], true);
  }

  quickActionButtons.forEach((b) => (b.disabled = false));
  summarizeButton.disabled = false;
  setInputEnabled(true);
}

// ---------------- Search within document ----------------

let searchDebounceTimer = null;
let searchRequestId = 0; // guards against a slow, older request overwriting newer results

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounceTimer);
  const query = searchInput.value.trim();

  if (!query) {
    searchResultsEl.innerHTML = "";
    return;
  }

  searchDebounceTimer = setTimeout(() => runSearch(query), 300);
});

async function runSearch(query) {
  const thisRequestId = ++searchRequestId;
  searchResultsEl.innerHTML = `<div class="search-empty">Searching...</div>`;

  try {
    const response = await apiFetch(`/search?q=${encodeURIComponent(query)}`);
    const data = await response.json();

    // A newer search has started since this one was sent — discard
    // this (now stale) result so it doesn't flash over the latest.
    if (thisRequestId !== searchRequestId) return;

    if (!response.ok) {
      searchResultsEl.innerHTML = `<div class="search-empty">${escapeHtml(data.error || "Search failed.")}</div>`;
      return;
    }

    renderSearchResults(data.results, query, data.message);
  } catch (error) {
    if (thisRequestId !== searchRequestId) return;
    searchResultsEl.innerHTML = `<div class="search-empty">${escapeHtml(error.message)}</div>`;
  }
}

function renderSearchResults(results, query, message) {
  searchResultsEl.innerHTML = "";

  if (message) {
    searchResultsEl.innerHTML = `<div class="search-empty">${escapeHtml(message)}</div>`;
    return;
  }

  if (!results || results.length === 0) {
    searchResultsEl.innerHTML = `<div class="search-empty">No matches found.</div>`;
    return;
  }

  results.forEach((result) => {
    const item = document.createElement("div");
    item.className = "search-result-item";
    item.innerHTML = `
            <div class="search-result-page">Page ${result.page_number}</div>
            <div>${highlightMatch(result.text, query)}</div>
        `;
    searchResultsEl.appendChild(item);
  });
}

function highlightMatch(text, query) {
  const escapedText = escapeHtml(text);
  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`(${escapedQuery})`, "gi");
  return escapedText.replace(regex, "<mark>$1</mark>");
}

// ---------------- Sidebar document/chat history list ----------------

async function loadDocumentList() {
  try {
    const response = await apiFetch("/documents");
    const data = await response.json();

    if (!response.ok) return;

    renderDocumentList(data.documents, data.active_document_id);
  } catch (error) {
    console.error("Could not load document list:", error.message);
  }
}

function renderDocumentList(documents, activeDocumentId) {
  historyListEl.innerHTML = "";

  documents.forEach((doc) => {
    const item = document.createElement("div");
    item.className =
      "history-item" + (doc.document_id === activeDocumentId ? " active" : "");
    item.title = doc.document_name;

    const label = document.createElement("span");
    label.className = "history-item-label";
    label.textContent = doc.document_name;
    label.addEventListener("click", () => switchDocument(doc.document_id));

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "history-delete-btn";
    deleteBtn.type = "button";
    deleteBtn.textContent = "×";
    deleteBtn.title = "Delete this document";
    deleteBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteDocument(doc.document_id, doc.document_name, item);
    });

    item.appendChild(label);
    item.appendChild(deleteBtn);
    historyListEl.appendChild(item);
  });
}

async function switchDocument(documentId) {
  try {
    const response = await apiFetch("/documents/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: documentId }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not switch document.");
    }

    chatWindow.innerHTML = "";
    searchInput.value = "";
    searchResultsEl.innerHTML = "";
    hasUploadedDocument = true;
    questionInput.disabled = false;
    sendButton.disabled = false;

    docNameEl.textContent = data.document_name;
    docMetaEl.textContent = "Previous conversation";
    documentInfo.classList.remove("hidden");

    await loadChatHistory();
    await loadDocumentList();
  } catch (error) {
    alert(error.message);
  }
}

async function deleteDocument(documentId, documentName, itemEl) {
  const confirmed = confirm(
    `Delete "${documentName}"? This will remove its chat history and cannot be undone.`,
  );
  if (!confirmed) return;

  // Visual feedback while the delete request is in flight
  itemEl.style.opacity = "0.5";
  itemEl.style.pointerEvents = "none";

  try {
    const response = await apiFetch(
      `/documents/${encodeURIComponent(documentId)}`,
      {
        method: "DELETE",
      },
    );
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Failed to delete document.");
    }

    await loadDocumentList();

    const historyResp = await apiFetch("/history");
    const historyData = await historyResp.json();
    if (!historyData.document_id) {
      resetChatUI();
    }
  } catch (error) {
    itemEl.style.opacity = "1";
    itemEl.style.pointerEvents = "auto";
    alert(error.message);
  }
}

function resetChatUI() {
  chatWindow.innerHTML = `<div class="welcome-message">Upload a PDF to start asking questions about it.</div>`;
  hasUploadedDocument = false;
  questionInput.disabled = true;
  sendButton.disabled = true;
  documentInfo.classList.add("hidden");
  searchInput.value = "";
  searchResultsEl.innerHTML = "";
  uploadStatus.textContent = "";
}

// ---------------- Chat history restoration ----------------

async function loadChatHistory() {
  try {
    const response = await apiFetch("/history");
    const data = await response.json();

    if (!response.ok || !data.messages || data.messages.length === 0) return;

    clearWelcomeMessage();
    hasUploadedDocument = true;
    questionInput.disabled = false;
    sendButton.disabled = false;

    docNameEl.textContent = data.document_name;
    docMetaEl.textContent = "Restored from previous session";
    documentInfo.classList.remove("hidden");
    uploadStatus.textContent = `Continuing chat with ${data.document_name}`;

    data.messages.forEach((msg) => {
      addUserMessage(msg.question);
      addAssistantMessage(msg.answer, msg.sources);
    });
  } catch (error) {
    console.error("Could not load chat history:", error.message);
  }
}

loadChatHistory();
loadDocumentList();

// ---------------- Logout handling ----------------

logoutButton.addEventListener("click", async () => {
  try {
    await fetch("/api/logout", { method: "POST" });
  } finally {
    window.location.href = "/login";
  }
});

// ---------------- Upload handling ----------------

pdfInput.addEventListener("change", async () => {
  const file = pdfInput.files[0];
  if (!file) return;
  await uploadPdf(file);
});

async function uploadPdf(file) {
  uploadLabel.classList.add("uploading");
  uploadLabelText.textContent = "Uploading and processing...";
  uploadStatus.textContent = "";
  uploadStatus.classList.remove("error");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await apiFetch("/upload", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) throw new Error(data.error || "Upload failed.");

    onUploadSuccess(data);
  } catch (error) {
    onUploadError(error.message);
  }
}

function onUploadSuccess(data) {
  uploadLabel.classList.remove("uploading");
  uploadLabelText.textContent = "Click to upload a different PDF";
  uploadStatus.textContent = `Ready — ${data.pages_count} pages, ${data.chunks_count} chunks indexed.`;

  docNameEl.textContent = data.file.original_filename;
  docMetaEl.textContent = `${data.pages_count} pages · ${data.file.size_mb} MB`;
  documentInfo.classList.remove("hidden");

  hasUploadedDocument = true;
  questionInput.disabled = false;
  sendButton.disabled = false;
  questionInput.focus();

  chatWindow.innerHTML = "";
  searchInput.value = "";
  searchResultsEl.innerHTML = "";
  loadDocumentList();
}

function onUploadError(message) {
  uploadLabel.classList.remove("uploading");
  uploadLabelText.textContent = "Click to upload a PDF";
  uploadStatus.textContent = message;
  uploadStatus.classList.add("error");
}

// ---------------- Chat handling ----------------

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionInput.value.trim();
  if (!question || !hasUploadedDocument) return;

  addUserMessage(question);
  questionInput.value = "";
  setInputEnabled(false);

  const typingBubble = addTypingIndicator();

  try {
    const response = await apiFetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    const data = await response.json();
    typingBubble.remove();

    if (!response.ok) throw new Error(data.error || "Something went wrong.");

    addAssistantMessage(data.answer, data.sources);
    loadDocumentList();
  } catch (error) {
    typingBubble.remove();
    addAssistantMessage(error.message, [], true);
  }

  setInputEnabled(true);
  questionInput.focus();
});

function setInputEnabled(enabled) {
  questionInput.disabled = !enabled;
  sendButton.disabled = !enabled;
}

// ---------------- Rendering helpers ----------------

function clearWelcomeMessage() {
  const welcome = chatWindow.querySelector(".welcome-message");
  if (welcome) welcome.remove();
}

function addUserMessage(text) {
  const messageEl = document.createElement("div");
  messageEl.className = "message user";
  messageEl.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
  chatWindow.appendChild(messageEl);
  scrollToBottom();
}

function addAssistantMessage(text, sources = [], isError = false) {
  const messageEl = document.createElement("div");
  messageEl.className = "message assistant";

  const bubbleClass = isError ? "bubble error" : "bubble";
  let html = `<div class="${bubbleClass}">${escapeHtml(text)}</div>`;

  if (!isError) {
    html += `<button class="copy-button" type="button">⧉ Copy</button>`;
  }

  if (sources && sources.length > 0) {
    const tags = sources
      .map((s) => {
        const pageLabel =
          s.page_number === "all" ? "All pages" : `p.${s.page_number}`;
        return `<span class="source-tag">${escapeHtml(s.document_name)} · ${pageLabel}</span>`;
      })
      .join("");
    html += `<div class="sources">${tags}</div>`;
  }

  messageEl.innerHTML = html;
  chatWindow.appendChild(messageEl);

  const copyBtn = messageEl.querySelector(".copy-button");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => copyToClipboard(text, copyBtn));
  }

  scrollToBottom();
}

function copyToClipboard(text, buttonEl) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      const original = buttonEl.textContent;
      buttonEl.textContent = "✓ Copied";
      buttonEl.classList.add("copied");
      setTimeout(() => {
        buttonEl.textContent = original;
        buttonEl.classList.remove("copied");
      }, 1500);
    })
    .catch((err) => console.error("Copy failed:", err));
}

function addTypingIndicator() {
  const messageEl = document.createElement("div");
  messageEl.className = "message assistant";
  messageEl.innerHTML = `
        <div class="bubble typing-indicator">
            <span></span><span></span><span></span>
        </div>
    `;
  chatWindow.appendChild(messageEl);
  scrollToBottom();
  return messageEl;
}

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
