// Chat requests, streamed events, and message DOM updates.
import { state, els } from "./state.js";
import { escapeHtml, isHebrewDominant, renderAnswer } from "./formatting.js";

async function ask(question) {
  setBusy(true);
  const streamState = createStreamState();
  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ question }),
    });
    if (!response.ok || !response.body) {
      const payload = await response.json().catch(() => ({}));
      streamState.node.remove();
      appendMessage("assistant", payload.detail || payload.error || "Chat failed.");
      return;
    }
    await readChatStream(response.body, streamState);
  } catch (error) {
    streamState.node.remove();
    appendMessage("assistant", `Request failed: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

function setBusy(value) {
  state.busy = value;
  els.status.textContent = "Ready";
  els.composer.querySelector("button").disabled = value;
}

async function resetConversation() {
  if (state.busy) {
    return;
  }
  els.resetConversation.disabled = true;
  try {
    const response = await fetch("/api/chat/reset", { method: "POST" });
    if (!response.ok) {
      throw new Error("The conversation could not be reset.");
    }
    els.messages.replaceChildren();
    appendMessage("assistant", "Ask a question about the archive, the document, or the evidence.");
  } catch (error) {
    appendMessage("assistant", error.message || "The conversation could not be reset.");
  } finally {
    els.resetConversation.disabled = false;
  }
}

async function readChatStream(body, streamState) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const eventText of events) {
      handleStreamEvent(parseServerSentEvent(eventText), streamState);
    }
  }
  if (buffer.trim()) {
    handleStreamEvent(parseServerSentEvent(buffer), streamState);
  }
}

function parseServerSentEvent(text) {
  const event = { event: "message", data: {} };
  const dataLines = [];
  for (const line of text.split("\n")) {
    if (line.startsWith("event: ")) {
      event.event = line.slice(7).trim();
    } else if (line.startsWith("data: ")) {
      dataLines.push(line.slice(6));
    }
  }
  if (dataLines.length) {
    event.data = JSON.parse(dataLines.join("\n"));
  }
  return event;
}

function handleStreamEvent(event, streamState) {
  if (event.event === "status") {
    updateStreamingStatus(streamState, event.data.message || "Reviewing material…");
  } else if (event.event === "item") {
    addStreamItem(streamState, event.data.item);
  } else if (event.event === "delta") {
    appendStreamingText(streamState, event.data.text || "");
  } else if (event.event === "final") {
    for (const item of event.data.items || []) {
      addStreamItem(streamState, item);
    }
    replaceWithAssistantMessage(streamState, event.data.answer || "");
  } else if (event.event === "error") {
    streamState.node.remove();
    appendMessage("assistant", event.data.detail || event.data.message || "Chat failed.");
  }
}

function appendMessage(role, text) {
  const node = document.createElement("article");
  node.className = `message message--${role}`;
  setMessageDirection(node, text);
  node.textContent = text;
  els.messages.appendChild(node);
  node.scrollIntoView({ block: "end" });
}

function appendAssistantMessage(answer, items) {
  const node = document.createElement("article");
  node.className = "message message--assistant";
  setMessageDirection(node, answer);
  node.innerHTML = renderAnswer(answer, items);
  els.messages.appendChild(node);
  node.scrollIntoView({ block: "end" });
}

function createStreamState() {
  const node = document.createElement("article");
  node.className = "message message--assistant message--streaming";
  const streamState = {
    node,
    rawAnswer: "",
    items: [],
    itemIds: new Set(),
    hasAnswerText: false,
  };
  updateStreamingStatus(streamState, "Reviewing material…");
  els.messages.appendChild(node);
  node.scrollIntoView({ block: "end" });
  return streamState;
}

function updateStreamingStatus(streamState, message) {
  if (streamState.hasAnswerText) {
    return;
  }
  streamState.node.innerHTML = `<span class="message-status">${escapeHtml(message)}</span>`;
}

function addStreamItem(streamState, item) {
  if (!item || !item.item_id || streamState.itemIds.has(item.item_id)) {
    return;
  }
  streamState.itemIds.add(item.item_id);
  streamState.items.push(item);
  state.items.set(item.item_id, item);
  renderStreamingAnswer(streamState);
}

function appendStreamingText(streamState, text) {
  if (!text) {
    return;
  }
  streamState.hasAnswerText = true;
  streamState.rawAnswer += text;
  renderStreamingAnswer(streamState);
}

function renderStreamingAnswer(streamState) {
  if (!streamState.hasAnswerText) {
    return;
  }
  setMessageDirection(streamState.node, streamState.rawAnswer);
  streamState.node.innerHTML = renderAnswer(streamState.rawAnswer, streamState.items);
  streamState.node.scrollIntoView({ block: "end" });
}

function replaceWithAssistantMessage(streamState, answer) {
  streamState.node.classList.remove("message--streaming");
  streamState.rawAnswer = answer;
  streamState.hasAnswerText = true;
  renderStreamingAnswer(streamState);
}

function setMessageDirection(node, text) {
  const isRtl = isHebrewDominant(text);
  node.dir = isRtl ? "rtl" : "ltr";
  node.classList.toggle("message--rtl", isRtl);
}

export { ask, appendMessage, appendAssistantMessage, readChatStream, parseServerSentEvent, resetConversation };
