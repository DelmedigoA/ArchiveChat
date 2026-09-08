import json

from archivechat.chat.faqs import FaqCollection


def test_faq_search_returns_questions_without_answers(tmp_path):
    faq_file = tmp_path / 'faq.json'
    faq_file.write_text(json.dumps([
        {'id': 'faq-1', 'question': 'Who manages the project?', 'answer': 'The answer mentions leadership.', 'url': 'https://example.org/faq'},
        {'id': 'faq-2', 'question': 'How is content organized?', 'answer': 'Timeline and geography.', 'url': 'https://example.org/faq'},
    ]))

    faqs = FaqCollection(faq_file)
    hits = faqs.search('manages project')

    assert hits == [{
        'faq_id': 'faq-1',
        'question': 'Who manages the project?',
        'url': 'https://example.org/faq',
        'score': hits[0]['score'],
    }]
    assert 'answer' not in hits[0]


def test_faq_read_returns_full_answer(tmp_path):
    faq_file = tmp_path / 'faq.json'
    faq_file.write_text(json.dumps([
        {'id': 'faq-1', 'question': 'Who manages the project?', 'answer': 'The full answer.', 'url': 'https://example.org/faq'},
    ]))

    faqs = FaqCollection(faq_file)

    assert faqs.read('faq-1')['answer'] == 'The full answer.'
    assert faqs.read('missing') == {'error': 'Unknown FAQ ID'}


def test_bearing_witness_faq_data_is_available():
    faqs = FaqCollection()

    hit = faqs.search('reliability verification uncertainty')[0]
    answer = faqs.read(hit['faq_id'])

    assert hit['question'] == 'How do you ensure the reliability of the information?'
    assert 'verification' in answer['answer']
