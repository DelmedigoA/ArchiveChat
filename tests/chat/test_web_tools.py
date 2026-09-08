from archivechat.chat.web_tools import make_web_tools


class FakeResponse:
    def __init__(self, data):
        self._data = data
        self.text = data if isinstance(data, str) else ''

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


class FakeHttpClient:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers, timeout))
        if 'api.php' in url and params.get('list') == 'search':
            return FakeResponse({'query': {'search': [
                {'title': 'Gaza War', 'snippet': 'Article snippet'},
            ]}})
        if 'api.php' in url and params.get('prop') == 'extracts':
            return FakeResponse({'query': {'pages': {
                '1': {'title': 'Gaza War', 'extract': 'Summary text.'},
            }}})
        return FakeResponse('<html><body><main>Page text</main></body></html>')


class FailingHttpClient:
    def get(self, url, params=None, headers=None, timeout=None):
        return FailingResponse()


class FailingResponse:
    text = ''

    def raise_for_status(self):
        import httpx

        request = httpx.Request('GET', 'https://en.wikipedia.org/w/api.php')
        response = httpx.Response(403, request=request)
        raise httpx.HTTPStatusError('403 Forbidden', request=request, response=response)


def test_wikipedia_search_tool_uses_api():
    client = FakeHttpClient()
    tools = {tool.name: tool for tool in make_web_tools(client)}

    result = tools['search_wikipedia'].invoke({'query': 'Gaza war', 'limit': 1})

    assert result == [{'title': 'Gaza War', 'snippet': 'Article snippet', 'url': 'https://en.wikipedia.org/wiki/Gaza_War'}]
    assert client.calls[0][2]['User-Agent'].startswith('ArchiveLens/')


def test_wikipedia_summary_tool_uses_api():
    client = FakeHttpClient()
    tools = {tool.name: tool for tool in make_web_tools(client)}

    result = tools['read_wikipedia_summary'].invoke({'title': 'Gaza War'})

    assert result == {'title': 'Gaza War', 'summary': 'Summary text.', 'url': 'https://en.wikipedia.org/wiki/Gaza_War'}


def test_fetch_web_page_text_rejects_non_http_urls():
    tools = {tool.name: tool for tool in make_web_tools(FakeHttpClient())}

    assert tools['fetch_web_page_text'].invoke({'url': 'file:///etc/passwd'}) == {'error': 'Only http and https URLs are supported'}


def test_web_tool_http_errors_return_structured_error():
    tools = {tool.name: tool for tool in make_web_tools(FailingHttpClient())}

    result = tools['search_wikipedia'].invoke({'query': 'Stacy Gilbert'})

    assert result['error'] == 'Wikipedia search failed'
    assert '403' in result['detail']
