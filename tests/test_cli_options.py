"""Configuration precedence shared by both entry points."""

import pytest

from archivechat.cli_options import parse_chat_options


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    import os

    for key in os.environ:
        if key.startswith('ARCHIVECHAT_'):
            monkeypatch.delenv(key)
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')


@pytest.mark.parametrize('web', [False, True])
def test_cli_overrides_yaml_which_overrides_environment(tmp_path, monkeypatch, web):
    config = tmp_path / 'config.yaml'
    config.write_text('model: yaml-model\nsearch-limit: 4\nverbosity: high\n')
    monkeypatch.setenv('ARCHIVECHAT_MODEL', 'env-model')
    monkeypatch.setenv('ARCHIVECHAT_SEARCH_LIMIT', '8')
    monkeypatch.setenv('ARCHIVECHAT_REASONING_EFFORT', 'medium')
    monkeypatch.setattr('sys.argv', ['archivechat', '--config', str(config), '--model', 'cli-model'])

    args = parse_chat_options('test', web=web)

    assert args.model == 'cli-model'
    assert args.search_limit == 4
    assert args.verbosity == 'high'
    assert args.reasoning_effort == 'medium'


@pytest.mark.parametrize('web', [False, True])
def test_environment_true_still_enables_switches_disabled_in_yaml(tmp_path, monkeypatch, web):
    config = tmp_path / 'config.yaml'
    config.write_text('semantic-search: false\nweb-tools: false\ninclude-document: false\n')
    for name in ('SEMANTIC_SEARCH', 'WEB_TOOLS', 'INCLUDE_DOCUMENT'):
        monkeypatch.setenv(f'ARCHIVECHAT_{name}', 'true')
    monkeypatch.setattr('sys.argv', ['archivechat', '--config', str(config)])

    args = parse_chat_options('test', web=web)

    assert args.semantic_search is True
    assert args.web_tools is True
    assert args.include_document is True


def test_web_retains_pdf_and_port_defaults(monkeypatch):
    from archivechat.web.app import DOCUMENT_PDF_PATH, DOCUMENT_PDF_ROUTE

    monkeypatch.setattr('sys.argv', ['archivechat', '--port', '0'])
    args = parse_chat_options('test', web=True)

    assert args.host == '127.0.0.1'
    assert args.port == 8765
    assert args.document_pdf_url == DOCUMENT_PDF_ROUTE
    assert args.document_pdf_path == DOCUMENT_PDF_PATH


@pytest.mark.parametrize('web', [False, True])
def test_missing_api_key_is_rejected_before_runtime_setup(monkeypatch, capsys, web):
    monkeypatch.delenv('OPENAI_API_KEY')
    monkeypatch.setattr('sys.argv', ['archivechat'])

    with pytest.raises(SystemExit) as exc:
        parse_chat_options('test', web=web)

    assert exc.value.code == 2
    assert 'Set OPENAI_API_KEY in your environment or .env' in capsys.readouterr().err
