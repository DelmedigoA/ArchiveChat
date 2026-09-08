from pathlib import Path


STATIC_APP = Path('src/archivechat/web/static/app.js')
STATIC_CSS = Path('src/archivechat/web/static/styles.css')


def test_archive_markdown_links_render_as_clickable_inline_citations():
    app_js = STATIC_APP.read_text()

    assert 'class="citation-link"' in app_js
    assert 'data-item-id' in app_js
    assert '[${number}]' in app_js
    assert 'citationNumbers' in app_js


def test_citation_links_are_styled():
    styles = STATIC_CSS.read_text()

    assert '.citation-link' in styles
    assert 'border-radius: 999px' in styles


def test_answer_renderer_supports_basic_inline_markdown():
    app_js = STATIC_APP.read_text()

    assert 'function renderInlineMarkdown' in app_js
    assert '<strong>$1</strong>' in app_js
    assert '<em>$2</em>' in app_js


def test_bearing_witness_fonts_are_loaded():
    index = Path('src/archivechat/web/static/index.html').read_text()
    styles = STATIC_CSS.read_text()

    assert 'family=Figtree' in index
    assert 'IBM+Plex+Sans' in index
    assert '--font-heading: "IBM Plex Sans"' in styles
    assert '--font-body: "Figtree"' in styles


def test_enter_submits_and_shift_enter_keeps_multiline_input():
    app_js = STATIC_APP.read_text()

    assert 'event.key === "Enter" && !event.shiftKey' in app_js
    assert 'event.preventDefault()' in app_js
    assert 'els.composer.requestSubmit()' in app_js


def test_opening_sentence_is_randomized_on_page_load():
    app_js = STATIC_APP.read_text()

    assert 'const openingSentences = [' in app_js
    assert 'Math.floor(Math.random() * openingSentences.length)' in app_js
    assert 'What would you like to understand from the archive?' not in app_js
    assert 'Ask a question about the archive, the document, or the evidence.' in app_js
    assert 'Start with a question about what happened, how it was documented, or what the sources show.' in app_js



def test_static_ui_uses_streaming_chat_endpoint_and_statuses():
    app_js = STATIC_APP.read_text()

    assert '/api/chat/stream' in app_js
    assert 'Accept: "text/event-stream"' in app_js
    assert 'function readChatStream' in app_js
    assert 'function parseServerSentEvent' in app_js
    assert 'function handleStreamEvent' in app_js
    assert 'Working…' in app_js
    assert 'function updateStreamingStatus' in app_js
    assert 'function renderStreamingAnswer' in app_js
    assert 'function addStreamItem' in app_js
    assert 'message-status' in app_js
    assert 'els.status.textContent = "Ready"' in app_js
    assert 'els.status.dataset.state' not in app_js
    assert 'Thinking' not in app_js
    assert 'Reading your question' not in app_js



def test_streaming_message_has_active_indicator():
    styles = STATIC_CSS.read_text()

    assert '.message-status::before' in styles
    assert '.status-pill[data-state="busy"]::before' not in styles
    assert '@keyframes status-pulse' in styles



def test_streaming_status_renders_inside_message_not_header():
    app_js = STATIC_APP.read_text()

    assert 'updateStreamingStatus(streamState, event.data.message || "Working…")' in app_js
    assert 'node.innerHTML = `<span class="message-status">${escapeHtml(message)}</span>`;' in app_js
    assert 'streamState.hasAnswerText' in app_js
    assert 'els.status.textContent = event.data.message' not in app_js



def test_streaming_answer_rerenders_markdown_live():
    app_js = STATIC_APP.read_text()

    assert 'streamState.rawAnswer += text' in app_js
    assert 'renderAnswer(streamState.rawAnswer, streamState.items)' in app_js
    assert 'event.event === "item"' in app_js
    assert 'addStreamItem(streamState, event.data.item)' in app_js



def test_status_updates_do_not_scroll_the_page():
    app_js = STATIC_APP.read_text()
    status_function = app_js.split('function updateStreamingStatus', 1)[1].split('function addStreamItem', 1)[0]

    assert 'scrollIntoView' not in status_function
