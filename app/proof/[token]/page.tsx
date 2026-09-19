"use client";
import { use, useEffect, useState } from "react";
import { api, type Receipt } from "@/lib/types";
import { ProofView } from "@/components/workspace";
import { Logo } from "@/components/ui";
export default function ReceiptPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const [receipt, setReceipt] = useState<Receipt | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    api<Receipt>("/receipts/" + token)
      .then(setReceipt)
      .catch((e) => setError(e.message));
  }, [token]);
  return (
    <main className="public-receipt">
      {receipt ? (
        <>
          <ProofView receipt={receipt} />
          <div className="public-receipt-actions">
            <a href="/workspace" className="secondary">
              Open ProofPact
            </a>
            <button className="primary" onClick={() => window.print()}>
              Print receipt
            </button>
          </div>
        </>
      ) : (
        <div className="boot">
          <Logo />
          <p>{error || "Opening the proof…"}</p>
        </div>
      )}
    </main>
  );
}
