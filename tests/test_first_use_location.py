from expkm.onboarding import setup_status
from expkm.store import Store


def test_first_use_explicitly_requires_concrete_output_location(tmp_path):
    value=setup_status(Store(tmp_path/'private'),'synthetic','sync','report')
    questions=[q for q in value['questions'] if q['id']=='save_location']
    assert len(questions)==1, 'Choosing Feishu or Markdown must also ask for its concrete location'
    assert 'options' not in questions[0], 'A document URL or filename needs a free-text answer'
    assert questions[0]['required'] is True
    assert value['status']=='needs_setup'
