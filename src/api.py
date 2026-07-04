import logging
import os
import re
import time
from pathlib import Path
from typing import Any, List, Optional
from threading import Lock
from functools import lru_cache

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from datetime import datetime

from config import settings
from search import RAGSearch


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

class ReviewSubmissionRequest(BaseModel):
    content: str
    priority: str = "medium"
    metadata: dict = {}

class ReviewActionRequest(BaseModel):
    review_id: str
    action: str  # "approve", "reject", "escalate"
    reviewer: str
    notes: str = ""

class ReviewResponse(BaseModel):
    review_id: str
    status: str
    content: str
    priority: str
    created_at: str
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    is_approved: Optional[bool] = None
    escalation_reason: Optional[str] = None

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI(
    title="RAG API",
    version="0.1.0",
    description="Production API for retrieval-augmented answers over local documents.",
)

# Add CORS middleware for frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Add LangChain middleware with human-in-the-loop integration
try:
    from middleware import LangChainMiddleware
    # Initialize LangChain middleware
    app.add_middleware(
        LangChainMiddleware,
        llm_model=settings.llm_model,
        api_key=settings.groq_api_key
    )
    logger.info("LangChain middleware with Groq models added successfully")
except ImportError as e:
    logger.warning(f"LangChain middleware not available: {e}")

# Initialize LangSmith integration
try:
    from rag_langsmith import initialize_langsmith
    if initialize_langsmith():
        logger.info("LangSmith integration initialized successfully")
    else:
        logger.warning("LangSmith integration failed to initialize")
except ImportError as e:
    logger.warning(f"LangSmith not available: {e}")
except Exception as e:
    logger.error(f"Failed to initialize LangSmith: {e}")

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request details
    logger.info(f"Request: {request.method} {request.url} - Client: {request.client.host if request.client else 'unknown'}")
    
    # Process the request
    response = await call_next(request)
    
    # Log response details
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - Time: {process_time:.3f}s - Content-Type: {response.headers.get('content-type', 'unknown')}")
    
    return response



_rag_lock = Lock()
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024

INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RAG Assistant</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #16181d;
      --muted: #606775;
      --line: #d9dde5;
      --primary: #185abc;
      --primary-dark: #123f84;
      --ok: #137333;
      --warn: #b06000;
      --error: #b3261e;
      --shadow: 0 18px 45px rgba(22, 24, 29, 0.12);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .shell {
      width: min(1040px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 22px;
    }

    h1 {
      margin: 0;
      font-size: clamp(28px, 4vw, 44px);
      line-height: 1.05;
      letter-spacing: 0;
    }

    .subtitle {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.45;
    }

    .status {
      min-width: 168px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--muted);
      font-size: 13px;
      text-align: right;
    }

    .status strong {
      display: block;
      margin-bottom: 2px;
      color: var(--text);
      font-size: 14px;
    }

    main {
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(280px, 0.55fr);
      gap: 18px;
      align-items: start;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }

    .ask-panel {
      padding: 18px;
    }

    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 700;
      font-size: 14px;
    }

    textarea {
      width: 100%;
      min-height: 180px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      color: var(--text);
      font: inherit;
      line-height: 1.5;
      outline: none;
    }

    textarea:focus,
    input:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(24, 90, 188, 0.16);
    }

    .controls {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 12px;
      margin-top: 14px;
      flex-wrap: wrap;
    }

    .top-k {
      display: grid;
      gap: 6px;
      max-width: 150px;
    }

    input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      font: inherit;
    }

    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    button {
      border: 0;
      border-radius: 8px;
      padding: 11px 15px;
      color: #fff;
      background: var(--primary);
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }

    button:hover {
      background: var(--primary-dark);
    }

    button.secondary {
      border: 1px solid var(--line);
      color: var(--text);
      background: #fff;
    }

    button.secondary:hover {
      background: #f0f2f5;
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.65;
    }

    .answer {
      margin-top: 18px;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
      min-height: 150px;
      white-space: pre-wrap;
      line-height: 1.55;
    }

    .answer.empty {
      color: var(--muted);
    }

    .side {
      padding: 16px;
    }

    .side h2 {
      margin: 0 0 12px;
      font-size: 16px;
      letter-spacing: 0;
    }

    .meta {
      display: grid;
      gap: 10px;
    }

    .meta-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 11px 0;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: 14px;
    }

    .meta-row:last-child {
      border-bottom: 0;
    }

    .pill {
      border-radius: 999px;
      padding: 4px 8px;
      background: #eef2f7;
      color: var(--text);
      font-size: 12px;
      font-weight: 700;
    }

    .pill.ok {
      background: #e6f4ea;
      color: var(--ok);
    }

    .pill.warn {
      background: #fff4e5;
      color: var(--warn);
    }

    .pill.error {
      background: #fce8e6;
      color: var(--error);
    }

    .docs-link {
      display: inline-block;
      margin-top: 14px;
      color: var(--primary);
      font-weight: 700;
      text-decoration: none;
    }

    .docs-link:hover {
      text-decoration: underline;
    }

    .upload-box {
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid var(--line);
    }

    .file-input {
      width: 100%;
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfe;
      font-size: 13px;
    }

    .upload-status {
      min-height: 20px;
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
    }

    .insights {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }

    .metric,
    .detail-box {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
    }

    .metric {
      padding: 10px;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
    }

    .metric strong {
      display: block;
      margin-top: 4px;
      font-size: 18px;
    }

    .details {
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }

    .detail-box {
      padding: 12px;
    }

    .detail-box h3 {
      margin: 0 0 8px;
      font-size: 14px;
      letter-spacing: 0;
    }

    .detail-box ul {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    @media (max-width: 820px) {
      header,
      main {
        display: block;
      }

      .status {
        margin-top: 16px;
        text-align: left;
      }

      .side {
        margin-top: 16px;
      }

      .insights {
        grid-template-columns: 1fr;
      }
    }

    /* HITL Modal Styles */
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(22, 24, 29, 0.4);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s ease;
    }

    .modal-overlay.active {
      opacity: 1;
      pointer-events: auto;
    }

    .modal-box {
      width: min(540px, calc(100% - 32px));
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      box-shadow: 0 24px 64px rgba(22, 24, 29, 0.2);
      padding: 24px;
      transform: scale(0.95);
      transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    .modal-overlay.active .modal-box {
      transform: scale(1);
    }

    .modal-header {
      margin-bottom: 16px;
    }

    .modal-title {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      color: var(--text);
    }

    .modal-body {
      margin-bottom: 24px;
      font-size: 14px;
      line-height: 1.5;
      color: var(--muted);
    }

    .pii-preview-box {
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
      padding: 12px;
    }

    .pii-preview-title {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      margin-bottom: 6px;
    }

    .pii-preview-content {
      font-family: monospace;
      font-size: 13px;
      color: var(--text);
      white-space: pre-wrap;
      word-break: break-all;
    }

    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      flex-wrap: wrap;
    }

    .modal-actions button {
      padding: 10px 16px;
      font-size: 14px;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--text);
      transition: all 0.2s ease;
    }

    .modal-actions button.primary {
      background: var(--primary);
      color: white;
      border-color: var(--primary);
    }

    .modal-actions button.primary:hover {
      background: var(--primary-dark);
    }

    .modal-actions button.danger {
      background: var(--error);
      color: white;
      border-color: var(--error);
    }

    .modal-actions button.danger:hover {
      background: #9d1c16;
    }

    .modal-actions button.secondary:hover {
      background: var(--bg);
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>RAG Assistant</h1>
        <p class="subtitle">Ask questions against your local document index.</p>
      </div>
      <div class="status" id="statusBox">
        <strong>Checking</strong>
        <span>Connecting to API...</span>
      </div>
    </header>

    <main>
      <section class="panel ask-panel">
        <form id="queryForm">
          <label for="query">Question</label>
          <textarea id="query" name="query" maxlength="4000" placeholder="What is NLP and explain it?" required></textarea>
          <div class="controls">
            <div class="top-k">
              <label for="topK">Top K</label>
              <input id="topK" name="topK" type="number" min="1" max="20" value="5">
            </div>
            <div class="actions">
              <button id="askButton" type="submit">Ask</button>
              <button class="secondary" id="clearButton" type="button">Clear</button>
            </div>
          </div>
        </form>

        <div class="answer empty" id="answer">Answer will appear here.</div>
        <div class="insights">
          <div class="metric">
            <span>Retrieved chunks</span>
            <strong id="retrievedMetric">-</strong>
          </div>
          <div class="metric">
            <span>Grounded</span>
            <strong id="groundedMetric">-</strong>
          </div>
          <div class="metric">
            <span>Guardrail</span>
            <strong id="guardrailMetric">-</strong>
          </div>
        </div>
        <div class="details">
          <div class="detail-box">
            <h3>Sources</h3>
            <ul id="sourcesList"><li>No sources yet.</li></ul>
          </div>
          <div class="detail-box">
            <h3>Evaluation</h3>
            <ul id="evaluationList"><li>No evaluation yet.</li></ul>
          </div>
        </div>
      </section>

      <aside class="panel side">
        <h2>System</h2>
        <div class="meta">
          <div class="meta-row">
            <span>API</span>
            <span class="pill" id="apiState">Checking</span>
          </div>
          <div class="meta-row">
            <span>Index</span>
            <span class="pill" id="indexState">Checking</span>
          </div>
          <div class="meta-row">
            <span>LLM key</span>
            <span class="pill" id="llmState">Checking</span>
          </div>
          <div class="meta-row">
            <span>Guardrails</span>
            <span class="pill" id="guardrailState">Checking</span>
          </div>
          <div class="meta-row">
            <span>Evaluation</span>
            <span class="pill" id="evaluationState">Checking</span>
          </div>
          <div class="meta-row">
            <span>MCP</span>
            <span class="pill" id="mcpState">Checking</span>
          </div>
        </div>
        <button class="secondary" id="reloadButton" type="button" style="margin-top: 14px; width: 100%;">Reload index</button>
        <div class="upload-box">
          <label for="pdfUpload">Upload PDF</label>
          <input class="file-input" id="pdfUpload" type="file" accept="application/pdf,.pdf">
          <button id="uploadButton" type="button" style="margin-top: 10px; width: 100%;">Upload and rebuild</button>
          <div class="upload-status" id="uploadStatus"></div>
        </div>
        <a class="docs-link" href="/docs">Open API docs</a>
      </aside>
    </main>
  </div>

  <!-- Human-in-the-Loop PII Modal -->
  <div class="modal-overlay" id="piiModal">
    <div class="modal-box">
      <div class="modal-header">
        <h2 class="modal-title">PII Detected</h2>
      </div>
      <div class="modal-body">
        <p>We detected sensitive details (like email addresses or phone numbers) in your question. Please choose how you want to proceed:</p>
        <div class="pii-preview-box">
          <div class="pii-preview-title">Original Question</div>
          <div class="pii-preview-content" id="originalQueryPreview"></div>
        </div>
        <div class="pii-preview-box">
          <div class="pii-preview-title">Redacted Proposal</div>
          <div class="pii-preview-content" id="redactedQueryPreview"></div>
        </div>
      </div>
      <div class="modal-actions">
        <button class="secondary" id="modalCancelButton">Cancel</button>
        <button id="modalRedactedButton">Use Redacted</button>
        <button class="primary" id="modalBypassButton">Proceed Unredacted</button>
      </div>
    </div>
  </div>

  <script>
    const form = document.getElementById("queryForm");
    const queryInput = document.getElementById("query");
    const topKInput = document.getElementById("topK");
    const askButton = document.getElementById("askButton");
    const clearButton = document.getElementById("clearButton");
    const reloadButton = document.getElementById("reloadButton");
    const pdfUpload = document.getElementById("pdfUpload");
    const uploadButton = document.getElementById("uploadButton");
    const uploadStatus = document.getElementById("uploadStatus");
    const answer = document.getElementById("answer");
    const statusBox = document.getElementById("statusBox");
    const apiState = document.getElementById("apiState");
    const indexState = document.getElementById("indexState");
    const llmState = document.getElementById("llmState");
    const guardrailState = document.getElementById("guardrailState");
    const evaluationState = document.getElementById("evaluationState");
    const mcpState = document.getElementById("mcpState");
    const retrievedMetric = document.getElementById("retrievedMetric");
    const groundedMetric = document.getElementById("groundedMetric");
    const guardrailMetric = document.getElementById("guardrailMetric");
    const sourcesList = document.getElementById("sourcesList");
    const evaluationList = document.getElementById("evaluationList");

    // HITL Modal Elements
    const piiModal = document.getElementById("piiModal");
    const originalQueryPreview = document.getElementById("originalQueryPreview");
    const redactedQueryPreview = document.getElementById("redactedQueryPreview");
    const modalCancelButton = document.getElementById("modalCancelButton");
    const modalRedactedButton = document.getElementById("modalRedactedButton");
    const modalBypassButton = document.getElementById("modalBypassButton");

    function setPill(element, label, state) {
      element.textContent = label;
      element.className = "pill " + state;
    }

    function setAnswer(text, isEmpty = false) {
      answer.textContent = text;
      answer.classList.toggle("empty", isEmpty);
    }

    function resetInsights() {
      retrievedMetric.textContent = "-";
      groundedMetric.textContent = "-";
      guardrailMetric.textContent = "-";
      sourcesList.innerHTML = "<li>No sources yet.</li>";
      evaluationList.innerHTML = "<li>No evaluation yet.</li>";
    }

    function renderInsights(data) {
      const evaluation = data.evaluation || {};
      const guardrails = data.guardrails || {};
      const sources = data.sources || [];

      retrievedMetric.textContent = evaluation.retrieved_chunks ?? "-";
      groundedMetric.textContent = evaluation.grounded ? "Yes" : "No";
      guardrailMetric.textContent = guardrails.answer_allowed === false ? "Blocked" : "Passed";

      if (sources.length) {
        sourcesList.innerHTML = sources.map((source) => {
          const page = source.page === null || source.page === undefined ? "" : " page " + (Number(source.page) + 1);
          const distance = source.distance === null || source.distance === undefined ? "" : " distance " + Number(source.distance).toFixed(3);
          const label = String(source.source || "unknown").split(/[\\\\/]/).pop();
          return "<li><strong>" + label + "</strong>" + page + distance + "</li>";
        }).join("");
      } else {
        sourcesList.innerHTML = "<li>No sources returned.</li>";
      }

      evaluationList.innerHTML = [
        "<li>Query-context overlap: " + (evaluation.query_context_overlap ?? "-") + "</li>",
        "<li>Answer-context overlap: " + (evaluation.answer_context_overlap ?? "-") + "</li>",
        "<li>Average distance: " + (evaluation.avg_distance ?? "-") + "</li>",
        "<li>PII redacted: " + (guardrails.pii_redacted ? "yes" : "no") + "</li>"
      ].join("");
    }

    async function refreshReady() {
      try {
        const response = await fetch("/ready");
        if (!response.ok) {
          throw new Error(await response.text());
        }
        const data = await response.json();
        statusBox.innerHTML = "<strong>Ready</strong><span>API is online</span>";
        setPill(apiState, "Online", "ok");
        setPill(indexState, data.index_loaded ? "Loaded" : "Missing", data.index_loaded ? "ok" : "warn");
        setPill(llmState, data.llm_configured ? "Configured" : "Missing", data.llm_configured ? "ok" : "warn");
        setPill(guardrailState, data.guardrails_enabled ? "Enabled" : "Off", data.guardrails_enabled ? "ok" : "warn");
        setPill(evaluationState, data.evaluation_enabled ? "Enabled" : "Off", data.evaluation_enabled ? "ok" : "warn");
        setPill(mcpState, data.mcp_configured ? "Configured" : "Not set", data.mcp_configured ? "ok" : "warn");
      } catch (error) {
        statusBox.innerHTML = "<strong>Unavailable</strong><span>Check server logs</span>";
        setPill(apiState, "Error", "error");
        setPill(indexState, "Unknown", "warn");
        setPill(llmState, "Unknown", "warn");
        setPill(guardrailState, "Unknown", "warn");
        setPill(evaluationState, "Unknown", "warn");
        setPill(mcpState, "Unknown", "warn");
      }
    }

    async function executeQuery(queryText, options = {}) {
      const topK = Number(topKInput.value || 5);
      askButton.disabled = true;
      setAnswer("Thinking...");

      try {
        const payload = {
          query: queryText,
          top_k: topK,
          allow_pii: !!options.allow_pii,
          force_redact: !!options.force_redact
        };
        const response = await fetch("/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "Query failed.");
        }

        if (data.status === "requires_review") {
          originalQueryPreview.textContent = data.original_query;
          redactedQueryPreview.textContent = data.redacted_query;
          piiModal.classList.add("active");
          setAnswer("PII detected in your query. Please review the prompt above.");
          return;
        }

        piiModal.classList.remove("active");
        setAnswer(data.answer || "No answer returned.");
        renderInsights(data);
      } catch (error) {
        piiModal.classList.remove("active");
        setAnswer(error.message || "Query failed.");
        resetInsights();
      } finally {
        askButton.disabled = false;
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const query = queryInput.value.trim();
      if (!query) {
        queryInput.focus();
        return;
      }
      await executeQuery(query);
    });

    modalCancelButton.addEventListener("click", () => {
      piiModal.classList.remove("active");
      setAnswer("Answer will appear here.", true);
      resetInsights();
      queryInput.focus();
    });

    modalRedactedButton.addEventListener("click", async () => {
      const query = queryInput.value.trim();
      piiModal.classList.remove("active");
      await executeQuery(query, { force_redact: true });
    });

    modalBypassButton.addEventListener("click", async () => {
      const query = queryInput.value.trim();
      piiModal.classList.remove("active");
      await executeQuery(query, { allow_pii: true });
    });

    clearButton.addEventListener("click", () => {
      queryInput.value = "";
      setAnswer("Answer will appear here.", true);
      resetInsights();
      queryInput.focus();
    });

    reloadButton.addEventListener("click", async () => {
      reloadButton.disabled = true;
      try {
        const response = await fetch("/reload", { method: "POST" });
        if (!response.ok) {
          throw new Error(await response.text());
        }
        await refreshReady();
      } catch (error) {
        setAnswer(error.message || "Reload failed.");
      } finally {
        reloadButton.disabled = false;
      }
    });

    uploadButton.addEventListener("click", async () => {
      const file = pdfUpload.files && pdfUpload.files[0];
      if (!file) {
        uploadStatus.textContent = "Choose a PDF first.";
        pdfUpload.focus();
        return;
      }
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        uploadStatus.textContent = "Only PDF files are supported here.";
        return;
      }

      uploadButton.disabled = true;
      uploadStatus.textContent = "Uploading and rebuilding index...";

      try {
        const response = await fetch("/upload/pdf", {
          method: "POST",
          headers: {
            "Content-Type": "application/pdf",
            "X-Filename": file.name
          },
          body: file
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "Upload failed.");
        }
        uploadStatus.textContent = "Uploaded " + data.filename + ". Index rebuilt.";
        await refreshReady();
      } catch (error) {
        uploadStatus.textContent = error.message || "Upload failed.";
      } finally {
        uploadButton.disabled = false;
      }
    });

    refreshReady();
    resetInsights();
  </script>
