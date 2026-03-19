const state = {
  workspace: null,
  selectedConcernId: null,
  selectedThreadId: null,
  messages: [],
};

const elements = {
  workspaceTitle: document.getElementById("workspace-title"),
  workspaceSubtitle: document.getElementById("workspace-subtitle"),
  modeLabel: document.getElementById("mode-label"),
  asOfLabel: document.getElementById("as-of-label"),
  statConcerns: document.getElementById("stat-concerns"),
  statThreads: document.getElementById("stat-threads"),
  statDeadlines: document.getElementById("stat-deadlines"),
  concernList: document.getElementById("concern-list"),
  threadList: document.getElementById("thread-list"),
  concernTitle: document.getElementById("concern-title"),
  concernMeta: document.getElementById("concern-meta"),
  concernPriority: document.getElementById("concern-priority"),
  concernStatus: document.getElementById("concern-status"),
  concernSummary: document.getElementById("concern-summary"),
  concernWhy: document.getElementById("concern-why"),
  quickPrompts: document.getElementById("quick-prompts"),
  nextSteps: document.getElementById("next-steps"),
  assistantFeed: document.getElementById("assistant-feed"),
  assistantForm: document.getElementById("assistant-form"),
  assistantInput: document.getElementById("assistant-input"),
  documentList: document.getElementById("document-list"),
  threadDetail: document.getElementById("thread-detail"),
  deadlineList: document.getElementById("deadline-list"),
  riskList: document.getElementById("risk-list"),
  draftList: document.getElementById("draft-list"),
};

function concernById(id) {
  return state.workspace.concerns.find((item) => item.id === id);
}

function threadById(id) {
  return state.workspace.threads.find((item) => item.id === id);
}

function linkedDocuments(concernId) {
  return state.workspace.documents.filter((doc) =>
    doc.linked_concern_ids.includes(concernId)
  );
}

function linkedThreads(concernId) {
  return state.workspace.threads.filter((thread) =>
    thread.linked_concern_ids.includes(concernId)
  );
}

function linkedDeadlines(concernId) {
  return state.workspace.deadlines.filter((deadline) => deadline.concern_id === concernId);
}

function linkedRisks(concernId) {
  const order = { critical: 0, high: 1, medium: 2, low: 3 };
  return state.workspace.risks
    .filter((risk) => risk.concern_id === concernId)
    .sort((a, b) => (order[a.severity] ?? 99) - (order[b.severity] ?? 99));
}

function formatDate(isoString) {
  const value = new Date(isoString);
  return value.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function setClassText(element, baseClass, suffix, label) {
  const variantBase = baseClass.replace(/-pill$/, "");
  element.className = `${baseClass} ${variantBase}-${suffix}`;
  element.textContent = label;
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function formatRichText(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replaceAll("\n", "<br>");
}

function renderWorkspaceMeta() {
  const { workspace, stats } = state.workspace;
  elements.workspaceTitle.textContent = workspace.title;
  elements.workspaceSubtitle.textContent = workspace.subtitle;
  elements.modeLabel.textContent = workspace.mode_label;
  elements.asOfLabel.textContent = `As of ${workspace.as_of}`;
  elements.statConcerns.textContent = stats.concerns_open;
  elements.statThreads.textContent = stats.threads_unread;
  elements.statDeadlines.textContent = stats.deadlines_urgent;
}

function renderConcernList() {
  elements.concernList.innerHTML = "";

  state.workspace.concerns.forEach((concern) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `list-item ${
      concern.id === state.selectedConcernId ? "active" : ""
    }`;
    button.innerHTML = `
      <div class="list-item-head">
        <strong class="item-title">${escapeHtml(concern.title)}</strong>
        <span class="priority-pill priority-${concern.priority}">${concern.priority}</span>
      </div>
      <p class="item-meta">${escapeHtml(concern.why_now)}</p>
    `;
    button.addEventListener("click", () => {
      state.selectedConcernId = concern.id;
      const firstThread = linkedThreads(concern.id)[0];
      if (firstThread) {
        state.selectedThreadId = firstThread.id;
      }
      render();
    });
    elements.concernList.appendChild(button);
  });
}

function renderThreadList() {
  elements.threadList.innerHTML = "";

  state.workspace.threads.forEach((thread) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `list-item ${
      thread.id === state.selectedThreadId ? "active" : ""
    }`;
    button.innerHTML = `
      <div class="list-item-head">
        <strong class="item-title">${escapeHtml(thread.subject)}</strong>
        ${thread.unread ? '<span class="status-pill status-watch">Unread</span>' : ""}
      </div>
      <p class="item-meta">${escapeHtml(thread.counterpart)}</p>
      <p class="item-meta">${escapeHtml(thread.snippet)}</p>
    `;
    button.addEventListener("click", () => {
      state.selectedThreadId = thread.id;
      renderThreadDetail();
    });
    elements.threadList.appendChild(button);
  });
}

