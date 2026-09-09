from archivechat.chat.prompts import PROMPT_DIR, load_chat_prompt


def test_chat_prompt_loads_system_and_instructions(tmp_path):
    prompt_dir = tmp_path / 'prompts'
    prompt_dir.mkdir()
    (prompt_dir / 'system.md').write_text('System role.\n')
    (prompt_dir / 'instructions.md').write_text('\nRead full items.\n')

    assert load_chat_prompt(prompt_dir) == 'System role.\n\nRead full items.'


def test_chat_prompt_rejects_missing_files(tmp_path):
    prompt_dir = tmp_path / 'prompts'
    prompt_dir.mkdir()
    (prompt_dir / 'system.md').write_text('System role.\n')

    import pytest

    with pytest.raises(FileNotFoundError):
        load_chat_prompt(prompt_dir)


def test_default_chat_prompt_describes_archive_role():
    prompt = load_chat_prompt(PROMPT_DIR)

    assert 'ArchiveLens' in prompt
    assert 'Gaza war' in prompt
    assert 'Bearing Witness' in prompt
    assert 'read the full items' in prompt
    assert 'Lee Mordechai' in prompt
    assert 'use the dedicated project metadata tools first' in prompt
    assert 'sitemap/crawl inventory' in prompt
    assert 'Put this recommendation at the end of the answer' in prompt
    assert 'If no relevant website section is identified in metadata, omit the recommendation' in prompt
    assert 'Do not hardcode one project' in prompt
    assert 'Use a Markdown link with the section title when metadata provides a URL' in prompt


def test_default_system_prompt_identifies_archivelens_role():
    system = (PROMPT_DIR / 'system.md').read_text()

    assert system.startswith('You are ArchiveLens, our research assistant for Bearing Witness archive about the Gaza war.')
    assert 'Never mention internal system concepts' in system
    assert 'I couldn\'t verify a public link.' in system
    assert 'Use a serious, restrained, professional tone.' in system
    assert 'Do not sound cheerful, playful,' in system
    assert 'overly conversational.' in system
    assert 'acknowledge' in system
    assert 'uncertainty explicitly.' in system
