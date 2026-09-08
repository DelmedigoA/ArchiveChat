const state = {
  items: new Map(),
  busy: false,
};

const els = {
  composer: document.getElementById("composer"),
  question: document.getElementById("question"),
  messages: document.getElementById("messages"),
  status: document.getElementById("status"),
};

els.composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy) {
    return;
  }
  const question = els.question.value.trim();
  if (!question) {
    return;
  }
  els.question.value = "";
  appendMessage("user", question);
  await ask(question);
});

els.question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    els.composer.requestSubmit();
  }
});

document.addEventListener("click", async (event) => {
  const sourceButton = event.target.closest("[data-item-id]");
  if (sourceButton) {
    const item = state.items.get(sourceButton.dataset.itemId);
    if (item) {
      openItemModal(item);
    }
    return;
  }

  const shareButton = event.target.closest("[data-share-item]");
  if (shareButton) {
    await copyItemUrl(shareButton.dataset.shareItem);
    return;
  }

  const modal = document.getElementById("item-modal");
  if (modal && (event.target === modal || event.target.closest("[data-modal-close]"))) {
    closeItemModal();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeItemModal();
  }
});

appendMessage("assistant", "What would you like to understand from the archive?");

async function ask(question) {
  setBusy(true);
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const payload = await response.json();
    if (!response.ok) {
      appendMessage("assistant", payload.detail || payload.error || "Chat failed.");
      return;
    }
    for (const item of payload.items || []) {
      state.items.set(item.item_id, item);
    }
    appendAssistantMessage(payload.answer || "", payload.items || []);
  } catch (error) {
    appendMessage("assistant", `Request failed: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

function setBusy(value) {
  state.busy = value;
  els.status.textContent = value ? "Thinking" : "Ready";
  els.composer.querySelector("button").disabled = value;
}

function appendMessage(role, text) {
  const node = document.createElement("article");
  node.className = `message message--${role}`;
  node.textContent = text;
  els.messages.appendChild(node);
  node.scrollIntoView({ block: "end" });
}

function appendAssistantMessage(answer, items) {
  const node = document.createElement("article");
  node.className = "message message--assistant";
  node.innerHTML = renderAnswer(answer, items);
  els.messages.appendChild(node);
  node.scrollIntoView({ block: "end" });
}

function renderAnswer(answer, items) {
  const byUrl = new Map();
  for (const item of items) {
    if (item.url) {
      byUrl.set(normalizeUrl(item.url), item);
    }
  }

  const citationNumbers = new Map();
  let nextCitationNumber = 1;
  const escaped = escapeHtml(answer);
  const formatted = renderInlineMarkdown(escaped);
  const linked = formatted.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, (match, label, url) => {
    const item = byUrl.get(normalizeUrl(url));
    if (!item) {
      return `<a href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">${label}</a>`;
    }

    if (!citationNumbers.has(item.item_id)) {
      citationNumbers.set(item.item_id, nextCitationNumber);
      nextCitationNumber += 1;
    }
    const number = citationNumbers.get(item.item_id);
    const title = item.title || label || `Source ${number}`;
    return `<button class="citation-link" type="button" data-item-id="${escapeAttribute(item.item_id)}" title="${escapeAttribute(title)}" aria-label="Open source ${number}: ${escapeAttribute(title)}">[${number}]</button>`;
  });
  return linked
    .split(/\n{2,}/)
    .map((paragraph) => `<p>${paragraph.replace(/\n/g, "<br>")}</p>`)
    .join("");
}
function renderInlineMarkdown(text) {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/(^|\s)\*([^*]+)\*/g, '$1<em>$2</em>')
    .replace(/(^|\s)_([^_]+)_/g, '$1<em>$2</em>');
}

