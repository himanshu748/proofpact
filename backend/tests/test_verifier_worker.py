import subprocess
from backend import verifier
from backend.domain import create_project, seed_proposals

def test_worker_timeout_blocks_every_check_and_cleans_process_group(monkeypatch):
    p = create_project('Timeout test', 'Synthetic browser timeout', fixture=True)
    seed_proposals(p)
    p['delivery'] = {'url': 'http://127.0.0.1:8000/fixture/fixed'}
    cleaned = []
    class Child:
        pid = 12345
        def communicate(self, value, timeout):
            assert timeout == 90
            raise subprocess.TimeoutExpired('worker', timeout)
        def wait(self): cleaned.append('wait')
    monkeypatch.setattr(verifier.subprocess, 'Popen', lambda *a, **kw: Child())
    monkeypatch.setattr(verifier.os, 'killpg', lambda pid, sig: cleaned.append(pid))
    run = verifier.run_verification(p)
    assert run['agreement_hash'] == p['hash']
    assert len(run['results']) == 5
    assert all(r['status'] == 'blocked' and r['evidence'] == [] for r in run['results'])
    assert cleaned == [12345, 'wait']