function renderConcernHero() {
  const concern = concernById(state.selectedConcernId);
  if (!concern) {
    return;
  }

  elements.concernTitle.textContent = concern.title;
  elements.concernMeta.textContent = `${concern.category} concern`;
  setClassText(
    elements.concernPriority,
    "priority-pill",
    concern.priority,
    concern.priority
  );
  setClassText(
    elements.concernStatus,
    "status-pill",
    concern.status,
    concern.status
  );
  elements.concernSummary.textContent = concern.summary;
  elements.concernWhy.textContent = concern.why_now;

  elements.quickPrompts.innerHTML = "";
  const prompts = [...new Set([concern.default_prompt, ...state.workspace.quick_prompts])].slice(
    0,
    4
  );
  prompts.forEach((prompt) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chip";
    button.textContent = prompt;
    button.addEventListener("click", () => runAssistant(prompt));
    elements.quickPrompts.appendChild(button);
  });

  elements.nextSteps.innerHTML = "";
  concern.next_steps.forEach((step) => {
    const item = document.createElement("li");
    item.textContent = step;
    elements.nextSteps.appendChild(item);
  });
}

function renderDocuments() {
  const concern = concernById(state.selectedConcernId);
  const documents = linkedDocuments(concern.id);
  elements.documentList.innerHTML = "";

  if (!documents.length) {
    elements.documentList.innerHTML = '<p class="empty-state">No documents linked yet.</p>';
    return;
  }

  documents.forEach((doc) => {
    const card = document.createElement("article");
    card.className = "doc-card";
    card.innerHTML = `
      <div class="list-item-head">
        <strong class="doc-title">${escapeHtml(doc.title)}</strong>
        <span class="tag">${escapeHtml(doc.type)}</span>
      </div>
      <p class="doc-meta">${escapeHtml(doc.source_path)}</p>
      <p>${escapeHtml(doc.excerpt)}</p>
    `;
    elements.documentList.appendChild(card);
  });
}

function renderThreadDetail() {
  const thread = threadById(state.selectedThreadId);
  elements.threadDetail.innerHTML = "";

  if (!thread) {
    elements.threadDetail.innerHTML = '<p class="empty-state">Pick a Gmail thread to inspect it here.</p>';
    return;
  }

  const header = document.createElement("article");
  header.className = "thread-card";
  header.innerHTML = `
    <div class="list-item-head">
      <strong class="item-title">${escapeHtml(thread.subject)}</strong>
      ${thread.unread ? '<span class="status-pill status-watch">Unread</span>' : ""}
    </div>
    <p class="thread-meta">${escapeHtml(thread.counterpart)}</p>
    <p class="thread-meta">Last activity ${formatDate(thread.last_message_at)}</p>
  `;
  elements.threadDetail.appendChild(header);

  thread.messages.forEach((message) => {
    const card = document.createElement("article");
    card.className = `thread-message ${message.direction}`;
    card.innerHTML = `
      <small>${escapeHtml(message.direction)} · ${escapeHtml(message.from)} → ${escapeHtml(
        message.to
      )} · ${formatDate(message.sent_at)}</small>
      <p>${escapeHtml(message.body)}</p>
    `;
    elements.threadDetail.appendChild(card);
  });
}

function renderDeadlines() {
  const concern = concernById(state.selectedConcernId);
  const deadlines = linkedDeadlines(concern.id);
  elements.deadlineList.innerHTML = "";

  if (!deadlines.length) {
    elements.deadlineList.innerHTML =
      '<p class="empty-state">No deterministic deadlines attached to this concern yet.</p>';
    return;
  }

  deadlines.forEach((deadline) => {
    const card = document.createElement("article");
    card.className = "deadline-card";
    card.innerHTML = `
      <div class="deadline-head">
        <strong class="deadline-title">${escapeHtml(deadline.title)}</strong>
        <span class="severity-pill deadline-${deadline.status}">${deadline.status}</span>
      </div>
      <p class="deadline-meta">Due ${escapeHtml(deadline.due_date)} · ${escapeHtml(
        deadline.category
      )}</p>
      <p>${escapeHtml(deadline.action)}</p>
    `;
    elements.deadlineList.appendChild(card);
  });
}

function renderRisks() {
  const concern = concernById(state.selectedConcernId);
  const risks = linkedRisks(concern.id);
  elements.riskList.innerHTML = "";

  if (!risks.length) {
    elements.riskList.innerHTML = '<p class="empty-state">No risk cards for this concern.</p>';
    return;
  }

  risks.forEach((risk) => {
    const card = document.createElement("article");
    card.className = "risk-card";
    card.innerHTML = `
      <div class="list-item-head">
        <strong class="risk-title">${escapeHtml(risk.title)}</strong>
        <span class="severity-pill severity-${risk.severity}">${risk.severity}</span>
      </div>
      <p class="risk-meta">${escapeHtml(risk.message)}</p>
    `;
    elements.riskList.appendChild(card);
  });
}