function openItemModal(item) {
  closeItemModal();
  const catalog = item.catalog || {};
  const sourceUrl = item.url || catalog.link || "";
  const modal = document.createElement("div");
  modal.className = "item-modal";
  modal.id = "item-modal";
  modal.innerHTML = `
    <div class="item-modal__panel" role="dialog" aria-modal="true" aria-labelledby="item-modal-title">
      <button class="item-modal__close" type="button" data-modal-close aria-label="Close">×</button>
      <div class="item-modal__body">
        <h2 id="item-modal-title">${escapeHtml(item.title || catalog.english_title || "Untitled item")}</h2>
        ${item.hebrew_title ? `<div class="item-modal__hebrew" dir="rtl">${escapeHtml(item.hebrew_title)}</div>` : ""}
        <div class="item-modal__meta">${renderMeta(catalog)}</div>
        ${renderIconChipRow("location", splitValues(catalog.location), "Location")}
        ${renderIconChipRow("person", catalog.figures_tags, "Figures")}
        ${renderEventDate(catalog)}
        <p class="item-modal__summary">${escapeHtml(item.description || item.hebrew_description || catalog.english_description || "")}</p>
        ${renderCatalogChips(catalog)}
        <div class="item-modal__published">${renderPublished(catalog)}</div>
      </div>
      <div class="item-modal__actions">
        <button class="item-modal__secondary" type="button" data-share-item="${escapeAttribute(item.item_id)}">Share <span aria-hidden="true">↗</span></button>
        <button class="item-modal__secondary" type="button">Found an issue? <span aria-hidden="true">⚑</span></button>
        ${sourceUrl ? `<a class="item-modal__primary" href="${escapeAttribute(sourceUrl)}" target="_blank" rel="noreferrer">View Item <span aria-hidden="true">↗</span></a>` : ""}
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  document.body.classList.add("has-modal-open");
}
function closeItemModal() {
  const modal = document.getElementById("item-modal");
  if (modal) {
    modal.remove();
  }
  document.body.classList.remove("has-modal-open");
}

function renderMeta(catalog) {
  const values = [
    catalog.type,
    formatList(catalog.media),
    formatList(catalog.language),
    catalog.id ? `Record #${catalog.id}` : "",
  ].filter(Boolean);
  return values.map(escapeHtml).join(" | ");
}

function renderIconChipRow(kind, values, label) {
  if (!Array.isArray(values) || !values.length) {
    return "";
  }
  const icon = kind === "location" ? "📍" : "👤";
  return `
    <div class="item-modal__icon-row" aria-label="${escapeAttribute(label)}">
      <span class="item-modal__row-icon" aria-hidden="true">${icon}</span>
      <div class="item-modal__row-chips">
        ${values.map((value) => `<span class="chip chip--neutral">${escapeHtml(value)}</span>`).join("")}
      </div>
    </div>
  `;
}

function renderEventDate(catalog) {
  const eventDate = formatDateRange(catalog.event_date_from, catalog.event_date_to);
  if (!eventDate) {
    return "";
  }
  return `
    <div class="item-modal__event-date">
      <span aria-hidden="true">▣</span>
      <span>Event Date: ${escapeHtml(eventDate)}</span>
    </div>
  `;
}

function renderCatalogChips(catalog) {
  const chips = [
    ...chipItems(catalog.theme_tags, "theme"),
    ...chipItems(catalog.countries_and_organizations_tags, "organization"),
    ...chipItems(catalog.locations_tags, "location"),
    ...chipItems(catalog.figures_tags, "figure"),
  ];
  if (!chips.length) {
    return "";
  }
  return `<div class="item-modal__chips">${chips.join("")}</div>`;
}

function chipItems(values, kind) {
  if (!Array.isArray(values)) {
    return [];
  }
  return values.map((value) => `<span class="chip chip--${kind}">${escapeHtml(value)}</span>`);
}

function renderPublished(catalog) {
  const parts = [catalog.platform, catalog.published_date].filter(Boolean);
  if (!parts.length) {
    return "";
  }
  return `Published: ${parts.map(escapeHtml).join(", ")}`;
}

function formatList(values) {
  return Array.isArray(values) ? values.join(", ") : values;
}

function splitValues(value) {
  if (Array.isArray(value)) {
    return value.filter(Boolean);
  }
  if (!value) {
    return [];
  }
  return String(value)
    .split(/;|,/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function formatDateRange(from, to) {
  if (!from && !to) {
    return "";
  }
  if (from && to && from !== to) {
    return `${formatDate(from)} - ${formatDate(to)}`;
  }
  return formatDate(from || to);
}

function formatDate(value) {
  if (!value) {
    return "";
  }
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}

async function copyItemUrl(itemId) {
  const item = state.items.get(itemId);
  const url = item?.url || item?.catalog?.link;
  if (!url || !navigator.clipboard) {
    return;
  }
  await navigator.clipboard.writeText(url);
}

function normalizeUrl(url) {
  return String(url || "").replace(/\/$/, "");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}
