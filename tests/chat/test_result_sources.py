import json
from types import SimpleNamespace
from uuid import uuid4

from langchain_core.messages import ToolMessage

from archivechat.chat.results import extract_read_items, item_summary
from archivechat.models import ArticleContent, Item


def test_extract_read_items_from_tool_messages():
    item = Item(
        id=uuid4(),
        contents=[
            ArticleContent(
                id=uuid4(),
                url='https://example.org/article',
                title='Article title',
                text_body='Body text',
            )
        ],
    )
    messages = [
        ToolMessage(content=json.dumps(item.model_dump(mode='json')), tool_call_id='read-1', name='read_item'),
        ToolMessage(content='[]', tool_call_id='search-1', name='search_items'),
    ]

    assert extract_read_items(messages) == [item.model_dump(mode='json')]


def test_extract_read_items_handles_responses_api_tool_content_shape():
    item = Item(
        id=uuid4(),
        contents=[
            ArticleContent(
                id=uuid4(),
                url='https://example.org/article',
                title='Article title',
                text_body='Body text',
            )
        ],
    )
    message = SimpleNamespace(
        name='read_item',
        content=[
            {
                'type': 'text',
                'text': json.dumps(item.model_dump(mode='json')),
            }
        ],
    )

    assert extract_read_items([message]) == [item.model_dump(mode='json')]


def test_item_summary_uses_catalog_when_present(guardian_item_path):
    item = Item.model_validate_json(guardian_item_path.read_text()).model_dump(mode='json')

    summary = item_summary(item)

    assert summary['item_id'] == item['id']
    assert summary['title'] == item['catalog_record']['english_title']
    assert summary['url'] == item['catalog_record']['link']
    assert 'theme_tags' in summary['catalog']