</body>
</html>
"""


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(default=settings.default_top_k, ge=1, le=20)
    allow_pii: bool = Field(default=False)
    force_redact: bool = Field(default=False)


class QueryResponse(BaseModel):
    status: str = "success"
    answer: str | None = None
    top_k: int
    sources: list[dict[str, Any]] = Field(default_factory=list)
    evaluation: dict[str, Any] = Field(default_factory=dict)
    guardrails: dict[str, Any] = Field(default_factory=dict)
    original_query: str | None = None
    redacted_query: str | None = None


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    index_loaded: bool
    llm_configured: bool
    guardrails_enabled: bool = True
    evaluation_enabled: bool = True
    mcp_configured: bool = False


class UploadResponse(BaseModel):
    status: str
    filename: str
    index_loaded: bool


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return INDEX_HTML

@app.get("/hitl", response_class=HTMLResponse)
async def hitl_ui() -> HTMLResponse:
    """Human-in-the-Loop Management UI"""
    try:
        with open("src/hitl_ui.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Human-in-the-Loop UI</h1><p>UI file not found</p>",
            status_code=404
        )


@lru_cache(maxsize=1)
def get_rag_search() -> RAGSearch:
    with _rag_lock:
        return RAGSearch(
            persist_dir=settings.persist_dir,
            data_dir=settings.data_dir,
            embedding_model=settings.embedding_model,
            llm_model=settings.llm_model,
            groq_api_key=settings.groq_api_key,
            auto_build_index=settings.auto_build_index,
        )





def _safe_upload_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    if not name:
        raise ValueError("Filename is required.")
    if not name.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")
    return name


def _index_files_exist() -> bool:
    persist_dir = Path(settings.persist_dir)
    return (persist_dir / "faiss.index").exists() and (persist_dir / "metadata.pkl").exists()


def _rebuild_index() -> RAGSearch:
    with _rag_lock:
        docs = load_all_documents(settings.data_dir)
        if not docs:
            raise ValueError(f"No supported documents found in {settings.data_dir}")
        store = FaissVectorStore(settings.persist_dir, settings.embedding_model)
        store.build_from_documents(docs)
        get_rag_search.cache_clear()
    return get_rag_search()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    return ReadyResponse(
        status="ready",
        index_loaded=_index_files_exist(),
        llm_configured=bool(settings.groq_api_key and settings.groq_api_key != "your_groq_api_key_here"),
        guardrails_enabled=True,
        evaluation_enabled=True,
        mcp_configured=True,
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GROQ_API_KEY is not configured.",
        )

    # Validate query using guardrails
    from guardrails import GuardrailResult, build_guardrail_payload, validate_query
    query_guardrail = validate_query(request.query)

    # Standard blocked patterns (e.g. prompt injection, length) should still raise 400 Bad Request
    if not query_guardrail.allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(query_guardrail.reasons),
        )

    # Human-in-the-loop: if PII is detected, and neither allow_pii nor force_redact is set
    if query_guardrail.pii_redacted and not request.allow_pii and not request.force_redact:
        # Submit for human review with priority based on sensitivity
        pii_patterns_detected = []
        for pattern_name, pattern in PII_PATTERNS.items():
            if re.search(pattern, request.query):
                pii_patterns_detected.append(pattern_name)
        
        priority = ReviewPriority.HIGH if pii_patterns_detected else ReviewPriority.MEDIUM
        
        review_metadata = {
            "pii_detected": pii_patterns_detected,
            "original_query": request.query,
            "redacted_query": query_guardrail.redacted_query,
            "timestamp": datetime.now().isoformat()
        }
        
        # Submit for review
        await human_in_loop_manager.submit_for_review(
            content=request.query,
            priority=priority,
            metadata=review_metadata
        )
        
        review_guardrail = GuardrailResult(
            allowed=True,
            reasons=[f"PII detected ({', '.join(pii_patterns_detected)}) and requires human review."],
            pii_redacted=True,
            redacted_query=query_guardrail.redacted_query,
            redacted_answer=query_guardrail.redacted_query,
        )
        return QueryResponse(
            status="requires_review",
            top_k=request.top_k,
            original_query=request.query,
            redacted_query=query_guardrail.redacted_query,
            sources=[],
            evaluation={},
            guardrails=build_guardrail_payload(
                query_guardrail,
                review_guardrail,
                allow_pii=request.allow_pii,
            ),
        )

    # Determine what query string to actually use in RAG search
    actual_query = query_guardrail.redacted_query if request.force_redact else request.query

    try:
        rag = get_rag_search()
        result = rag.search_and_summarize_with_metadata(
            actual_query,
            top_k=request.top_k,
            allow_pii=request.allow_pii
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query failed.",
        ) from exc

    return QueryResponse(
        status="success",
        answer=result["answer"],
        top_k=request.top_k,
        sources=result["sources"],
        evaluation=result["evaluation"],
        guardrails=result["guardrails"],
    )


@app.post("/reload", response_model=ReadyResponse)
def reload_index() -> ReadyResponse:
    get_rag_search.cache_clear()
    rag = get_rag_search()
    return ReadyResponse(
        status="ready",
        index_loaded=rag.is_ready,
        llm_configured=rag.llm_configured,
        guardrails_enabled=True,
        evaluation_enabled=True,
        mcp_configured=True,
    )


@app.post("/upload/pdf", response_model=UploadResponse)
async def upload_pdf(
    request: Request,
    x_filename: str = Header(default="document.pdf"),
) -> UploadResponse:
    try:
        filename = _safe_upload_filename(x_filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    content = await request.body()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded PDF is empty.",
        )
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF is larger than 25 MB.",
        )
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file does not look like a PDF.",
        )

    upload_dir = Path(settings.data_dir) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = upload_dir / filename
    upload_path.write_bytes(content)

    try:
        rag = _rebuild_index()
    except Exception as exc:
        logger.exception("Failed to rebuild index after upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF uploaded, but index rebuild failed.",
        ) from exc

    return UploadResponse(status="uploaded", filename=filename, index_loaded=rag.is_ready)


# Human-in-the-loop Management Endpoints
from pydantic import BaseModel
from human_in_loop import human_in_loop_manager, ReviewPriority

@app.post("/hitl/submit", response_model=ReviewResponse)
async def submit_for_review(request: ReviewSubmissionRequest) -> ReviewResponse:
    """Submit content for human review"""
    priority = ReviewPriority(request.priority.lower())
    review = await human_in_loop_manager.submit_for_review(
        content=request.content,
        priority=priority,
        metadata=request.metadata
    )
    
    return ReviewResponse(
        review_id=review.id,
        status=review.status.value,
        content=review.content,
        priority=review.priority.value,
        created_at=review.created_at.isoformat(),
        reviewed_at=review.reviewed_at.isoformat() if review.reviewed_at else None,
        reviewed_by=review.reviewed_by,
        review_notes=review.review_notes,
        is_approved=review.is_approved,
        escalation_reason=review.escalation_reason
    )

@app.get("/hitl/reviews/pending", response_model=List[ReviewResponse])
async def get_pending_reviews(priority: Optional[str] = None) -> List[ReviewResponse]:
    """Get all pending reviews, optionally filtered by priority"""
    if priority:
        review_priority = ReviewPriority(priority.lower())
        reviews = await human_in_loop_manager.get_pending_reviews(review_priority)
    else:
        reviews = await human_in_loop_manager.get_pending_reviews()
    
    return [
        ReviewResponse(
            review_id=review.id,
            status=review.status.value,
            content=review.content,
            priority=review.priority.value,
            created_at=review.created_at.isoformat(),
            reviewed_at=review.reviewed_at.isoformat() if review.reviewed_at else None,
            reviewed_by=review.reviewed_by,
            review_notes=review.review_notes,
            is_approved=review.is_approved,
            escalation_reason=review.escalation_reason
        )
        for review in reviews
    ]

@app.post("/hitl/review/{review_id}/approve")
async def approve_review(review_id: str, request: ReviewActionRequest) -> dict:
    """Approve a review request"""
    success = await human_in_loop_manager.approve_review(
        review_id=review_id,
        reviewer=request.reviewer,
        notes=request.notes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or already processed"
        )
    
    return {"message": "Review approved successfully"}

@app.post("/hitl/review/{review_id}/reject")
async def reject_review(review_id: str, request: ReviewActionRequest) -> dict:
    """Reject a review request"""
    success = await human_in_loop_manager.reject_review(
        review_id=review_id,
        reviewer=request.reviewer,
        notes=request.notes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or already processed"
        )
    
    return {"message": "Review rejected successfully"}

@app.post("/hitl/review/{review_id}/escalate")
async def escalate_review(review_id: str, request: ReviewActionRequest) -> dict:
    """Escalate a review request"""
    success = await human_in_loop_manager.escalate_review(
        review_id=review_id,
        reason=request.notes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or already processed"
        )
    
    return {"message": "Review escalated successfully"}

@app.get("/hitl/reviews/history", response_model=List[ReviewResponse])
async def get_review_history(days: int = 7) -> List[ReviewResponse]:
    """Get review history for the specified number of days"""
    reviews = await human_in_loop_manager.get_review_history(days)
    
    return [
        ReviewResponse(
            review_id=review.id,
            status=review.status.value,
            content=review.content,
            priority=review.priority.value,
            created_at=review.created_at.isoformat(),
            reviewed_at=review.reviewed_at.isoformat() if review.reviewed_at else None,
            reviewed_by=review.reviewed_by,
            review_notes=review.review_notes,
            is_approved=review.is_approved,
            escalation_reason=review.escalation_reason
        )
        for review in reviews
    ]

@app.get("/hitl/reviews/statistics")
async def get_review_statistics() -> dict:
    """Get review statistics"""
    stats = await human_in_loop_manager.get_review_statistics()
    return stats

@app.get("/monitoring/metrics")
async def get_monitoring_metrics() -> dict:
    """Get monitoring metrics from middleware"""
    # Get metrics from request monitoring middleware
    from middleware import RequestMonitoringMiddleware
    # This would need access to the middleware instance
    # For now, return basic metrics
    return {
        "timestamp": datetime.now().isoformat(),
        "message": "Monitoring metrics available - middleware integration needed for full metrics"
    }

@app.get("/monitoring/security")
async def get_security_metrics() -> dict:
    """Get security monitoring metrics"""
    from middleware import SecurityMonitoringMiddleware
    # This would need access to the middleware instance
    # For now, return basic security info
    return {
        "timestamp": datetime.now().isoformat(),
        "message": "Security monitoring active - middleware integration needed for full metrics"
    }

@app.post("/agent/process")
async def process_with_agent(request: dict) -> dict:
    """Process content using LangChain agent for human-in-the-loop decisions"""
    try:
        content = request.get("content", "")
        context = request.get("context", {})
        
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        # Process with LangChain agent
        result = await human_in_loop_manager.process_with_agent(content, context)
        
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Agent processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")

@app.post("/agent/validate")
async def validate_content(request: dict) -> dict:
    """Validate content using LangChain agent"""
    try:
        content = request.get("content", "")
        
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        # Use agent for validation
        result = await human_in_loop_manager.process_with_agent(
            content,
            {"validation_mode": True}
        )
        
        return {
            "status": "success",
            "validation_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Content validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Content validation failed: {str(e)}")

@app.get("/agent/status")
async def get_agent_status() -> dict:
    """Get LangChain agent status"""
    try:
        return {
            "langchain_available": LANGCHAIN_AVAILABLE,
            "agent_enabled": human_in_loop_manager.agent_executor is not None,
            "llm_configured": human_in_loop_manager.llm is not None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        return {
            "langchain_available": False,
            "agent_enabled": False,
            "llm_configured": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/monitoring/requests")
async def get_request_metrics(request_id: Optional[str] = None) -> dict:
    """Get request metrics"""
    from middleware import LangChainMiddleware
    # This would need access to the middleware instance
    # For now, return basic request info
    return {
        "timestamp": datetime.now().isoformat(),
        "message": "Request monitoring active - LangChain middleware integrated"
    }

# Enhanced Evaluation Endpoints
@app.post("/evaluate/enhanced")
async def enhanced_evaluation(request: dict) -> dict:
    """Perform enhanced RAG evaluation with detailed explanations for LangSmith"""
    if not ENHANCED_EVAL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Enhanced evaluation not available")
    
    try:
        question = request.get("question")
        answer = request.get("answer")
        documents = request.get("documents", [])
        reference_answer = request.get("reference_answer")
        experiment_name = request.get("experiment_name", "enhanced-rag-evaluation")
        metadata = request.get("metadata", {})
        
        if not question or not answer:
            raise HTTPException(status_code=400, detail="Question and answer are required")
        
        # Perform enhanced evaluation
        evaluation = evaluate_rag_with_explanations(
            question=question,
            answer=answer,
            documents=documents,
            reference_answer=reference_answer,
            **metadata
        )
        
        # Send to LangSmith if available
        if send_enhanced_langsmith_evaluation:
            langsmith_result = send_enhanced_langsmith_evaluation(
                question=question,
                answer=answer,
                documents=documents,
                reference_answer=reference_answer,
                experiment_name=experiment_name,
                metadata=metadata
            )
            
            return {
                "status": "success",
                "evaluation": evaluation.to_dict(),
                "langsmith_result": langsmith_result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "success",
                "evaluation": evaluation.to_dict(),
                "langsmith_result": None,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Enhanced evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Enhanced evaluation failed: {str(e)}")

@app.post("/evaluate/query")
async def evaluate_query_response(request: dict) -> dict:
    """Evaluate a specific query-response pair with enhanced metrics"""
    if not ENHANCED_EVAL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Enhanced evaluation not available")
    
    try:
        query = request.get("query")
        response = request.get("response")
        reference_answer = request.get("reference_answer")
        documents = request.get("documents", [])
        
        if not query or not response:
            raise HTTPException(status_code=400, detail="Query and response are required")
        
        # Perform evaluation with the RAG system
        from search import RAGSearch
        rag_search = RAGSearch()
        
        # Get search results for evaluation
        search_results = rag_search.search(query, top_k=5)
        
        # Perform enhanced evaluation
        evaluation = evaluate_rag_with_explanations(
            question=query,
            answer=response,
            documents=documents or search_results.get("sources", []),
            reference_answer=reference_answer,
            avg_distance=search_results.get("evaluation", {}).get("avg_distance"),
            grounded=search_results.get("evaluation", {}).get("grounded", False)
        )
        
        return {
            "status": "success",
            "evaluation": evaluation.to_dict(),
            "query_results": search_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Query evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query evaluation failed: {str(e)}")

@app.get("/evaluation/status")
async def get_evaluation_status() -> dict:
    """Get the status of enhanced evaluation capabilities"""
    return {
        "enhanced_evaluation_available": ENHANCED_EVAL_AVAILABLE,
        "langsmith_available": False,  # LangSmith integration disabled
        "langsmith_connected": False,
        "available_models": ["llama-3.3-70b-versatile", "mixtral-8x7b-instruct", "openai/gpt-oss-120b"] if ENHANCED_EVAL_AVAILABLE else [],
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    
    print("Starting RAG API server on 127.0.0.1:8001")
    print("API Documentation available at: http://127.0.0.1:8001/docs")
    print("Health check available at: http://127.0.0.1:8001/health")
    
    uvicorn.run(app, host="127.0.0.1", port=8001)
