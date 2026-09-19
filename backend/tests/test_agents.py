import json
import pytest
from backend.agents import offer_prompt, parse_offer, validate_private_offer, negotiate
from backend.domain import create_project

PUBLIC = {'requirements': ['Login', 'Analytics', 'CSV', 'OTP']}
PRIVATE = {'private_limit_minor': 800000, 'opening_minor': 500000, 'deadline': '2026-09-23', 'notes': 'private note', '_rev': 5}

def raw(**changes):
    return json.dumps({'decision': 'counter', 'price_minor': 750000, 'deadline': '2026-09-21', 'scope_ids': [0, 1, 2, 3], **changes})

def test_prompt_numbers_scope_and_whitelists_private_context():
    system, payload = offer_prompt('client', PUBLIC, PRIVATE)
    context = json.loads(payload)
    assert context['shared']['required_scope_ids'] == [0, 1, 2, 3]
    assert context['shared']['requirements'][-1] == {'id': 3, 'requirement': 'OTP'}
    assert '_rev' not in context['your_private_brief']
    assert 'private note' not in json.dumps(context['shared'])
    assert 'less than 800000' in system

@pytest.mark.parametrize('changes', [
    {'scope_ids': [0, 1, 2]}, {'scope_ids': [0, 1, 2, 3, 3]},
    {'scope_ids': [0, 1, 2, 4]}, {'notes': 'secret'}, {'price_minor': '750000'},
])
def test_invalid_or_private_model_output_rejected(changes):
    with pytest.raises(ValueError): parse_offer(raw(**changes), PUBLIC)

@pytest.mark.parametrize('changes', [{'price_minor': 850000}, {'price_minor': 800000}, {'deadline': '2026-09-23'}])
def test_client_private_constraints_enforced(changes):
    with pytest.raises(ValueError): validate_private_offer(parse_offer(raw(**changes), PUBLIC), 'client', PRIVATE)

def test_bounded_repair_does_not_share_private_context(monkeypatch):
    calls = []
    class Fake:
        def offer(self, role, public, private):
            calls.append((role, dict(public), dict(private)))
            if len(calls) == 1: raise ValueError('raw private model response')
            return parse_offer(raw(), PUBLIC)
    monkeypatch.setattr('backend.agents.ModalAgents', Fake)
    p = create_project('Test', 'Test scope', requirements=PUBLIC['requirements'])
    builder = {**PRIVATE, 'private_limit_minor': 650000, 'deadline': '2026-09-21', 'notes': 'builder secret'}
    negotiate(p, PRIVATE, builder, 'modal')
    assert p['state'] == 'AWAITING_APPROVAL'
    assert p['approvals'] == {}
    assert len(calls) == 3
    assert 'validation_feedback' in calls[1][1]
    assert 'builder secret' not in json.dumps(calls[-1])
    assert 'raw private model response' not in json.dumps(calls)
    assert 'private_limit_minor' not in json.dumps(p)
