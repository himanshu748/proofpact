"use client";
import Link from "next/link";
import { useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  ArrowLeft,
  Check,
  CheckCheck,
  Lock,
  ShieldCheck,
  FileText,
  Plus,
  Minus,
  GitCompareArrows,
  AlertCircle,
  RotateCcw,
  Eye,
  ChevronRight,
  Code2,
  UserRound,
  Scale,
  Server,
  Database,
  Cloud,
  CheckCircle2,
} from "lucide-react";
import { Logo } from "./ui";
import "@/app/landing.css";

const stages = [
  "The brief",
  "The proposal",
  "Human approval",
  "The check",
  "The repair",
  "The proof",
];
export default function Landing() {
  const [stage, setStage] = useState(1),
    [fixed, setFixed] = useState(false);
  return (
    <div className="lp">
      <a href="#landing-main" className="lp-skip">
        Skip to content
      </a>
      <header className="lp-nav">
        <Link href="/" aria-label="ProofPact home">
          <Logo />
        </Link>
        <nav aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#the-proof">What counts as proof</a>
          <Link href="/workspace" className="lp-nav-cta">
            Open workspace <ArrowUpRight size={15} />
          </Link>
        </nav>
      </header>
      <main id="landing-main">
        <section className="lp-hero">
          <div className="lp-hero-copy">
            <h1>
              Agree on done.
              <br />
              <em>Prove it.</em>
            </h1>
            <p>
              A clear agreement between the person with the idea and the person
              building it. Negotiated by private advocates. Approved by you.
              Checked against the work.
            </p>
            <div className="lp-hero-actions">
              <Link href="/workspace" className="lp-button">
                Open live demo <ArrowUpRight size={18} />
              </Link>
              <a href="#how-it-works" className="lp-underlink">
                See how it works <ArrowRight size={15} />
              </a>
            </div>
            <div className="lp-demo-note">
              <span /> No signup. Two perspectives. One complete walkthrough.
            </div>
            <div className="lp-hero-foot">
              <span className="lp-initials violet">A</span>
              <span className="lp-initials teal">J</span>
              <span>
                Built for the conversations
                <br />
                between “can you?” and “it’s done.”
              </span>
            </div>
          </div>
          <div className="lp-stage">
            <div className="lp-stage-top">
              <span>
                <span className="lp-tiny-square" /> A PACT IN PRACTICE
              </span>
              <span>Synthetic demo</span>
            </div>
            <div className="lp-artifact-scene">
              <div className="lp-paper-back" />
              <article
                className={"lp-artifact step-" + stage}
                aria-live="polite"
                aria-atomic="true"
              >
                <div className="lp-document-head">
                  <span>
                    <FileText size={14} /> ACME / ADMIN PORTAL
                  </span>
                  <span
                    className={
                      "lp-state " +
                      (stage === 5 ? "done" : stage === 3 ? "failed" : "")
                    }
                  >
                    {stage === 0
                      ? "Opening brief"
                      : stage === 1
                        ? "Proposal v3"
                        : stage === 2
                          ? "Awaiting you"
                          : stage === 3
                            ? "Needs a fix"
                            : stage === 4
                              ? "Rerun complete"
                              : "Verified"}
                  </span>
                </div>
                {stage < 3 ? (
                  <>
                    <h2>A good place to agree.</h2>
                    <p className="lp-doc-intro">
                      {stage === 0
                        ? "The ask is ambitious. Let’s make it workable."
                        : "The essentials stay. The trade-offs are clear."}
                    </p>
                    <div className="lp-price-grid">
                      <div>
                        <span>Project fee</span>
                        <strong>{stage === 0 ? "₹5,000" : "₹7,500"}</strong>
                        {stage === 1 ? (
                          <small>
                            <s>₹8,000</s> <ArrowRight size={11} /> Meet in the
                            middle
                          </small>
                        ) : (
                          <small>Fixed project fee</small>
                        )}
                      </div>
                      <div>
                        <span>Delivery</span>
                        <strong>{stage === 0 ? "Sunday" : "Monday"}</strong>
                        <small>
                          {stage === 0 ? "20 September" : "21 September"}
                          {stage === 1 && (
                            <span className="lp-change">+1 day</span>
                          )}
                        </small>
                      </div>
                    </div>
                    <div className="lp-scope">
                      {[
                        "Secure login",
                        "Analytics dashboard",
                        "Complete CSV export",
                        "OTP verification",
                      ].map((t) => (
                        <div key={t}>
                          <Check size={14} />
                          <span>{t}</span>
                          {t === "OTP verification" && stage === 1 && (
                            <small>Kept in scope</small>
                          )}
                        </div>
                      ))}
                    </div>
                    <div className="lp-excluded">
                      <span>
                        {stage === 0
                          ? "ALSO REQUESTED"
                          : "SAVED FOR ANOTHER DAY"}
                      </span>
                      <div>
                        <span>
                          {stage === 0 ? (
                            <Plus size={11} />
                          ) : (
                            <Minus size={11} />
                          )}{" "}
                          Payments
                        </span>
                        <span>
                          {stage === 0 ? (
                            <Plus size={11} />
                          ) : (
                            <Minus size={11} />
                          )}{" "}
                          Dark mode
                        </span>
                      </div>
                    </div>
                    <div className="lp-doc-bottom">
                      {stage === 2 ? (
                        <>
                          <div className="lp-signoff">
                            <span className="lp-initials violet">A</span>
                            <span>
                              Client approved
                              <Check size={12} />
                            </span>
                          </div>
                          <div className="lp-signoff waiting">
                            <span className="lp-initials teal">J</span>
                            <span>
                              Builder’s turn
                              <Lock size={12} />
                            </span>
                          </div>
                        </>
                      ) : (
                        <>
                          <ShieldCheck size={16} />
                          <span>4 deliverables. 5 ways to verify them.</span>
                        </>
                      )}
                    </div>
                  </>
                ) : stage < 5 ? (
                  <>
                    <div className="lp-check-heading">
                      <div
                        className={
                          "lp-check-icon " + (stage === 4 ? "success" : "")
                        }
                      >
                        {stage === 3 ? (
                          <AlertCircle size={27} />
                        ) : (
                          <CheckCheck size={27} />
                        )}
                      </div>
                      <h2>
                        {stage === 3
                          ? "Almost isn’t done."
                          : "The fix holds up."}
                      </h2>
                      <p>
                        {stage === 3
                          ? "The button worked. The export didn’t."
                          : "Same agreement. New delivery. Real evidence."}
                      </p>
                    </div>
                    <div className="lp-check-list">
                      {[
                        "Secure login",
                        "Analytics overview",
                        "OTP verification",
                        "CSV export",
                        "Mobile layout",
                      ].map((t, i) => (
                        <div
                          key={t}
                          className={i === 3 && stage === 3 ? "row-failed" : ""}
                        >
                          {i === 3 && stage === 3 ? (
                            <AlertCircle size={15} />
                          ) : (
                            <CheckCircle2 size={15} />
                          )}
                          <span>{t}</span>
                          <small>
                            {i === 3
                              ? stage === 3
                                ? "10 / 27 records"
                                : "27 / 27 records"
                              : i === 4
                                ? "Human reviewed"
                                : "Passed"}
                          </small>
                        </div>
                      ))}
                    </div>
                    <div
                      className={
                        "lp-file-note " + (stage === 4 ? "repaired" : "")
                      }
                    >
                      <FileText size={17} />
                      <div>
                        <strong>acme-orders.csv</strong>
                        <span>
                          {stage === 3
                            ? "Only the current page made it into the file."
                            : "All 27 records. Including the other pages."}
                        </span>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="lp-mini-receipt">
                    <div className="lp-receipt-seal">
                      <ShieldCheck size={38} />
                    </div>
                    <p>AGREED. DELIVERED. VERIFIED.</p>
                    <h2>Proof of Done.</h2>
                    <span>Acme Admin Portal</span>
                    <div className="lp-receipt-line">
                      <span>Agreement v3</span>
                      <strong>5 / 5 criteria</strong>
                    </div>
                    <div className="lp-receipt-line">
                      <span>Both people approved</span>
                      <CheckCheck size={17} />
                    </div>
                    <div className="lp-receipt-code">
                      SHA-256 / example receipt
                    </div>
                    <small>
                      A record of what was promised.
                      <br />
                      And the evidence that it happened.
                    </small>
                  </div>
                )}
              </article>
              {stage < 3 && (
                <div
                  className={
                    "lp-agent-note " +
                    (stage === 0 ? "client-note" : "builder-note")
                  }
                >
                  <span className="lp-note-avatar">
                    {stage === 0 ? (
                      <UserRound size={15} />
                    ) : (
                      <Code2 size={15} />
                    )}
                  </span>
                  <div>
                    <strong>
                      {stage === 0
                        ? "Client advocate"
                        : stage === 2
                          ? "Your decision"
                          : "Builder advocate"}
                    </strong>
                    <p>
                      {stage === 0
                        ? "Keep OTP. The extras can wait."
                        : stage === 2
                          ? "No agent can approve for you."
                          : "One more day. Room to do it right."}
                    </p>
                  </div>
                </div>
              )}
              {stage === 5 && (
                <div className="lp-verified-note">
                  <Check size={14} /> Nothing left to guess.
                </div>
              )}
            </div>
            <div className="lp-stepper">
              <button
                aria-label="Previous demo step"
                onClick={() => setStage(Math.max(0, stage - 1))}
                disabled={stage === 0}
              >
                <ArrowLeft size={14} />
              </button>
              <div role="tablist" aria-label="Agreement walkthrough">
                {stages.map((s, i) => (
                  <button
                    key={s}
                    role="tab"
                    aria-selected={stage === i}
                    aria-label={s}
                    className={stage === i ? "selected" : ""}
                    onClick={() => setStage(i)}
                  >
                    <span />
                  </button>
                ))}
              </div>
              <span>
                {String(stage + 1).padStart(2, "0")} / 06{" "}
                <strong>{stages[stage]}</strong>
              </span>
              <button
                aria-label="Next demo step"
                onClick={() => setStage(Math.min(5, stage + 1))}
                disabled={stage === 5}
              >
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </section>
        <div className="lp-principles">
          <span>
            <Lock size={16} /> Your limits stay on your side.
          </span>
          <span>
            <UserRound size={16} /> People give the final yes.
          </span>
          <span>
            <ShieldCheck size={16} /> Every result needs evidence.
          </span>
        </div>
        <section className="lp-how" id="how-it-works">
          <div className="lp-section-heading">
            <h2>
              Two sides of the table.
              <br />
              <em>Finally, on the same page.</em>
            </h2>
            <p>
              You shouldn’t have to reveal your bottom line to find common
              ground. Each side gets an advocate. The agreement gets everyone’s
              attention.
            </p>
          </div>
          <div className="lp-two-sides">
            <article className="lp-side lp-client">
              <div className="lp-side-title">
                <span className="lp-role-icon">
                  <UserRound size={22} />
                </span>
                <h3>“Here’s what I need.”</h3>
                <span>THE CLIENT</span>
              </div>
              <p>
                Explain the outcome you want, what matters most, and where you
                have room to move.
              </p>
              <div className="lp-private-lines">
                <div>
                  <span>Public opening budget</span>
                  <strong>₹5,000</strong>
                </div>
                <div>
                  <span>
                    <Lock size={12} /> Private ceiling
                  </span>
                  <strong
                    className="lp-redacted"
                    aria-label="Hidden private value"
                  >
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                  </strong>
                </div>
                <div>
                  <span>
                    <Lock size={12} /> Latest acceptable date
                  </span>
                  <strong
                    className="lp-redacted"
                    aria-label="Hidden private value"
                  >
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                  </strong>
                </div>
              </div>
              <small>
                Only your advocate receives your private constraints.
              </small>
            </article>
            <div className="lp-table-divider">
              <Scale size={22} />
              <span>
                ONE
                <br />
                SHARED
                <br />
                PACT
              </span>
            </div>
            <article className="lp-side lp-builder">
              <div className="lp-side-title">
                <span className="lp-role-icon">
                  <Code2 size={22} />
                </span>
                <h3>“Here’s what it takes.”</h3>
                <span>THE BUILDER</span>
              </div>
              <p>
                Make feasibility part of the conversation. Protect your time
                without negotiating against yourself.
              </p>
              <div className="lp-private-lines">
                <div>
                  <span>Public opening price</span>
                  <strong>₹8,000</strong>
                </div>
                <div>
                  <span>
                    <Lock size={12} /> Private minimum
                  </span>
                  <strong
                    className="lp-redacted"
                    aria-label="Hidden private value"
                  >
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                  </strong>
                </div>
                <div>
                  <span>
                    <Lock size={12} /> Capacity & technical risks
                  </span>
                  <strong
                    className="lp-redacted"
                    aria-label="Hidden private value"
                  >
                    <span />
                    <span />
                    <span />
                    <span />
                    <span />
                  </strong>
                </div>
              </div>
              <small>Public proposals travel. Private limits don’t.</small>
            </article>
          </div>
          <div className="lp-shared-result">
            <span className="lp-signed-lines">
              <span className="lp-initials violet">A</span>
              <Check size={14} />
              <span className="lp-initials teal">J</span>
              <Check size={14} />
            </span>
            <p>
              One version. Two approvals. <strong>No moving goalposts.</strong>
            </p>
            <Link href="/workspace">
              See the agreement room <ArrowUpRight size={15} />
            </Link>
          </div>
        </section>
        <section className="lp-scope-story">
          <div className="lp-scope-copy">
            <span className="lp-quote-mark" aria-hidden="true">
              “
            </span>
            <h2>
              Can you just
              <br />
              add payments?
            </h2>
            <p>
              Some of the most expensive words in a project start with “can you
              just.” New requests deserve a clear conversation, not a silent
              change to the deal.
            </p>
            <Link href="/workspace" className="lp-underlink">
              Try a scope-change request <ArrowRight size={16} />
            </Link>
          </div>
          <div className="lp-amendment">
            <div className="lp-amendment-top">
              <Scale size={19} />
              <span>SCOPE CHECK</span>
              <span>Agreement v3</span>
            </div>
            <p>
              “Also add payments and dark mode.
              <br />
              It should be small.”
            </p>
            <div className="lp-scope-verdict">
              <AlertCircle size={17} />
              <strong>That’s outside this agreement.</strong>
            </div>
            <span className="lp-scope-reason">
              Both items were explicitly excluded from the approved scope.
            </span>
            <div className="lp-amendment-options">
              <span>
                <GitCompareArrows size={15} /> Swap an existing deliverable
              </span>
              <span>
                <Plus size={15} /> Adjust the price and deadline
              </span>
              <span>
                <Lock size={15} /> Keep the current agreement
              </span>
            </div>
            <footer>
              A new scope needs a new version. And two new approvals.
            </footer>
          </div>
        </section>
        <section className="lp-proof" id="the-proof">
          <div className="lp-evidence-demo">
            <div className="lp-evidence-title">
              <span>
                <FileText size={16} /> acme-orders.csv
              </span>
              <span>Illustrative check</span>
            </div>
            <div className="lp-csv-table">
              <div className="lp-csv-heading">
                <span>ORDER</span>
                <span>CUSTOMER</span>
                <span>AMOUNT</span>
              </div>
              {[1, 2, 3].map((i) => (
                <div key={i}>
                  <span>ACM-00{i}</span>
                  <span>Customer {i}</span>
                  <span>₹2,000</span>
                </div>
              ))}
              <div className="lp-csv-ellipsis">
                <span>…</span>
                <span>More records in the app</span>
                <span>…</span>
              </div>
              <div>
                <span>ACM-{fixed ? "027" : "010"}</span>
                <span>Customer {fixed ? "27" : "10"}</span>
                <span>₹2,000</span>
              </div>
            </div>
            <div
              className={"lp-csv-result " + (fixed ? "fixed" : "")}
              aria-live="polite"
            >
              <div>
                {fixed ? <CheckCircle2 size={22} /> : <AlertCircle size={22} />}
                <span>
                  <strong>
                    {fixed
                      ? "All the records. Not just the first page."
                      : "The export stopped at page one."}
                  </strong>
                  <small>
                    {fixed
                      ? "27 exported / 27 expected"
                      : "10 exported / 27 expected"}
                  </small>
                </span>
              </div>
              <button onClick={() => setFixed(!fixed)}>
                {fixed ? "Reset example" : "Apply the demo fix"}
                {fixed ? <RotateCcw size={14} /> : <ArrowRight size={14} />}
              </button>
            </div>
            <div className="lp-evidence-caption">
              <Eye size={13} /> In the live demo, a real browser downloads and
              checks this file.
            </div>
          </div>
          <div className="lp-proof-copy">
            <h2>
              A button that works
              <br />
              isn’t always
              <br />
              <em>work that’s done.</em>
            </h2>
            <p>
              The export button responds. The file downloads. But 17 records are
              missing. ProofPact checks the acceptance condition, so “looks
              finished” doesn’t become “approved.”
            </p>
            <ul>
              <li>
                <Check size={15} /> Checks tied to the locked agreement
              </li>
              <li>
                <Check size={15} /> Screenshots and file evidence per criterion
              </li>
              <li>
                <Check size={15} /> Human review when a test can’t decide
              </li>
            </ul>
            <Link href="/workspace" className="lp-underlink">
              Inspect the evidence yourself <ArrowUpRight size={16} />
            </Link>
          </div>
        </section>
        <section className="lp-build-note">
          <div>
            <h3>Built to make its work inspectable.</h3>
            <p>
              Explicit permissions. Bounded negotiation. An agreement hash that
              both people approve.
            </p>
          </div>
          <div className="lp-build-services">
            <span>
              <Cloud size={18} /> AWS
            </span>
            <span className="lp-service-rule" />
            <span>
              <Server size={18} /> Modal
            </span>
            <span className="lp-service-rule" />
            <span>
              <Eye size={18} /> Playwright
            </span>
          </div>
          <details>
            <summary>
              A note on the implementation <Plus size={15} />
            </summary>
            <p>
              The demo uses synthetic participants with a visible role switcher.
              Modal runs private advocate inference; Amazon Bedrock remains an
              available adapter after an initial daily-quota failure. AWS
              DynamoDB and private S3 provide the deployment’s persistence.
              Playwright performs browser checks. This is agent orchestration,
              not an implementation of the A2A protocol.
            </p>
          </details>
        </section>
        <section className="lp-final">
          <div className="lp-final-mark">
            <CheckCheck size={31} />
          </div>
          <h2>
            Less back-and-forth.
            <br />
            <em>More forward.</em>
          </h2>
          <p>
            Start with a clearer agreement.
            <br />
            Finish with something you can point to.
          </p>
          <Link href="/workspace" className="lp-button">
            Open live demo <ArrowUpRight size={18} />
          </Link>
          <small>No signup required. No real commitments.</small>
        </section>
      </main>
      <footer className="lp-footer">
        <Link href="/" aria-label="ProofPact home">
          <Logo />
        </Link>
        <span>Agree on done. Prove it.</span>
        <div>
          <a href="#how-it-works">How it works</a>
          <Link href="/workspace">
            Enter the workspace <ArrowUpRight size={13} />
          </Link>
        </div>
      </footer>
    </div>
  );
}
