"use client";
import { useEffect, useState } from "react";
import { Lock, ShieldCheck, AlertCircle, ArrowRight } from "lucide-react";
import { api, money, type Pact, type Role } from "@/lib/types";
import { Badge } from "./ui";

type Checkout = {
  key: string;
  order_id: string;
  amount: number;
  currency: string;
};
type CheckoutResponse = {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
};
declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open(): void };
  }
}
async function loadCheckout() {
  if (window.Razorpay) return;
  await new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve();
    script.onerror = () => {
      script.remove();
      reject(new Error("Razorpay checkout could not load. Try again."));
    };
    document.head.appendChild(script);
  });
  if (!window.Razorpay) throw new Error("Razorpay checkout is unavailable.");
}
const statuses: Record<string, string> = {
  CREATING: "Order needs reconciliation",
  AWAITING_PAYMENT: "Awaiting test payment",
  TRANSFER_PENDING: "Transfer processing",
  FUNDED: "Test funds on hold",
  DISPUTED: "Dispute under review",
  RELEASING: "Release needs reconciliation",
  RELEASE_PENDING: "Settlement pending",
  SETTLED: "Test settlement confirmed",
  REVIEW_REQUIRED: "Provider review required",
};
export default function Payments({
  pact,
  role,
  update,
}: {
  pact: Pact;
  role: Role;
  update: (p: Pact) => void;
}) {
  const [configured, setConfigured] = useState(false),
    [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [reviewed, setReviewed] = useState(false),
    [reason, setReason] = useState("");
  const payment = pact.payment;
  useEffect(() => {
    api<{ configured: boolean }>("/payments/config")
      .then((c) => setConfigured(c.configured))
      .catch((e) => setError(e.message))
      .finally(() => setLoaded(true));
  }, []);
  useEffect(() => {
    setReviewed(false);
    setReason("");
    setError("");
  }, [pact.id, pact.hash, payment?.status]);
  async function action(path: string, data?: unknown) {
    setBusy(true);
    setError("");
    try {
      update(
        await api<Pact>(`/projects/${pact.id}/payment/${path}`, "POST", data),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function fund() {
    setBusy(true);
    setError("");
    try {
      await loadCheckout();
      const result = await api<{ project: Pact; checkout: Checkout }>(
        `/projects/${pact.id}/payment/order`,
        "POST",
        { content_hash: pact.hash, reviewed },
      );
      update(result.project);
      new window.Razorpay!({
        ...result.checkout,
        name: "ProofPact · Test mode",
        description: `Agreement v${pact.current?.version} milestone`,
        handler: (response: CheckoutResponse) => {
          void action("confirm", response);
        },
        modal: { ondismiss: () => setBusy(false) },
        theme: { color: "#65609a" },
      }).open();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  const canFund =
    configured &&
    role === "client" &&
    pact.state === "AGREEMENT_LOCKED" &&
    !pact.pending_amendment &&
    (!payment || payment.status === "AWAITING_PAYMENT");
  const canRelease =
    configured &&
    role === "client" &&
    pact.state === "VERIFIED" &&
    payment?.status === "FUNDED" &&
    !pact.pending_amendment;
  return (
    <div className="two-column">
      <section className="form-paper">
        <Badge tone="amber">Razorpay Route · test mode only</Badge>
        <h2>Agree first. Fund the milestone.</h2>
        <p>
          The client funds the agreed amount before work starts. Settlement
          stays on hold while the builder delivers. Verification supplies
          evidence; the client explicitly approves release.
        </p>
        <div className="verification-header">
          <Lock size={24} />
          <div>
            <strong>
              {pact.current
                ? money(pact.current.price_minor)
                : "Agree a price first"}
            </strong>
            <small>
              One milestone ·{" "}
              {pact.current
                ? `agreement v${pact.current.version}`
                : "both approvals required"}
            </small>
          </div>
        </div>
        <h3>
          {payment ? statuses[payment.status] || payment.status : "Not funded"}
        </h3>
        {!loaded ? (
          <p>Checking payment setup…</p>
        ) : (
          !configured && (
            <p className="demo-disclosure">
              Razorpay Route test setup is not connected yet. Funding and
              release are disabled. This demo cannot move real money.
            </p>
          )
        )}
        {payment && (
          <>
            <p className="mono wrap">
              Agreement SHA-256 {payment.agreement_hash}
            </p>
            <p>{payment.order_id && `Order ${payment.order_id}`}</p>
          </>
        )}
        {payment?.status === "DISPUTED" && (
          <p className="error-banner">
            Release is blocked. An operator must review the evidence with both
            people and arrange a resolution. No automatic refund or payout
            occurs.
          </p>
        )}
        {(canFund || canRelease) && (
          <label className="check-label">
            <input
              type="checkbox"
              checked={reviewed}
              onChange={(e) => setReviewed(e.target.checked)}
            />
            <span>
              {canRelease
                ? "I reviewed this delivery and approve releasing this test milestone."
                : "I reviewed the scope, amount and deadline for this test milestone."}
            </span>
          </label>
        )}
        <div className="change-options">
          {!payment || payment.status === "AWAITING_PAYMENT" ? (
            <button
              className="primary"
              disabled={busy || !canFund || !reviewed}
              onClick={fund}
            >
              Fund test milestone <ArrowRight size={16} />
            </button>
          ) : null}
          {payment?.order_id && (
            <button
              className="secondary"
              disabled={busy || !configured}
              onClick={() => action("refresh")}
            >
              Refresh payment status
            </button>
          )}
          {payment?.status === "FUNDED" && (
            <button
              className="primary"
              disabled={busy || !canRelease || !reviewed}
              onClick={() =>
                action("release", { content_hash: pact.hash, reviewed })
              }
            >
              Approve test release
            </button>
          )}
        </div>
        {payment?.status === "FUNDED" && (
          <div className="side-paper">
            <h3>Something went wrong?</h3>
            <p>
              Either participant can flag a dispute before release. Funds stay
              on hold while the issue is reviewed.
            </p>
            <label className="field">
              Reason
              <textarea
                rows={3}
                minLength={10}
                maxLength={2000}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
            <button
              className="secondary"
              disabled={busy || reason.trim().length < 10}
              onClick={() => action("dispute", { reason })}
            >
              <AlertCircle size={16} />
              Open dispute
            </button>
          </div>
        )}
        {error && (
          <p className="error-banner" role="alert">
            {error}
          </p>
        )}
        {busy && <p role="status">Waiting for Razorpay…</p>}
      </section>
      <aside className="side-paper">
        <ShieldCheck size={28} />
        <h3>What protects the agreement?</h3>
        <ol>
          <li>Both people approve the same scope, price and deadline.</li>
          <li>Razorpay confirms payment and a held transfer.</li>
          <li>The builder submits work against that locked scope.</li>
          <li>The client reviews the evidence and approves release.</li>
        </ol>
        <p>
          A pending extra request cannot silently change the funded scope. A
          payment record blocks amendments until the milestone is resolved.
        </p>
        <p>
          Test transactions only. Settlement holds are not a claim of regulated
          escrow. Live accounts, dispute operations and provider approval are
          still required before handling real money.
        </p>
      </aside>
    </div>
  );
}
