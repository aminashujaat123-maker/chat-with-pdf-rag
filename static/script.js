// Chat with PDF — front-end logic.
// Handles: uploading a PDF, sending questions to /ask, and
// rendering the conversation (including source citations).

const pdfInput = document.getElementById("pdf-input");
const uploadLabel = document.getElementById("upload-label");
const uploadLabelText = document.getElementById("upload-label-text");
const uploadStatus = document.getElementById("upload-status");
const documentInfo = document.getElementById("document-info");
const docNameEl = document.getElementById("doc-name");
const docMetaEl = document.getElementById("doc-meta");

const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const questionInput = document.getElementById("question-input");
const sendButton = document.getElementById("send-button");

let hasUploadedDocument = false;

// ---------------- Upload handling ----------------

pdfInput.addEventListener("change", async () => {
  const file = pdfInput.files[0];
  if (!file) {
    return;
  }

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
    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Upload failed.");
    }

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

  clearWelcomeMessage();
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
  if (!question || !hasUploadedDocument) {
    return;
  }

  addUserMessage(question);
  questionInput.value = "";
  setInputEnabled(false);

  const typingBubble = addTypingIndicator();

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    const data = await response.json();
    typingBubble.remove();

    if (!response.ok) {
      throw new Error(data.error || "Something went wrong.");
    }

    addAssistantMessage(data.answer, data.sources);
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
  if (welcome) {
    welcome.remove();
  }
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

  if (sources && sources.length > 0) {
    const tags = sources
      .map(
        (s) =>
          `<span class="source-tag">${escapeHtml(s.document_name)} · p.${s.page_number}</span>`,
      )
      .join("");
    html += `<div class="sources">${tags}</div>`;
  }

  messageEl.innerHTML = html;
  chatWindow.appendChild(messageEl);
  scrollToBottom();
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
