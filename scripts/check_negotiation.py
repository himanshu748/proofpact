"""Real provider smoke test using synthetic briefs, with no private output."""
import sys
import time
from backend.agents import negotiate
from backend.domain import create_project, seed_proposals, digest

p = create_project('Advocate smoke test', 'Build a small admin dashboard.', fixture=True)
seed_proposals(p)
client = {'private_limit_minor': 800000, 'opening_minor': 500000, 'deadline': '2026-09-23', 'notes': 'OTP is essential.'}
builder = {'private_limit_minor': 650000, 'opening_minor': 800000, 'deadline': '2026-09-21', 'notes': 'Payments excluded.'}
started = time.monotonic()
mode = sys.argv[1] if len(sys.argv) > 1 else 'modal'
negotiate(p, client, builder, mode)
assert p['state'] == 'AWAITING_APPROVAL', p['state']
assert p['proposals'][-1]['source'] == mode
assert p['current']['included'] == p['requirements']
assert p['approvals'] == {}
assert p['hash'] == digest(p['current'])
assert builder['private_limit_minor'] < p['current']['price_minor'] < client['private_limit_minor']
print({'provider': mode, 'state': p['state'], 'scope_count': len(p['current']['included']), 'human_approvals': 0, 'seconds': round(time.monotonic() - started, 1)})
