# Connect an agent to ProofPact

ProofPact exposes an **A2A 1.0 JSON-RPC binding** for the existing negotiation and delivery services. External agents can discover it, request work, and retrieve persistent task artifacts. Internal advocates still use the configured Modal or Bedrock adapter; this does not claim that their inference calls themselves use A2A.

## Connect

1. Open a pact in the workspace and choose **Agents**.
2. Choose read-only access (default), or explicitly allow work for the currently selected demo participant.
3. Create a key and copy it into your agent's secret settings. The key is shown only once, lasts at most one hour, and is bound to that pact and participant role. Switching the demo role does not change an existing key's authority. Replacing it invalidates the previous key for that role.
4. Discover `GET /.well-known/agent-card.json` (also `/api/a2a/agent-card`). Its supported interface points to `POST /api/a2a`.
5. Send `Authorization: Bearer <key>`, `A2A-Version: 1.0`, and `Content-Type: application/json`.

Never put keys in URLs, source control, screenshots, or agent prompts. The server stores only a digest lookup. The browser keeps the new key in component memory, not local storage. Revocation blocks future requests; already-running work may finish. Expired or revoked keys cannot retrieve prior tasks.

## Message example

```json
{
  "jsonrpc": "2.0",
  "id": "request-1",
  "method": "SendMessage",
  "params": {
    "message": {
      "messageId": "unique-message-1",
      "role": "ROLE_USER",
      "parts": [{"data": {"action": "get_pact"}}]
    }
  }
}
```

`contextId` is optional; if supplied, it must equal the pact ID bound to the key. Each response contains `result.task`, including a task ID, state, and structured artifact. `TASK_STATE_COMPLETED` means the requested operation finished; it does **not** mean delivery passed or the agreement was approved. Inspect the artifact's pact state and criterion results.

A `get_pact` artifact returns the active agreement, hash, approvals, pending amendment, submitted delivery and latest verification summary. It excludes private briefs, payment records and screenshot evidence. Evidence remains behind the workspace session.

## Commands

Use exactly one JSON `data` part. Work commands require `expected_hash` from a fresh `get_pact` response (`"unversioned"` before the first proposal).

| action | Additional fields | Permission |
| --- | --- | --- |
| `get_pact` | None | All keys |
| `negotiate` | `expected_hash`, `mode`: `demo`, `modal`, or `bedrock` | Work-enabled key |
| `check_change` | `expected_hash`, `text` | Work-enabled client key |
| `submit_delivery` | `expected_hash`, `url`, optional `notes` | Work-enabled builder key |
| `verify_delivery` | `expected_hash` | Work-enabled key |

`demo` negotiation is explicitly a deterministic sample. Provider modes call the existing private advocates and preserve their validation and failure behavior. All original workflow guards, URL restrictions, quotas and optimistic writes still apply. An agent cannot supply a different pact ID, role or private brief through this interface.

There are no commands for agreement/amendment approval, manual criterion acceptance, receipt publication, funding, disputes, refunds or payment release. These remain outside agent authority. Pending scope additions do not replace the agreed version until both humans approve in the workspace.

## Task retrieval and retries

- `GetTask`: `params: {"id":"task-id", "historyLength":0}` returns the task.
- `ListTasks`: accepts `contextId`, `status`, `pageSize` (1–100), `pageToken`, `historyLength`, `statusTimestampAfter`, and `includeArtifacts`. Lists only tasks created by the current key. Artifacts are omitted by default. Follow `nextPageToken` until empty.
- Retrying the same message ID and identical message returns the recorded result without executing again. Reusing an ID with changed content is rejected.
- Work is reserved durably before execution. If a process is interrupted, the task may remain working and requires operator reconciliation; a retry does not blindly rerun the operation. Use `GetTask` and inspect the pact before taking further action.
- A failed task is terminal. After resolving the cause and refreshing the pact, submit a new message ID.
- `CancelTask` returns `TaskNotCancelableError`: blocking work cannot safely be interrupted. No cancellation is falsely reported.

The binding is intentionally blocking to match the current buffered Lambda runtime. Streaming, push notifications, immediate background execution, extended cards and multi-turn task continuation are unsupported and return explicit protocol errors. It is not a complete implementation of every optional A2A capability. A missing version header is treated as 0.3 and rejected rather than silently changing wire formats.

## Validation and current limits

Run `.venv/bin/python -m pytest backend/tests -q` for protocol, authorization, isolation, replay, expiry, role and workflow tests. Run `.venv/bin/python scripts/check_a2a.py http://127.0.0.1:8000` for a synthetic HTTP round trip including sample negotiation, ordinary human approval API calls, real broken/fixed Chromium verification, task retrieval, replay and key revocation. The script never prints keys and stops with manual review still required. It can also target the hosted origin.

The connection panel's **Test connection** button sends a real read-only A2A message and displays the returned task. Demo identity remains synthetic and switchable. Real accounts use Cognito email verification, fixed roles and pact membership. Email verification does not establish legal identity. See [accounts](accounts.md) for setup and operating limits. Razorpay Route sandbox access is separately pending support; A2A cannot enable payments or bypass that prerequisite.

Protocol reference: [A2A 1.0 specification](https://a2a-protocol.org/v1.0.0/specification/), [versioned canonical schema](https://github.com/a2aproject/A2A/blob/v1.0.0/specification/a2a.proto).
