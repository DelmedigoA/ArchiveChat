from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APIError, NotFoundError

from archivelens.chat import __main__ as cli, runtime


@pytest.fixture
def setup_cli(monkeypatch):
    monkeypatch.setattr(cli, 'load_dotenv', lambda: None)
    monkeypatch.delenv('ARCHIVELENS_MODEL', raising=False)
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    model = Mock()
    graph = Mock()
    graph.invoke.return_value = {'messages': [SimpleNamespace(content='Hello')]}
    monkeypatch.setattr(runtime, 'ChatOpenAI', model)
    monkeypatch.setattr(runtime, 'OpenAIEmbeddings', Mock(return_value='embeddings'))
    monkeypatch.setattr(runtime, 'Collection', Mock())
    monkeypatch.setattr(runtime, 'DocumentCollection', Mock(return_value='document_collection'))
    monkeypatch.setattr(runtime, 'ProjectMetadataCollection', Mock(return_value='project_metadata_collection'))
    monkeypatch.setattr(runtime, 'make_web_tools', Mock(return_value=['web_tool']))
    build_graph = Mock(return_value=graph)
    monkeypatch.setattr(runtime, 'build_graph', build_graph)
    return model, graph, build_graph


def test_cli_has_working_default(monkeypatch, setup_cli):
    monkeypatch.setattr('sys.argv', ['archivelens', '--question', 'hi'])
    cli.main()
    assert setup_cli[0].call_args.kwargs['model'] == 'gpt-5'
    assert setup_cli[0].call_args.kwargs['reasoning_effort'] == 'low'
    assert setup_cli[0].call_args.kwargs['verbosity'] == 'low'
    assert setup_cli[0].call_args.kwargs['use_responses_api'] is True


def test_cli_prints_responses_api_text_blocks(monkeypatch, setup_cli, capsys):
    setup_cli[1].invoke.return_value = {'messages': [SimpleNamespace(content=[
        {'type': 'text', 'text': 'Hello from Responses API.', 'annotations': []},
    ])]}
    monkeypatch.setattr('sys.argv', ['archivelens', '--question', 'hi'])
    cli.main()
    out = capsys.readouterr().out
    assert 'ArchiveLens: Hello from Responses API.' in out
    assert "'type': 'text'" not in out


def test_cli_allows_reasoning_effort_override(monkeypatch, setup_cli):
    monkeypatch.setattr('sys.argv', ['archivelens', '--reasoning-effort', 'medium', '--question', 'hi'])
    cli.main()
    assert setup_cli[0].call_args.kwargs['reasoning_effort'] == 'medium'


def test_cli_allows_verbosity_override(monkeypatch, setup_cli):
    monkeypatch.setattr('sys.argv', ['archivelens', '--verbosity', 'medium', '--question', 'hi'])
    cli.main()
    assert setup_cli[0].call_args.kwargs['verbosity'] == 'medium'


def test_cli_omits_reasoning_effort_when_disabled(monkeypatch, setup_cli):
    monkeypatch.setattr('sys.argv', ['archivelens', '--reasoning-effort', 'none', '--question', 'hi'])
    cli.main()
    assert 'reasoning_effort' not in setup_cli[0].call_args.kwargs
    assert setup_cli[0].call_args.kwargs['use_responses_api'] is False


def test_cli_allows_search_limit_override(monkeypatch, setup_cli):
    monkeypatch.setattr('sys.argv', ['archivelens', '--search-limit', '7', '--question', 'hi'])
    cli.main()
    assert setup_cli[2].call_args.kwargs['search_limit'] == 7


def test_cli_passes_project_metadata_collection(monkeypatch, setup_cli):
    monkeypatch.setattr('sys.argv', ['archivelens', '--question', 'hi'])
    cli.main()
    runtime.ProjectMetadataCollection.assert_called_once()
    assert setup_cli[2].call_args.kwargs['project_metadata_collection'] == 'project_metadata_collection'


def test_cli_can_enable_openai_embeddings(monkeypatch, setup_cli):
    monkeypatch.setattr('sys.argv', ['archivelens', '--semantic-search', '--include-document', '--question', 'hi'])
    cli.main()
    runtime.OpenAIEmbeddings.assert_called_once_with(model='text-embedding-3-small', timeout=60, max_retries=1)
    assert runtime.Collection.call_args.kwargs['embeddings'].__class__.__name__ == 'CachedEmbeddings'
    assert runtime.DocumentCollection.call_args.kwargs['embeddings'].__class__.__name__ == 'CachedEmbeddings'


def test_cli_allows_embedding_model_override(monkeypatch, setup_cli):
    monkeypatch.setattr('sys.argv', [
        'archivelens', '--semantic-search', '--embedding-model', 'text-embedding-3-large', '--question', 'hi',
    ])
    cli.main()
    assert runtime.OpenAIEmbeddings.call_args.kwargs['model'] == 'text-embedding-3-large'


def test_cli_can_enable_web_tools(monkeypatch, setup_cli):
    monkeypatch.setattr('sys.argv', ['archivelens', '--web-tools', '--question', 'hi'])
    cli.main()
    runtime.make_web_tools.assert_called_once_with()
    assert setup_cli[2].call_args.kwargs['extra_tools'] == ['web_tool']


def test_cli_rejects_invalid_search_limit(monkeypatch, setup_cli, capsys):
    monkeypatch.setattr('sys.argv', ['archivelens', '--search-limit', '0', '--question', 'hi'])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    setup_cli[0].assert_not_called()
    assert 'search-limit' in capsys.readouterr().err


def test_placeholder_rejected_before_api_call(monkeypatch, setup_cli, capsys):
    monkeypatch.setattr('sys.argv', ['archivelens', '--model', 'YOUR_MODEL', '--question', 'hi'])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    setup_cli[0].assert_not_called()
    assert 'placeholder' in capsys.readouterr().err


def test_unavailable_model_is_readable_error(monkeypatch, setup_cli, capsys):
    monkeypatch.setattr('sys.argv', ['archivelens', '--model', 'missing-model', '--question', 'hi'])
    setup_cli[1].invoke.side_effect = NotFoundError(
        'missing', response=httpx.Response(404, request=httpx.Request('POST', 'https://api.openai.com')),
        body=None,
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    assert 'missing-model' in capsys.readouterr().err


def test_openai_api_error_includes_original_message(monkeypatch, setup_cli, capsys):
    monkeypatch.setattr('sys.argv', ['archivelens', '--question', 'hi'])
    setup_cli[1].invoke.side_effect = APIError(
        'unsupported parameter: reasoning_effort',
        request=httpx.Request('POST', 'https://api.openai.com'),
        body=None,
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert 'OpenAI request failed' in err
    assert 'unsupported parameter: reasoning_effort' in err
