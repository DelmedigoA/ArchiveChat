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


def test_bearing_witness_page_citations_are_deterministically_rendered_as_buttons():
    app_js = STATIC_APP.read_text()

    assert 'function renderDocumentCitations' in app_js
    assert 'Bearing\\s+Witness\\s*,\\s*p{1,2}' in app_js
    assert 'data-document-page' in app_js
    assert 'lastPage < firstPage' in app_js
    assert 'document-citation-link' in app_js


def test_document_viewer_is_lazy_loaded_and_opens_the_citation_first_page():
    app_js = STATIC_APP.read_text()

    assert 'await openDocumentViewer(Number(documentCitation.dataset.documentPage))' in app_js
    assert 'fetch("/api/document-config")' in app_js
    assert 'import("/static/vendor/pdfjs/pdf.mjs")' in app_js
    assert 'pdfjs.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.mjs"' in app_js
    assert 'rangeChunkSize: 65536' in app_js
    assert 'await showDocumentPage(page)' in app_js


def test_document_viewer_has_resizable_accessible_two_pane_workspace():
    index = Path('src/archivechat/web/static/index.html').read_text()
    app_js = STATIC_APP.read_text()
    styles = STATIC_CSS.read_text()

    assert 'role="separator"' in index
    assert 'id="workspace-divider"' in index
    assert 'id="document-close"' in index
    assert 'function beginWorkspaceResize' in app_js
    assert 'sessionStorage.setItem("archivechat:workspace-split"' in app_js
    assert 'function handleDividerKeydown' in app_js
    assert '.workspace--viewer-open' in styles
    assert 'grid-template-columns: minmax(360px, var(--chat-pane-width)) 10px minmax(360px, 1fr)' in styles


def test_pdfjs_runtime_is_self_hosted_with_its_worker_and_license():
    vendor = Path('src/archivechat/web/static/vendor/pdfjs')

    assert (vendor / 'pdf.mjs').is_file()
    assert (vendor / 'pdf.worker.mjs').is_file()
    assert (vendor / 'LICENSE').is_file()


def test_answer_renderer_supports_basic_inline_markdown():
    app_js = STATIC_APP.read_text()

    assert 'function renderInlineMarkdown' in app_js
    assert '<strong>$1</strong>' in app_js
    assert '<em>$2</em>' in app_js


def test_hebrew_dominant_messages_use_rtl_direction():
    app_js = STATIC_APP.read_text()
    styles = STATIC_CSS.read_text()

    assert 'function isHebrewDominant' in app_js
    assert 'hebrewLetters.length > letters.length / 2' in app_js
    assert 'node.dir = isRtl ? "rtl" : "ltr"' in app_js
    assert 'setMessageDirection(node, text)' in app_js
    assert 'setMessageDirection(streamState.node, streamState.rawAnswer)' in app_js
    assert '.message--rtl' in styles
    assert 'direction: rtl' in styles
    assert 'text-align: right' in styles


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
    assert 'Reviewing material…' in app_js
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

    assert 'updateStreamingStatus(streamState, event.data.message || "Reviewing material…")' in app_js
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