function renderDrafts() {
  elements.draftList.innerHTML = "";

  if (!state.workspace.drafts.length) {
    elements.draftList.innerHTML =
      '<p class="empty-state">Generate a follow-up draft from the co-work panel.</p>';
    return;
  }

  state.workspace.drafts.forEach((draft) => {
    const card = document.createElement("article");
    card.className = "draft-card";
    card.innerHTML = `
      <div class="draft-head">
        <strong class="draft-title">${escapeHtml(draft.subject)}</strong>
        <span class="status-pill status-${draft.status}">${draft.status}</span>
      </div>
      <p class="draft-meta">${escapeHtml(draft.to)} · ${escapeHtml(draft.title)}</p>
      <p>${escapeHtml(draft.body)}</p>
    `;

    if (draft.status === "draft") {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "send-btn";
      button.textContent = "Simulate send";
      button.addEventListener("click", async () => {
        const response = await fetch(`/api/drafts/${draft.id}/send`, {
          method: "POST",
        });
        const updated = await response.json();
        const target = state.workspace.drafts.find((item) => item.id === updated.id);
        Object.assign(target, updated);
        renderDrafts();
        pushLocalAssistantMessage(
          `Draft sent for **${updated.title}** to ${updated.to}. In the real product this step would require explicit Gmail approval and send confirmation.`
        );
      });
      card.appendChild(button);
    }

    elements.draftList.appendChild(card);
  });
}

function renderAssistantFeed() {
  elements.assistantFeed.innerHTML = "";

  state.messages.forEach((message) => {
    const card = document.createElement("article");
    card.className = `message ${message.role}`;
    card.innerHTML = `
      <span class="message-role">${message.role === "assistant" ? "Workspace" : "You"}</span>
      <div class="message-body">${formatRichText(message.text)}</div>
    `;

    if (message.citations?.length) {
      const citationRow = document.createElement("div");
      citationRow.className = "citation-row";
      message.citations.forEach((citation) => {
        const chip = document.createElement("div");
        chip.className = "citation";
        chip.innerHTML = `
          <strong>${escapeHtml(citation.label)}</strong>
          <small>${escapeHtml(citation.source_path)}</small>
        `;
        citationRow.appendChild(chip);
      });
      card.appendChild(citationRow);
    }

    if (message.actions?.length) {
      const actionRow = document.createElement("div");
      actionRow.className = "action-row";
      message.actions.forEach((action) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "action-btn";
        button.textContent = action.label;
        button.addEventListener("click", async () => {
          if (action.type === "draft_email") {
            const response = await fetch("/api/drafts", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ concern_id: action.concern_id }),
            });
            const draft = await response.json();
            state.workspace.drafts.unshift(draft);
            renderDrafts();
            pushLocalAssistantMessage(
              `Created a draft email for **${draft.title}** with subject **${draft.subject}**. Review it in the draft queue before sending.`
            );
          }
        });
        actionRow.appendChild(button);
      });
      card.appendChild(actionRow);
    }

    elements.assistantFeed.appendChild(card);
  });
}

function pushLocalAssistantMessage(text) {
  state.messages.push({ role: "assistant", text });
  renderAssistantFeed();
}

async function runAssistant(prompt) {
  if (!prompt.trim()) return;

  state.messages.push({ role: "user", text: prompt });
  renderAssistantFeed();

  const response = await fetch("/api/assistant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      concern_id: state.selectedConcernId,
    }),
  });
  const payload = await response.json();
  state.messages.push({
    role: "assistant",
    text: payload.text,
    citations: payload.citations,
    actions: payload.actions,
  });
  renderAssistantFeed();
}

function render() {
  renderWorkspaceMeta();
  renderConcernList();
  renderThreadList();
  renderConcernHero();
  renderDocuments();
  renderThreadDetail();
  renderDeadlines();
  renderRisks();
  renderDrafts();
  renderAssistantFeed();
}

async function boot() {
  const response = await fetch("/api/workspace");
  state.workspace = await response.json();
  state.selectedConcernId = state.workspace.concerns[0]?.id ?? null;
  state.selectedThreadId = state.workspace.threads[0]?.id ?? null;
  state.messages = [
    {
      role: "assistant",
      text:
        "The workspace is live. Pick a concern, inspect the linked Gmail context, and ask for a status read, evidence summary, or follow-up draft.",
    },
  ];
  render();
}

elements.assistantForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = elements.assistantInput.value;
  elements.assistantInput.value = "";
  await runAssistant(prompt);
});

boot();
