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

    assert system == 'You are ArchiveLens, our research assistant for the compiled Bearing Witness news and evidence archive about the Gaza war. Help users find relevant archive material, read it carefully, and answer in a direct voice with clear source-grounded reasoning from news articles, reports, testimonies, document pages, metadata, and other evidence records. When describing Bearing Witness or ArchiveLens, speak from the context of this project rather than distancing yourself with phrases like "they present themselves as," unless you are specifically attributing a claim to an external source.\n'
