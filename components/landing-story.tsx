import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  Lock,
  FileCheck2,
} from "lucide-react";

export function PactJourney() {
  return (
    <section className="lp-journey" aria-label="How a project becomes proof">
      <div className="lp-journey-intro">
        <span>A project, from promise to proof.</span>
        <a href="#how-it-works">
          Follow the story <ArrowRight size={15} />
        </a>
      </div>
      <ol>
        {[
          ["Brief privately", "Each person tells their agent what matters."],
          [
            "Agree together",
            "Scope, checks and a deadline. Two human approvals.",
          ],
          [
            "Check the delivery",
            "Compare the work with the version you accepted.",
          ],
          ["Keep the evidence", "Share a receipt that explains what passed."],
        ].map(([title, description], i) => (
          <li key={title}>
            <span className="lp-journey-number">{i + 1}</span>
            <div>
              <h3>{title}</h3>
              <p>{description}</p>
            </div>
            {i < 3 && <ArrowRight className="lp-journey-arrow" size={17} />}
          </li>
        ))}
      </ol>
    </section>
  );
}

export function ObservableAgreement() {
  return (
    <section className="lp-observable" id="definition-of-done">
      <div className="lp-observable-copy">
        <h2>
          “Done” should be
          <br />
          <em>something you can check.</em>
        </h2>
        <p>
          Before the first line of code, decide what will be delivered, how it
          will be accepted, how long corrections can be requested, and who gives
          the final yes.
        </p>
        <p>
          A PDF can describe the deal. ProofPact connects that deal to the
          delivered work.
        </p>
        <Link href="/login/client" className="lp-underlink">
          Create a pact with your freelancer <ArrowUpRight size={16} />
        </Link>
      </div>
      <div className="lp-contract">
        <div className="lp-contract-header">
          <FileCheck2 size={23} />
          <span>Definition of done</span>
          <small>Example agreement</small>
        </div>
        <dl>
          <div>
            <dt>Deliverable</dt>
            <dd>A dashboard with CSV export.</dd>
          </div>
          <div>
            <dt>Acceptance</dt>
            <dd>
              The exported file contains all 27 records, across every page.
            </dd>
          </div>
          <div>
            <dt>Revision window</dt>
            <dd>
              7 days from the first delivery. Corrections refer to agreed
              criteria.
            </dd>
          </div>
          <div>
            <dt>Delivery approver</dt>
            <dd>Alex, the client. An agent cannot approve on Alex’s behalf.</dd>
          </div>
        </dl>
        <div className="lp-contract-seal">
          <Lock size={15} />
          <span>These terms belong to the version both people approve.</span>
        </div>
      </div>
    </section>
  );
}

export function AwsArchitecture() {
  return (
    <section className="lp-architecture" id="built-on-aws">
      <div className="lp-section-heading">
        <h2>
          A working product.
          <br />
          <em>A traceable path.</em>
        </h2>
        <p>
          AWS hosts the application, accounts and evidence. Each agreement
          version stays attached to the checks performed against it.
        </p>
      </div>
      <div
        className="lp-architecture-map"
        aria-label="AWS Lambda runs ProofPact; Cognito authenticates participants, DynamoDB persists agreements, and private S3 stores evidence. Modal runs advocate inference and A2A connects external agents."
      >
        <div className="lp-arch-people">
          <span>
            <i className="lp-initials violet">C</i> Client
          </span>
          <span>
            <i className="lp-initials teal">F</i> Freelancer
          </span>
          <small>Separate accounts · private briefs</small>
        </div>
        <svg className="lp-arch-wire" viewBox="0 0 100 60" aria-hidden="true">
          <path d="M20 0 V20 Q20 30 30 30 H70 Q80 30 80 40 V60 M80 0 V20 Q80 30 70 30 H30 Q20 30 20 40 V60" />
          <circle cx="50" cy="30" r="4" />
        </svg>
        <div className="lp-arch-core">
          <span>ProofPact on AWS Lambda</span>
          <strong>Brief → agreement → verification → receipt</strong>
          <small>
            Next.js + FastAPI · human approval at the decision points
          </small>
        </div>
        <div className="lp-arch-services">
          <div>
            <strong>Cognito</strong>
            <span>Participant sign-in</span>
          </div>
          <div>
            <strong>DynamoDB</strong>
            <span>Versions, approvals & tasks</span>
          </div>
          <div>
            <strong>Private S3</strong>
            <span>Screenshots & file evidence</span>
          </div>
        </div>
        <p className="lp-arch-inference">
          Modal runs advocate inference. A2A 1.0 gives external agents scoped
          access. CodeBuild, ECR and CloudFormation build and deploy the
          application.
        </p>
      </div>
      <details className="lp-build-limits">
        <summary>What works today, and what still needs work</summary>
        <p>
          The live synthetic demo runs real browser checks. Custom acceptance
          criteria use human review. Cognito sign-in and participant isolation
          passed hosted tests; signup-email delivery still needs an inbox test.
          Bedrock remains an adapter after the initial quota failure. Razorpay
          payments remain disabled while Route access is pending.
        </p>
      </details>
    </section>
  );
}

export function JudgeStart() {
  return (
    <section className="lp-judge" id="try-proofpact">
      <div>
        <h2>Try the whole story.</h2>
        <p>
          Open a ready-made project. Review both sides, lock the agreement,
          catch a broken export, then verify the repair.
        </p>
        <div className="lp-judge-facts">
          <span>
            <Check size={15} /> No signup
          </span>
          <span>
            <Check size={15} /> Synthetic project
          </span>
          <span>
            <Check size={15} /> Real browser checks
          </span>
        </div>
      </div>
      <div className="lp-judge-actions">
        <Link className="lp-button" href="/workspace?demo=1">
          Open the interactive demo <ArrowUpRight size={18} />
        </Link>
        <a
          href="/proof/J8HU-vXRBb5O4AuFidfeHEQ_hFwtFsEc"
          className="lp-underlink"
        >
          View a completed sample receipt <ArrowRight size={15} />
        </a>
        <a
          href="https://github.com/himanshu748/proofpact"
          className="lp-underlink"
        >
          Read the source on GitHub <ArrowUpRight size={15} />
        </a>
      </div>
    </section>
  );
}
