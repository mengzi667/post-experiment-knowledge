"""Synthetic sequential native-card contract, including interrupted host replies."""
import pytest
from expkm.store import Store
from expkm.cli import parser,run
from expkm.common import write_json
from test_intake import preferences,confirm,request

def questions():
    return [{'id':'requirements','title':'Confirm synthetic scope','options':['Confirm','Revise']},
            {'id':'template','title':'Choose template','options':['Provide','Reuse','Codex recommends']},
            {'id':'locations','title':'Confirm exact synthetic save locations','options':['Confirm','Revise']}]

def start(tmp_path):
    from expkm.cards import Cards
    store=Store(tmp_path/'private');preferences(store)
    cards=Cards(store);state=cards.start('synthetic-request-one',questions())
    return store,cards,state['session']

def answer(cards,session,qid,text):
    return cards.answer(session,{'question_id':qid,'answer':text,'response_reference':'synthetic-host-reply-'+qid})

def test_only_one_card_is_pending_and_partial_reply_does_not_lose_the_rest(tmp_path):
    _,cards,s=start(tmp_path)
    first=cards.next(s);assert len(first['questions'])==1 and first['question_id']=='requirements'
    assert cards.next(s)==first
    answer(cards,s,'requirements','Confirm')
    assert cards.next(s)['question_id']=='template'
    assert cards.next(s)['remaining']==2
    answer(cards,s,'template','Reuse');assert cards.next(s)['question_id']=='locations'
    answer(cards,s,'locations','Confirm');assert cards.next(s)['status']=='complete'

def test_no_default_answer_or_out_of_order_reply_advances_queue(tmp_path):
    _,cards,s=start(tmp_path)
    with pytest.raises(ValueError):answer(cards,s,'template','Reuse')
    with pytest.raises(ValueError):answer(cards,s,'requirements','')
    assert cards.next(s)['question_id']=='requirements'

def test_replayed_answer_is_idempotent_but_conflicting_answer_stops(tmp_path):
    _,cards,s=start(tmp_path);answer(cards,s,'requirements','Confirm')
    answer(cards,s,'requirements','Confirm');assert cards.next(s)['question_id']=='template'
    with pytest.raises(ValueError):answer(cards,s,'requirements','Revise')

def test_unanswered_cards_block_intake_even_if_preferences_already_exist(tmp_path):
    store,cards,s=start(tmp_path)
    with pytest.raises(ValueError):confirm(store)
    answer(cards,s,'requirements','Confirm');answer(cards,s,'template','Reuse')
    with pytest.raises(ValueError):confirm(store)
    answer(cards,s,'locations','Confirm');assert confirm(store)['version']
    with pytest.raises(ValueError):cards.append(s,[{'id':'extra','title':'Late unreviewed change'}])

def test_resume_and_append_summary_then_close_are_preserved(tmp_path):
    from expkm.cards import Cards
    store,cards,s=start(tmp_path)
    for q,text in [('requirements','Confirm'),('template','Reuse'),('locations','Confirm')]:answer(cards,s,q,text)
    cards=Cards(Store(store.root));cards.append(s,[{'id':'summary','title':'Review the exact final request','options':['Confirm','Revise']}])
    assert cards.next(s)['question_id']=='summary'
    with pytest.raises(ValueError):cards.close(s)
    answer(cards,s,'summary','Confirm');cards.close(s)
    assert cards.status(s)['closed']
    with pytest.raises(ValueError):cards.append(s,[{'id':'new','title':'New task'}])

def test_cli_returns_native_tool_payload_without_internal_ids(tmp_path):
    store,_,s=start(tmp_path)
    value=run(parser().parse_args(['--store',str(store.root),'cards','next','--session',s]))
    assert set(value['questions'][0])=={'title','options'}
    assert len(value['questions'])==1 and value['execution_allowed'] is False

def test_duplicate_or_changed_question_identity_is_rejected(tmp_path):
    _,cards,s=start(tmp_path)
    with pytest.raises(ValueError):cards.start('synthetic-request-one',[{'id':'requirements','title':'Changed scope'}])
    with pytest.raises(ValueError):cards.append(s,[{'id':'requirements','title':'Duplicate'}])

def test_setup_instructs_host_to_render_exactly_one_question(tmp_path):
    from expkm.onboarding import setup_status
    value=setup_status(Store(tmp_path/'private'),'quality')
    assert value['card_protocol']['questions_per_call']==1
    assert value['card_protocol']['advance_only_after_actual_reply'] is True
    assert value['card_protocol']['resume_pending_on_partial_reply'] is True
