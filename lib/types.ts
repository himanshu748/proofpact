export type Role = "client" | "builder";
export type Criterion = {
  id: string;
  title: string;
  description: string;
  method: string;
  required: boolean;
};
export type Agreement = {
  version: number;
  name: string;
  project_id: string;
  client: string;
  builder: string;
  currency: string;
  price_minor: number;
  deadline: string;
  included: string[];
  excluded: string[];
  criteria: Criterion[];
  change_policy: string;
  risks: string[];
};
export type Evidence = {
  type: "screenshot" | "csv";
  name: string;
  content?: string;
  rows?: number;
  expected_rows?: number;
};
export type Result = {
  criterion_id: string;
  title: string;
  status: "passed" | "failed" | "review" | "blocked";
  observed: string;
  expected: string;
  evidence: Evidence[];
  human_review?: { role: string; at: string; accepted: boolean };
};
export type Run = {
  id: string;
  agreement_hash: string;
  version: number;
  url: string;
  at: string;
  results: Result[];
  engine: string;
  duration_ms: number;
};
export type Approval = { role: Role; hash: string; at: string };
export type Pact = {
  payment?: {
    mode: "test";
    status: string;
    agreement_hash: string;
    amount_minor: number;
    order_id?: string;
    transfer_id?: string;
    checked_at?: string;
    dispute?: { by: string; reason: string; at: string };
  };
  id: string;
  name: string;
  brief: string;
  client: string;
  builder: string;
  fixture: boolean;
  state: string;
  created_at: string;
  requirements: string[];
  current?: Agreement;
  hash?: string;
  approvals: Partial<Record<Role, Approval>>;
  pending_amendment?: {
    agreement: Agreement;
    hash: string;
    base_hash: string;
    approvals: Partial<Record<Role, Approval>>;
  } | null;
  brief_ready: Record<Role, boolean>;
  proposals: {
    agreement: Agreement;
    actor: string;
    rationale: string;
    source: string;
    at: string;
  }[];
  events: {
    id: string;
    actor: string;
    title: string;
    detail: string;
    at: string;
  }[];
  changes: {
    id: string;
    text: string;
    classification: string;
    rationale: string;
    options: string[];
    at: string;
  }[];
  delivery: { url: string; notes: string; at: string; hash: string } | null;
  runs: Run[];
  agreements: { agreement: Agreement; hash: string; at: string }[];
};
export type Receipt = {
  project: string;
  agreement: Agreement;
  hash: string;
  approvals: Partial<Record<Role, Approval>>;
  run: Run;
  issued_at: string;
};
export const money = (minor: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(minor / 100);
export const date = (value: string) =>
  new Date(value + "T12:00:00").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
export const day = (value: string) =>
  new Date(value + "T12:00:00").toLocaleDateString("en-GB", {
    weekday: "long",
  });
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const r = await fetch("/api" + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  const body = await r.json();
  if (!r.ok)
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Please check the form fields and try again.",
    );
  return body;
}
