"use client";
import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  ArrowRight,
  ArrowUpRight,
  ArrowLeft,
  Check,
  ChevronDown,
  ChevronRight,
  Clock,
  FileText,
  Folder,
  LayoutGrid,
  Lock,
  MessageSquare,
  Plus,
  ShieldCheck,
  Sparkles,
  Activity,
  Play,
  RotateCcw,
  Scale,
  CheckCircle2,
  Globe,
  ExternalLink,
  Eye,
  Download,
  GitCompareArrows,
  MoreHorizontal,
  PanelLeftClose,
  SlidersHorizontal,
  Info,
  LoaderCircle,
  X,
  Minus,
  CalendarDays,
  UserRound,
  Link2,
  AlertCircle,
  Code2,
  Server,
  Search,
} from "lucide-react";
import {
  api,
  money,
  date,
  day,
  type Pact,
  type Role,
  type Agreement,
  type Result,
  type Receipt,
} from "@/lib/types";
import { Logo, Badge, Modal, Empty, PrivacyNote, External } from "./ui";

import Payments from "./payments";

type Tab =
  | "Overview"
  | "Private brief"
  | "Negotiation"
  | "Agreement"
  | "Delivery"
  | "Verification"
  | "Payments"
  | "Activity";
const tabs: Tab[] = [
  "Overview",
  "Private brief",
  "Negotiation",
  "Agreement",
  "Delivery",
  "Verification",
  "Payments",
  "Activity",
];
const labels: Record<string, string> = {
  BRIEFING: "Private briefs",
  READY_TO_NEGOTIATE: "Ready to negotiate",
  NEGOTIATING: "Negotiating",
  AWAITING_APPROVAL: "Ready for your review",
  AGREEMENT_LOCKED: "Agreement locked",
  SUBMITTED: "Delivery submitted",
  VERIFYING: "Verification in progress",
  NEEDS_FIX: "Changes needed",
  NEEDS_HUMAN_REVIEW: "Needs your review",
  VERIFIED: "Verified",
  NO_DEAL: "No agreement yet",
};
const roleNames: Record<string, string> = {
  client: "Client advocate",
  builder: "Builder advocate",
  mediator: "Mediator",
  system: "ProofPact",
  verifier: "Verifier",
};

export default function Workspace() {
  const [projects, setProjects] = useState<Pact[]>([]),
    [id, setId] = useState(""),
    [role, setRole] = useState<Role>("client"),
    [tab, setTab] = useState<Tab>("Negotiation"),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [sharedReceipt, setSharedReceipt] = useState<{
      hash: string;
      url: string;
    } | null>(null),
    [modal, setModal] = useState(""),
    [mode, setMode] = useState("modal"),
    [evidence, setEvidence] = useState<Result | null>(null),
    [version, setVersion] = useState<number | null>(null),
    [showDiff, setShowDiff] = useState(true),
    [sidebar, setSidebar] = useState(false),
    [showProjects, setShowProjects] = useState(false);
  const pact = projects.find((p) => p.id === id);
  const load = useCallback(async () => {
    try {
      const r = await api<{
        projects: Pact[];
        role: Role;
        agent_provider: string;
      }>("/session", "POST");
      setProjects(r.projects);
      setId((old) =>
        r.projects.some((p) => p.id === old) ? old : r.projects[0]?.id,
      );
      setRole(r.role);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(""), 6000);
    return () => clearTimeout(t);
  }, [notice]);
  const update = (p: Pact) => {
    setProjects((old) =>
      old.some((x) => x.id === p.id)
        ? old.map((x) => (x.id === p.id ? p : x))
        : [...old, p],
    );
    setId(p.id);
  };
  async function action(
    path: string,
    data?: unknown,
    label = "Saving",
    method = "POST",
  ) {
    if (!pact) return;
    setBusy(label);
    setError("");
    try {
      const p = await api<Pact>(`/projects/${pact.id}${path}`, method, data);
      update(p);
      return p;
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function switchRole(next: Role) {
    setBusy("Switching role");
    try {
      await api("/session/role", "POST", { role: next });
      setRole(next);
      setNotice(`Demo Theater: viewing the ${next} side.`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  const navigate = (next: Tab) => {
    setTab(next);
    setShowProjects(false);
    setSidebar(false);
  };
  async function share() {
    if (!pact) return;
    setBusy("Creating receipt");
    try {
      const r = await api<{ token: string }>(
        `/projects/${pact.id}/share`,
        "POST",
      );
      const url = location.origin + "/proof/" + r.token;
      setSharedReceipt({ hash: pact.hash!, url });
      setNotice("Receipt ready. Private briefs and raw evidence are excluded.");
      void navigator.clipboard?.writeText(url).catch(() => {});
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  const current = pact?.current;
  const selected =
    current &&
    (version === null
      ? current
      : pact.proposals.find((x) => x.agreement.version === version)
          ?.agreement || current);
  const isLocked = pact?.agreements.some((a) => a.hash === pact.hash);
  const lastRun = pact?.runs.at(-1);
  const newRun =
    lastRun &&
    lastRun.agreement_hash === pact?.hash &&
    lastRun?.url === pact?.delivery?.url &&
    pact?.delivery &&
    lastRun.at >= pact.delivery.at
      ? lastRun
      : undefined;

  if (loading)
    return (
      <div className="boot">
        <Logo />
        <div className="loading-line" />
        <p>Opening your agreement room…</p>
      </div>
    );
  if (!pact)
    return (
      <div className="boot">
        <Logo />
        <h2>Let’s get your workspace ready.</h2>
        <p role="alert">{error || "No project is open."}</p>
        <button className="primary" onClick={load}>
          Try again <RotateCcw size={16} />
        </button>
      </div>
    );
  return (
    <div className="workspace">
      <a className="skip-link" href="#main">
        Skip to agreement
      </a>
      <aside className={"sidebar " + (sidebar ? "open" : "")}>
        <a href="/" className="logo-link" aria-label="ProofPact home">
          <Logo />
        </a>
        <button
          className="workspace-picker"
          onClick={() => {
            setShowProjects(true);
            setSidebar(false);
          }}
        >
          <span className="workspace-avatar">S</span>
          <span>
            Studio workspace<small>Personal workspace</small>
          </span>
          <ChevronDown size={15} />
        </button>
        <div className="nav-label">WORKSPACE</div>
        <button
          className={"nav-item " + (showProjects ? "active" : "")}
          onClick={() => setShowProjects(true)}
        >
          <LayoutGrid size={17} /> All pacts{" "}
          <span className="nav-count">{projects.length}</span>
        </button>
        <button className="nav-item" onClick={() => navigate("Activity")}>
          <Activity size={17} /> Recent activity
        </button>
        <div className="nav-label project-label">
          YOUR PACTS
          <button aria-label="Create pact" onClick={() => setModal("create")}>
            <Plus size={15} />
          </button>
        </div>
        {projects.map((p) => (
          <button
            key={p.id}
            className={
              "nav-project " + (!showProjects && p.id === id ? "active" : "")
            }
            onClick={() => {
              setId(p.id);
              setShowProjects(false);
              setTab(p.current ? "Negotiation" : "Private brief");
              setVersion(null);
              setSidebar(false);
            }}
          >
            <span
              className={
                "project-dot " + (p.state === "VERIFIED" ? "green" : "")
              }
            />
            <span>{p.name}</span>
          </button>
        ))}
        <button className="new-pact" onClick={() => setModal("create")}>
          <Plus size={16} /> New pact
        </button>
        <div className="sidebar-bottom">
          <div className="demo-card">
            <div>
              <span className="live-dot" /> Demo Theater <Badge>ON</Badge>
            </div>
            <p>Two sides. One shared definition of done.</p>
            <button onClick={() => setModal("demo")}>
              Explore the walkthrough <ArrowUpRight size={14} />
            </button>
          </div>
          <button
            className="nav-item help"
            onClick={() => setModal("architecture")}
          >
            <Code2 size={17} /> Under the hood <ArrowUpRight size={14} />
          </button>
          <div className="user-profile">
            <div className={"avatar " + role}>
              {role === "client" ? "AM" : "JC"}
            </div>
            <span>
              {pact[role]}
              <small>
                {role === "client" ? "Client" : "Builder"} · demo participant
              </small>
            </span>
            <button
              className="icon-button"
              aria-label="Switch demo role"
              onClick={() =>
                switchRole(role === "client" ? "builder" : "client")
              }
            >
              <ChevronDown size={16} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace-body">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="Toggle navigation"
              onClick={() => setSidebar(!sidebar)}
            >
              <PanelLeftClose size={18} />
            </button>
            <Folder size={15} />
            <button onClick={() => setShowProjects(true)}>Pacts</button>
            <ChevronRight size={13} />
            <span>{showProjects ? "All pacts" : pact.name}</span>
          </div>
          <div className="topbar-right">
            <span className="shared-label">
              <span className="live-dot" /> Shared workspace
            </span>
            <div className="avatar-stack">
              <span className="avatar client">AM</span>
              <span className="avatar builder">JC</span>
            </div>
            <button
              className="icon-button"
              aria-label="Workspace details"
              onClick={() => setModal("demo")}
            >
              <MoreHorizontal size={20} />
            </button>
          </div>
        </header>
        <main id="main">
          {showProjects ? (
            <div className="projects-screen">
              <div className="eyebrow">YOUR WORKSPACE</div>
              <div className="section-heading">
                <div>
                  <h1>A little clarity goes a long way.</h1>
                  <p>Every project, with a shared definition of done.</p>
                </div>
                <button className="primary" onClick={() => setModal("create")}>
                  <Plus size={16} /> Create a pact
                </button>
              </div>
              <div className="project-grid">
                {projects.map((p) => (
                  <button
                    className="project-tile"
                    key={p.id}
                    onClick={() => {
                      setId(p.id);
                      navigate(p.current ? "Negotiation" : "Private brief");
                    }}
                  >
                    <div>
                      <FileText size={24} />
                      <Badge
                        tone={p.state === "VERIFIED" ? "success" : "amber"}
                      >
                        {labels[p.state]}
                      </Badge>
                    </div>
                    <h2>{p.name}</h2>
                    <p>{p.brief}</p>
                    <footer>
                      <span>
                        {p.client} & {p.builder}
                      </span>
                      <ArrowRight size={18} />
                    </footer>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              <section className="project-header">
                <div className="project-title-row">
                  <div>
                    <div className="eyebrow">
                      <span className="tiny-diamond" /> PACT /{" "}
                      {pact.id.slice(-6).toUpperCase()}
                    </div>
                    <h1>{pact.name}</h1>
                    <p>
                      Clear expectations. Fair trade-offs. Nothing left to
                      guess.
                    </p>
                  </div>
                  <div className="project-actions">
                    <Badge tone={isLocked ? "success" : "amber"}>
                      <span className="status-dot" />
                      {labels[pact.state]}
                    </Badge>
                    <button
                      className="secondary compact"
                      onClick={() => setModal("details")}
                    >
                      <FileText size={15} /> Project brief
                    </button>
                  </div>
                </div>
                <nav className="tabs" aria-label="Project sections">
                  {tabs.map((t) => (
                    <button
                      key={t}
                      onClick={() => navigate(t)}
                      className={tab === t ? "selected" : ""}
                    >
                      {t}
                      {t === "Negotiation" && (
                        <span className="tab-count">
                          {pact.proposals.length}
                        </span>
                      )}
                      {t === "Verification" && newRun && (
                        <span className="tab-dot" />
                      )}
                    </button>
                  ))}
                </nav>
              </section>
              {error && (
                <div className="error-banner" role="alert">
                  <AlertCircle size={18} />
                  <span>{error}</span>
                  <button
                    className="icon-button"
                    aria-label="Dismiss error"
                    onClick={() => setError("")}
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
              <div className="screen-content">
                {(tab === "Negotiation" || tab === "Agreement") && (
                  <>
                    <div className="room-heading">
                      <div>
                        <span className="eyebrow">
                          {isLocked
                            ? "THE SHARED COMMITMENT"
                            : "A LITTLE GIVE. A LITTLE GET."}
                        </span>
                        <h2>
                          {isLocked
                            ? "An agreement you can build on."
                            : "Find your common ground."}
                        </h2>
                      </div>
                      <span className="room-hint">
                        <Lock size={13} /> Humans make the final call.
                      </span>
                    </div>
                    {selected ? (
                      <div
                        className={
                          "negotiation-grid " +
                          (tab === "Agreement" ? "agreement-view" : "")
                        }
                      >
                        <aside className="advocate-column">
                          <AdvocatePanel
                            role={role}
                            pact={pact}
                            onBrief={() => navigate("Private brief")}
                            onCounter={() => setModal("counter")}
                          />
                          <div className="other-advocate">
                            <div
                              className={
                                "agent-icon " +
                                (role === "client" ? "builder" : "client")
                              }
                            >
                              <ShieldCheck size={19} />
                            </div>
                            <div>
                              <strong>
                                {role === "client" ? "Builder" : "Client"}{" "}
                                advocate
                              </strong>
                              <small>
                                <Lock size={11} /> Their constraints stay
                                private
                              </small>
                            </div>
                            <span className="live-dot" />
                          </div>
                          <PrivacyNote />
                        </aside>
                        <div className="agreement-column">
                          <div className="document-toolbar">
                            <span>
                              <FileText size={14} />
                              {isLocked
                                ? "Locked agreement"
                                : "Current proposal"}
                            </span>
                            <button onClick={() => setModal("versions")}>
                              Version {selected.version}
                              <ChevronDown size={13} />
                            </button>
                          </div>
                          <AgreementPaper
                            agreement={selected}
                            pact={pact}
                            showDiff={showDiff && selected.version === 3}
                            isLocked={!!isLocked}
                            onCriteria={() => setModal("criteria")}
                          />
                          <div className="document-footer">
                            <span>
                              <ShieldCheck size={14} />
                              {pact.proposals.at(-1)?.source === "demo"
                                ? "Sample negotiation"
                                : "Human approval required"}{" "}
                              · {selected.criteria.length} measurable criteria
                            </span>
                            <button onClick={() => setShowDiff(!showDiff)}>
                              <GitCompareArrows size={14} />
                              {showDiff ? "Hide" : "Show"} changes
                            </button>
                          </div>
                          {pact.state === "AWAITING_APPROVAL" && (
                            <div className="approval-bar">
                              <div>
                                <span className="approval-dot" />
                                <span>
                                  <strong>
                                    Your agreement. Your decision.
                                  </strong>
                                  <small>
                                    {Object.keys(pact.approvals).length} of 2
                                    people have approved this version
                                  </small>
                                </span>
                              </div>
                              <button
                                className="primary"
                                disabled={
                                  !!busy ||
                                  !!pact.approvals[role] ||
                                  selected.version !== current?.version
                                }
                                onClick={() => setModal("approve")}
                              >
                                {pact.approvals[role] ? (
                                  <>
                                    <Check size={16} /> You approved
                                  </>
                                ) : (
                                  <>
                                    Review & approve <ArrowRight size={16} />
                                  </>
                                )}
                              </button>
                            </div>
                          )}
                          {isLocked && (
                            <div className="approval-bar locked-bar">
                              <div>
                                <Lock size={19} />
                                <span>
                                  <strong>Locked by both people.</strong>
                                  <small>
                                    Version {current?.version} · SHA-256{" "}
                                    {pact.hash?.slice(0, 10)}…
                                  </small>
                                </span>
                              </div>
                              <button
                                className="primary"
                                onClick={() => navigate("Delivery")}
                              >
                                Go to delivery <ArrowRight size={16} />
                              </button>
                            </div>
                          )}
                        </div>
                        <aside className="activity-column">
                          <div className="rail-heading">
                            <h3>How we got here</h3>
                            <span>{pact.proposals.length} rounds</span>
                          </div>
                          <div className="timeline">
                            {pact.proposals.map((proposal, i) => (
                              <button
                                className={
                                  "timeline-event " +
                                  (proposal.agreement.version ===
                                  selected.version
                                    ? "current"
                                    : "")
                                }
                                key={proposal.agreement.version}
                                onClick={() =>
                                  setVersion(proposal.agreement.version)
                                }
                              >
                                <span
                                  className={
                                    "timeline-marker " + proposal.actor
                                  }
                                >
                                  {proposal.actor === "mediator" ? (
                                    <Scale size={13} />
                                  ) : proposal.actor === "builder" ? (
                                    <Code2 size={13} />
                                  ) : (
                                    <UserRound size={13} />
                                  )}
                                </span>
                                <div className="timeline-meta">
                                  <span>ROUND {i + 1}</span>
                                  {i === pact.proposals.length - 1 && (
                                    <span className="latest">LATEST</span>
                                  )}
                                </div>
                                <h4>
                                  {i === 0
                                    ? "The starting point"
                                    : i === 1
                                      ? "A practical counter"
                                      : "Common ground"}
                                </h4>
                                <p>{proposal.rationale}</p>
                                <div className="timeline-values">
                                  {money(proposal.agreement.price_minor)}
                                  <span>·</span>
                                  {date(proposal.agreement.deadline)}
                                </div>
                                <small>
                                  {roleNames[proposal.actor] || proposal.actor}{" "}
                                  <ArrowUpRight size={12} />
                                </small>
                              </button>
                            ))}
                          </div>
                          <button
                            className="text-button full-activity"
                            onClick={() => navigate("Activity")}
                          >
                            View full activity <ArrowRight size={14} />
                          </button>
                          <div className="human-note">
                            <span className="human-note-icon">
                              <UserRound size={18} />
                            </span>
                            <h4>
                              Agents do the legwork.
                              <br />
                              You hold the pen.
                            </h4>
                            <p>
                              No proposal becomes an agreement until both people
                              approve.
                            </p>
                          </div>
                        </aside>
                      </div>
                    ) : (
                      <Empty title="Your agreement starts with two perspectives.">
                        Complete both private briefs, then let the advocates
                        find a workable proposal.
                        <button
                          className="primary"
                          onClick={() => navigate("Private brief")}
                        >
                          Complete your brief <ArrowRight size={16} />
                        </button>
                      </Empty>
                    )}
                  </>
                )}
                {tab === "Overview" && (
                  <Overview pact={pact} navigate={navigate} />
                )}
                {tab === "Private brief" && (
                  <PrivateBrief
                    pact={pact}
                    role={role}
                    busy={busy}
                    action={action}
                    switchRole={switchRole}
                    mode={mode}
                    setMode={setMode}
                    onNegotiate={async () => {
                      const p = await action(
                        "/negotiate",
                        { mode },
                        "Negotiating",
                      );
                      if (p) navigate("Negotiation");
                    }}
                  />
                )}
                {tab === "Delivery" && (
                  <Delivery
                    pact={pact}
                    role={role}
                    busy={busy}
                    action={action}
                    switchRole={switchRole}
                    onVerify={() => navigate("Verification")}
                    onChange={() => setModal("change")}
                    onAmend={() => setModal("amend")}
                  />
                )}
                {tab === "Verification" && (
                  <Verification
                    pact={pact}
                    role={role}
                    busy={busy}
                    action={action}
                    onEvidence={setEvidence}
                    onDelivery={() => navigate("Delivery")}
                    onProof={() => setModal("proof")}
                    share={share}
                  />
                )}
                {tab === "Payments" && (
                  <Payments
                    key={pact.id}
                    pact={pact}
                    role={role}
                    update={update}
                  />
                )}
                {tab === "Activity" && <ActivityFeed pact={pact} />}
              </div>
            </>
          )}
          <footer className="workspace-footer">
            <span>Made for better agreements.</span>
            <span>
              <Lock size={12} /> Private by design{" "}
              <span className="footer-dot">·</span> ProofPact
            </span>
          </footer>
        </main>
      </div>
      {notice && (
        <div className="toast" role="status">
          <CheckCircle2 size={18} />
          {notice}
          <button
            className="icon-button"
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X size={14} />
          </button>
        </div>
      )}
      {busy && (
        <div className="busy-status" role="status">
          <LoaderCircle size={16} className="spin" />
          {busy}…
        </div>
      )}
      {modal === "approve" && current && (
        <ApproveDialog
          pact={pact}
          role={role}
          busy={busy}
          close={() => setModal("")}
          approve={async () => {
            const p = await action(
              "/approve",
              { content_hash: pact.hash, reviewed: true },
              "Recording approval",
            );
            if (p) {
              setModal("");
              setNotice(
                p.state === "AGREEMENT_LOCKED"
                  ? "Both people approved. Your agreement is locked."
                  : "Your approval is recorded. The other participant still needs to approve.",
              );
            }
          }}
        />
      )}
      {modal === "create" && (
        <CreateDialog
          close={() => setModal("")}
          created={(p) => {
            update(p);
            setModal("");
            navigate("Private brief");
          }}
        />
      )}
      {modal === "details" && (
        <Modal title="The original brief" onClose={() => setModal("")}>
          <div className="modal-content">
            <Badge>Shared with both sides</Badge>
            <h3>{pact.name}</h3>
            <p className="quote">{pact.brief}</p>
            <div className="people-row">
              <span>
                <span className="avatar client">AM</span>
                {pact.client}
                <small>Client</small>
              </span>
              <span>
                <span className="avatar builder">JC</span>
                {pact.builder}
                <small>Builder</small>
              </span>
            </div>
          </div>
        </Modal>
      )}
      {modal === "criteria" && current && (
        <Modal title="What done looks like" onClose={() => setModal("")}>
          <div className="modal-content">
            <p>These criteria become immutable when both people approve.</p>
            {current.criteria.map((c, i) => (
              <div className="criterion-definition" key={c.id}>
                <span className="criterion-number">0{i + 1}</span>
                <div>
                  <strong>{c.title}</strong>
                  <p>{c.description}</p>
                  <Badge tone="blue">{c.method}</Badge>
                </div>
              </div>
            ))}
          </div>
        </Modal>
      )}
      {modal === "versions" && (
        <Modal title="Agreement history" onClose={() => setModal("")}>
          <div className="modal-content">
            {pact.proposals.map((p) => (
              <button
                className="version-row"
                key={p.agreement.version}
                onClick={() => {
                  setVersion(p.agreement.version);
                  setModal("");
                }}
              >
                <FileText size={18} />
                <span>
                  <strong>Version {p.agreement.version}</strong>
                  <small>{p.rationale}</small>
                </span>
                <span>{money(p.agreement.price_minor)}</span>
                <ChevronRight size={16} />
              </button>
            ))}
          </div>
        </Modal>
      )}
      {modal === "counter" && (
        <Modal title="Ask for another proposal" onClose={() => setModal("")}>
          <div className="modal-content">
            <p>
              A new proposal clears existing approvals. Your locked agreements
              stay in the history.
            </p>
            <label className="field">
              Negotiation provider
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="modal">Modal · Qwen private advocates</option>
                <option value="bedrock">Amazon Bedrock</option>
                <option value="demo">Sample negotiation · no AI</option>
              </select>
            </label>
            <button
              className="primary"
              disabled={!!busy}
              onClick={async () => {
                const p = await action("/negotiate", { mode }, "Negotiating");
                if (p) {
                  setVersion(null);
                  setModal("");
                }
              }}
            >
              Request counter <ArrowRight size={16} />
            </button>
          </div>
        </Modal>
      )}
      {modal === "change" && (
        <ChangeDialog
          close={() => setModal("")}
          busy={busy}
          submit={async (text) => {
            const p = await action("/changes", { text }, "Reviewing scope");
            if (p) {
              setModal("");
              setNotice(
                "Change review added. Your locked agreement is unchanged.",
              );
            }
          }}
        />
      )}
      {modal === "amend" && current && (
        <AmendDialog
          agreement={current}
          close={() => setModal("")}
          busy={busy}
          submit={async (data) => {
            const p = await action("/amend", data, "Proposing amendment");
            if (p) {
              setModal("");
              setVersion(null);
              navigate("Delivery");
            }
          }}
        />
      )}
      {modal === "demo" && (
        <Modal title="One pact. The whole story." onClose={() => setModal("")}>
          <div className="modal-content">
            <Badge tone="amber">Demo Theater · synthetic participants</Badge>
            <p>
              Explore both sides of an agreement. Role switching is a demo
              capability; these are not independent authenticated people.
            </p>
            {[
              "Review the sample proposal and its trade-offs.",
              "Approve as the client, switch roles, then approve as the builder.",
              "Submit the broken fixture and verify it. The CSV exports only 10 of 27 records.",
              "Submit the fixed fixture, rerun, and confirm the mobile screenshot.",
              "Open and share the Proof of Done receipt.",
            ].map((s, i) => (
              <div className="demo-step" key={s}>
                <span>{i + 1}</span>
                {s}
              </div>
            ))}
            <button
              className="primary"
              onClick={() => {
                setModal("");
                navigate("Negotiation");
              }}
            >
              Enter the room <ArrowRight size={16} />
            </button>
          </div>
        </Modal>
      )}
      {modal === "architecture" && <Architecture close={() => setModal("")} />}
      {modal === "proof" && current && newRun && (
        <Modal title="Proof of Done" onClose={() => setModal("")} wide>
          <ProofView
            receipt={{
              project: pact.name,
              agreement: current,
              hash: pact.hash!,
              approvals: pact.approvals,
              run: newRun,
              issued_at: newRun.at,
            }}
          />
          <div className="modal-actions">
            <button className="secondary" onClick={() => window.print()}>
              <Download size={16} /> Print receipt
            </button>
            {sharedReceipt && sharedReceipt.hash === pact.hash && (
              <a
                className="secondary"
                href={sharedReceipt.url}
                target="_blank"
                rel="noreferrer"
              >
                Open shared receipt <ArrowUpRight size={16} />
              </a>
            )}
            <button className="primary" onClick={share} disabled={!!busy}>
              <Link2 size={16} /> Copy share link
            </button>
          </div>
        </Modal>
      )}
      {evidence && (
        <EvidenceDialog
          result={evidence}
          pact={pact}
          close={() => setEvidence(null)}
          role={role}
          busy={busy}
          confirm={async (accepted) => {
            const p = await action(
              "/human-review",
              { criterion_id: evidence.criterion_id, accepted },
              "Recording review",
            );
            if (p) setEvidence(null);
          }}
        />
      )}
    </div>
  );
}

function AdvocatePanel({
  role,
  pact,
  onBrief,
  onCounter,
}: {
  role: Role;
  pact: Pact;
  onBrief: () => void;
  onCounter: () => void;
}) {
  return (
    <div className={"advocate-card " + role}>
      <div className="advocate-top">
        <div className={"agent-icon " + role}>
          <ShieldCheck size={22} />
        </div>
        <span className="agent-status">
          <span className="live-dot" /> Ready
        </span>
      </div>
      <h3>Your {role} advocate</h3>
      <div className="private-label">
        <Lock size={11} /> In your corner. On your terms.
      </div>
      <div className="advocate-divider" />
      <span className="eyebrow">THE RECOMMENDATION</span>
      <h4>
        {pact.state === "NO_DEAL"
          ? "Revisit your constraints."
          : pact.state === "AWAITING_APPROVAL"
            ? "This is worth a look."
            : "A clear path forward."}
      </h4>
      <p>
        {role === "client"
          ? "The essentials stay in. The extras can wait. You get a clearer scope and a delivery date both sides can commit to."
          : "The scope is explicit, the trade-offs are visible, and additional work needs a new agreement."}
      </p>
      <div className="advocate-check">
        <Check size={14} />
        <span>Required scope retained</span>
      </div>
      <div className="advocate-check">
        <Check size={14} />
        <span>Five ways to verify delivery</span>
      </div>
      <button className="advocate-button" onClick={onBrief}>
        View your private brief <ArrowUpRight size={14} />
      </button>
      {pact.state === "AWAITING_APPROVAL" && (
        <button className="text-button counter-link" onClick={onCounter}>
          Want a different trade-off?
        </button>
      )}
    </div>
  );
}

function AgreementPaper({
  agreement: a,
  pact,
  showDiff,
  isLocked,
  onCriteria,
}: {
  agreement: Agreement;
  pact: Pact;
  showDiff: boolean;
  isLocked: boolean;
  onCriteria: () => void;
}) {
  return (
    <article className="agreement-paper">
      <div className="paper-topline">
        <span className="eyebrow">A SHARED DEFINITION OF DONE</span>
        <Badge tone={isLocked ? "success" : "amber"}>
          {isLocked ? <Lock size={11} /> : <Clock size={11} />}{" "}
          {isLocked ? "Locked" : "For your review"}
        </Badge>
      </div>
      <h2>{a.name}</h2>
      <div className="agreement-parties">
        <span>
          <span className="party-dot client" />
          {a.client}
        </span>
        <span className="party-connector">↔</span>
        <span>
          <span className="party-dot builder" />
          {a.builder}
        </span>
      </div>
      <div className="deal-terms">
        <div>
          <span className="term-label">Project fee</span>
          <strong>{money(a.price_minor)}</strong>
          {showDiff ? (
            <span className="term-change">
              <s>₹8,000</s>
              <ArrowRight size={12} />
              <span>₹500 less</span>
            </span>
          ) : (
            <span className="term-change">Fixed project fee</span>
          )}
        </div>
        <div>
          <span className="term-label">Delivery date</span>
          <strong>
            {date(a.deadline)}
            <small>{day(a.deadline)}</small>
          </strong>
          {showDiff ? (
            <span className="term-change">
              <s>20 Sep</s>
              <ArrowRight size={12} />
              <span>One extra day</span>
            </span>
          ) : (
            <span className="term-change">Agreed delivery date</span>
          )}
        </div>
      </div>
      <section className="scope-section">
        <div className="paper-section-title">
          <h3>In the pact</h3>
          <span>{a.included.length} deliverables</span>
        </div>
        <ul className="scope-list">
          {a.included.map((s, i) => (
            <li key={s}>
              <span className="scope-check">
                <Check size={13} />
              </span>
              <span>
                {s}
                <small>
                  {pact.fixture
                    ? [
                        "Email and password authentication",
                        "Key metrics, clearly presented",
                        "Every record. Not just the current page.",
                        "An extra layer of account protection",
                      ][i]
                    : "Required deliverable"}
                </small>
              </span>
              {showDiff && i === 3 && <Badge tone="teal">Kept in</Badge>}
            </li>
          ))}
        </ul>
      </section>
      <section className="excluded-section">
        <div className="paper-section-title">
          <h3>Outside this agreement</h3>
          <span>Explicitly excluded</span>
        </div>
        <div className="excluded-chips">
          {a.excluded.length ? (
            a.excluded.map((s) => (
              <span key={s}>
                <Minus size={12} />
                {s}
              </span>
            ))
          ) : (
            <span>No exclusions specified</span>
          )}
        </div>
        {showDiff && (
          <p>Less scope. More room to deliver the essentials well.</p>
        )}
      </section>
      <button className="criteria-summary" onClick={onCriteria}>
        <div className="criteria-icon">
          <ShieldCheck size={21} />
        </div>
        <span>
          <strong>Done will be more than a promise.</strong>
          <small>
            {a.criteria.length} acceptance criteria, each with a way to verify
            it.
          </small>
        </span>
        <ArrowUpRight size={16} />
      </button>
      <div className="paper-policy">
        <Lock size={12} />
        <p>New requests need a new agreement. Both sides get a say.</p>
      </div>
    </article>
  );
}

function Overview({
  pact: p,
  navigate,
}: {
  pact: Pact;
  navigate: (t: Tab) => void;
}) {
  const steps = [
    {
      title: "Two private perspectives",
      text: "Both sides share their real constraints with their own advocate.",
      done: Object.values(p.brief_ready).every(Boolean),
      tab: "Private brief",
    },
    {
      title: "One clear agreement",
      text: "Review measurable scope, price and delivery date.",
      done: !!p.current,
      tab: "Negotiation",
    },
    {
      title: "Two human approvals",
      text: "Both people sign off on the exact same version.",
      done: Object.keys(p.approvals).length === 2,
      tab: "Agreement",
    },
    {
      title: "Evidence-backed delivery",
      text: "Inspect the checks, review the evidence, and know what passed.",
      done: p.state === "VERIFIED",
      tab: "Verification",
    },
  ];
  return (
    <div className="overview">
      <div className="eyebrow">THE BIG PICTURE</div>
      <h2>From a brief to a shared finish line.</h2>
      <p className="intro">{p.brief}</p>
      <div className="journey">
        {steps.map((s, i) => (
          <button key={s.title} onClick={() => navigate(s.tab as Tab)}>
            <span className={"journey-number " + (s.done ? "done" : "")}>
              {s.done ? <Check size={20} /> : i + 1}
            </span>
            <div>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </div>
            <ArrowUpRight size={18} />
          </button>
        ))}
      </div>
      <div className="overview-note">
        <Scale size={24} />
        <div>
          <h3>Agents propose. People agree.</h3>
          <p>
            Your private limits never appear in the shared agreement. No agent
            can approve on your behalf.
          </p>
        </div>
      </div>
    </div>
  );
}

function PrivateBrief({
  pact: p,
  role,
  busy,
  action,
  switchRole,
  mode,
  setMode,
  onNegotiate,
}: {
  pact: Pact;
  role: Role;
  busy: string;
  action: (
    path: string,
    data?: unknown,
    label?: string,
    method?: string,
  ) => Promise<Pact | undefined>;
  switchRole: (r: Role) => void;
  mode: string;
  setMode: (s: string) => void;
  onNegotiate: () => void;
}) {
  const [brief, setBrief] = useState({
      private_limit_minor: role === "client" ? 800000 : 650000,
      opening_minor: role === "client" ? 500000 : 800000,
      deadline: role === "client" ? "2026-09-23" : "2026-09-21",
      notes: "",
    }),
    [err, setErr] = useState(""),
    [loaded, setLoaded] = useState(false),
    [revealed, setRevealed] = useState(false);
  useEffect(() => {
    let active = true;
    setLoaded(false);
    setRevealed(false);
    api<typeof brief>(`/projects/${p.id}/brief`)
      .then((b) => {
        if (active) {
          setBrief(
            b || {
              private_limit_minor: role === "client" ? 800000 : 650000,
              opening_minor: role === "client" ? 500000 : 800000,
              deadline: role === "client" ? "2026-09-23" : "2026-09-21",
              notes: "",
            },
          );
          setLoaded(true);
        }
      })
      .catch((e) => {
        if (active) setErr(e.message);
      });
    return () => {
      active = false;
    };
  }, [p.id, role]);
  const editable = ["BRIEFING", "NO_DEAL"].includes(p.state);
  return (
    <div className="two-column">
      <section className="form-paper">
        <Badge tone={role}>
          <Lock size={12} /> Only your side can read this
        </Badge>
        <h2>A little context for your advocate.</h2>
        <p>
          Be honest about your limits. The other side only sees the proposals
          you put forward.
        </p>
        {err && <p className="inline-error">{err}</p>}
        {!loaded ? (
          <p>Loading your private brief…</p>
        ) : (
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              await action("/brief", brief, "Saving private brief", "PUT");
            }}
          >
            <label className="field">
              Public opening {role === "client" ? "budget" : "price"} · ₹
              <input
                type="number"
                min="1"
                max="10000000"
                required
                disabled={!editable}
                value={brief.opening_minor / 100}
                onChange={(e) =>
                  setBrief({
                    ...brief,
                    opening_minor: Number(e.target.value) * 100,
                  })
                }
              />
              <small>Visible in your opening offer.</small>
            </label>
            <label className="field">
              Private {role === "client" ? "maximum budget" : "minimum price"} ·
              ₹
              <div className="sensitive-input">
                <input
                  aria-label="Private price limit"
                  type={revealed ? "number" : "password"}
                  required
                  disabled={!editable}
                  value={brief.private_limit_minor / 100}
                  onChange={(e) =>
                    setBrief({
                      ...brief,
                      private_limit_minor: Number(e.target.value) * 100,
                    })
                  }
                />
                <button
                  type="button"
                  className="icon-button"
                  aria-label={
                    revealed ? "Hide private value" : "Reveal private value"
                  }
                  onClick={() => setRevealed(!revealed)}
                >
                  <Eye size={17} />
                </button>
              </div>
              <small>
                <Lock size={11} /> Never included in public events or the other
                side’s context.
              </small>
            </label>
            <label className="field">
              {role === "client"
                ? "Latest acceptable delivery"
                : "Earliest feasible delivery"}
              <input
                type="date"
                required
                disabled={!editable}
                value={brief.deadline}
                onChange={(e) =>
                  setBrief({ ...brief, deadline: e.target.value })
                }
              />
            </label>
            <label className="field">
              What should your advocate know?
              <textarea
                rows={4}
                disabled={!editable}
                maxLength={2000}
                value={brief.notes}
                onChange={(e) => setBrief({ ...brief, notes: e.target.value })}
                placeholder="Your priorities, technical risks, and non-negotiables."
              />
            </label>
            {editable ? (
              <button className="primary" disabled={!!busy}>
                Save private brief <Lock size={15} />
              </button>
            ) : (
              <div className="notice-box">
                <Lock size={16} /> This brief is frozen for the current
                negotiation.
              </div>
            )}
          </form>
        )}
      </section>
      <aside>
        <div className="side-paper">
          <h3>Both voices matter.</h3>
          <p>Each advocate receives only their own side’s private brief.</p>
          {(["client", "builder"] as Role[]).map((r) => (
            <div className="participant-status" key={r}>
              <span className={"avatar " + r}>
                {r === "client" ? "AM" : "JC"}
              </span>
              <span>
                <strong>{p[r]}</strong>
                <small>{r} brief</small>
              </span>
              <Badge tone={p.brief_ready[r] ? "success" : "amber"}>
                {p.brief_ready[r] ? "Ready" : "Waiting"}
              </Badge>
            </div>
          ))}
          <button
            className="secondary full"
            disabled={!!busy}
            onClick={() => switchRole(role === "client" ? "builder" : "client")}
          >
            View as {role === "client" ? "builder" : "client"}{" "}
            <ArrowRight size={15} />
          </button>
          <small className="demo-disclosure">
            Role switching is available only in Demo Theater.
          </small>
        </div>
        <div className="side-paper">
          <h3>Let the advocates work.</h3>
          <label className="field">
            Response source
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="modal">Modal · Qwen</option>
              <option value="bedrock">Amazon Bedrock</option>
              <option value="demo">Sample · deterministic</option>
            </select>
          </label>
          <button
            className="primary full"
            disabled={
              !!busy || !["READY_TO_NEGOTIATE", "NO_DEAL"].includes(p.state)
            }
            onClick={onNegotiate}
          >
            Start negotiation <Sparkles size={16} />
          </button>
          <p className="fine-print">
            Up to five rounds. Both humans must approve the result.
          </p>
        </div>
      </aside>
    </div>
  );
}

function Delivery({
  pact: p,
  role,
  busy,
  action,
  switchRole,
  onVerify,
  onChange,
  onAmend,
}: {
  pact: Pact;
  role: Role;
  busy: string;
  action: (
    path: string,
    data?: unknown,
    label?: string,
  ) => Promise<Pact | undefined>;
  switchRole: (r: Role) => void;
  onVerify: () => void;
  onChange: () => void;
  onAmend: () => void;
}) {
  const [url, setUrl] = useState(p.delivery?.url || ""),
    [notes, setNotes] = useState("");
  const locked = p.agreements.some((a) => a.hash === p.hash);
  if (!locked)
    return (
      <Empty title="First, agree on the finish line.">
        Both people need to approve the same agreement before a delivery can be
        submitted.
      </Empty>
    );
  return (
    <div className="two-column">
      <div>
        <div className="form-paper">
          <Badge tone="success">
            <Lock size={12} /> Agreement v{p.current?.version} locked
          </Badge>
          <h2>Ready to show your work?</h2>
          <p>
            Submit your delivery. The verifier checks it against the exact scope
            you both approved.
          </p>
          {role !== "builder" ? (
            <div className="notice-box">
              <UserRound size={18} />
              <div>
                Delivery is the builder’s action.
                <button
                  className="text-button"
                  disabled={!!busy}
                  onClick={() => switchRole("builder")}
                >
                  Switch to builder in Demo Theater <ArrowRight size={14} />
                </button>
              </div>
            </div>
          ) : (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const result = await action(
                  "/delivery",
                  { url, notes },
                  "Submitting delivery",
                );
                if (result) onVerify();
              }}
            >
              {p.fixture && (
                <div className="fixture-picker">
                  <span className="eyebrow">TRY THE TEST TARGET</span>
                  <div>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() =>
                        setUrl("http://127.0.0.1:8000/fixture/broken")
                      }
                    >
                      Broken CSV <Code2 size={14} />
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() =>
                        setUrl("http://127.0.0.1:8000/fixture/fixed")
                      }
                    >
                      Fixed CSV <Check size={14} />
                    </button>
                  </div>
                  <small>
                    Real browser checks against synthetic demo data.
                  </small>
                </div>
              )}
              <label className="field">
                Deployed URL
                <input
                  type="url"
                  required
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://your-project.example"
                />
              </label>
              <label className="field">
                Delivery notes <span className="optional">optional</span>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  maxLength={2000}
                  placeholder="What changed? Anything the reviewer should know?"
                />
              </label>
              <button className="primary" disabled={!!busy}>
                Submit for verification <ArrowRight size={16} />
              </button>
            </form>
          )}
        </div>
        {p.delivery && (
          <div className="side-paper">
            <h3>Latest delivery</h3>
            <p className="mono wrap">{p.delivery.url}</p>
            {p.delivery.notes && <p>{p.delivery.notes}</p>}
            <button className="text-button" onClick={onVerify}>
              Open verification <ArrowRight size={15} />
            </button>
          </div>
        )}
        {p.pending_amendment && (
          <div className="change-result">
            <Badge tone="amber">Proposed addition · not active</Badge>
            <h3>Review agreement v{p.pending_amendment.agreement.version}</h3>
            <p>
              Version {p.current?.version} still defines what must be delivered.
              This proposal needs both approvals before it changes your finish
              line.
            </p>
            <p>
              <strong>
                {money(p.pending_amendment.agreement.price_minor)}
              </strong>{" "}
              · Due {date(p.pending_amendment.agreement.deadline)}
            </p>
            <ul>
              {p.pending_amendment.agreement.included.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p>
              {Object.keys(p.pending_amendment.approvals).length} of 2 approvals
            </p>
            <button
              className="primary"
              disabled={!!busy || !!p.pending_amendment.approvals[role]}
              onClick={() =>
                action(
                  "/amendment/approve",
                  { content_hash: p.pending_amendment!.hash, reviewed: true },
                  "Approving amendment",
                )
              }
            >
              {p.pending_amendment.approvals[role]
                ? "Your approval recorded"
                : "Accept this scope, price and date"}
            </button>{" "}
            <button
              className="secondary"
              disabled={!!busy}
              onClick={() =>
                action(
                  "/amendment/reject",
                  { content_hash: p.pending_amendment!.hash, reviewed: true },
                  "Rejecting amendment",
                )
              }
            >
              Reject amendment
            </button>
          </div>
        )}
        {p.changes.map((c) => (
          <div className="change-result" key={c.id}>
            <Badge tone="amber">
              {c.classification === "scope_change"
                ? "Likely scope change"
                : c.classification === "clarification"
                  ? "Included clarification"
                  : "Needs a conversation"}
            </Badge>
            <h3>“{c.text}”</h3>
            <p>{c.rationale}</p>
            <div className="change-options">
              {c.options.map((o, i) => (
                <span key={o}>
                  <span>0{i + 1}</span>
                  {o}
                </span>
              ))}
            </div>
            <button className="secondary" onClick={onAmend}>
              Draft an amendment <ArrowRight size={14} />
            </button>
          </div>
        ))}
      </div>
      <aside>
        <div className="side-paper">
          <div className="agent-icon mediator">
            <Scale size={22} />
          </div>
          <h3>A small request can change the deal.</h3>
          <p>
            Compare new requests against your locked scope before anyone starts
            extra work.
          </p>
          <button
            className="secondary full"
            disabled={role !== "client"}
            onClick={onChange}
          >
            Propose a change <Plus size={15} />
          </button>
          {role !== "client" && (
            <small className="demo-disclosure">
              Switch to the client to request a change.
            </small>
          )}
        </div>
        <div className="scope-reminder">
          <span className="eyebrow">YOUR FINISH LINE</span>
          {p.current?.included.map((s) => (
            <div key={s}>
              <Check size={14} />
              {s}
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}

function Verification({
  pact: p,
  role,
  busy,
  action,
  onEvidence,
  onDelivery,
  onProof,
  share,
}: {
  pact: Pact;
  role: Role;
  busy: string;
  action: (
    path: string,
    data?: unknown,
    label?: string,
  ) => Promise<Pact | undefined>;
  onEvidence: (r: Result) => void;
  onDelivery: () => void;
  onProof: () => void;
  share: () => void;
}) {
  const run = p.runs
    .filter(
      (r) =>
        r.agreement_hash === p.hash &&
        r.url === p.delivery?.url &&
        r.at >= p.delivery.at,
    )
    .at(-1);
  const pass = run?.results.filter((r) => r.status === "passed").length || 0;
  if (!p.delivery)
    return (
      <Empty title="No delivery to inspect just yet.">
        Once the builder submits a URL, each criterion gets its own check and
        evidence.
        <button className="primary" onClick={onDelivery}>
          Go to delivery <ArrowRight size={15} />
        </button>
      </Empty>
    );
  return (
    <div className="verification-screen">
      <div className="section-heading">
        <div>
          <div className="eyebrow">THE PROOF IS IN THE DETAILS</div>
          <h2>
            {p.state === "VERIFIED"
              ? "Done. And you can prove it."
              : p.state === "NEEDS_FIX"
                ? "Good progress. One more pass."
                : "Let’s put the agreement to the test."}
          </h2>
          <p>Independent checks. Inspectable evidence. No guessing.</p>
        </div>
        <button
          className="primary"
          disabled={!!busy || p.state === "VERIFIED"}
          onClick={() => action("/verify", undefined, "Running browser checks")}
        >
          {busy === "Running browser checks" ? (
            <LoaderCircle size={16} className="spin" />
          ) : run ? (
            <RotateCcw size={16} />
          ) : (
            <Play size={16} />
          )}{" "}
          {run ? "Rerun verification" : "Run verification"}
        </button>
      </div>
      <div className="verification-header">
        <div className="agent-icon verifier">
          <ShieldCheck size={24} />
        </div>
        <div>
          <strong>Agreement v{p.current?.version}</strong>
          <small className="wrap">{p.delivery.url}</small>
        </div>
        {run && (
          <span className="run-count">
            <strong>{pass}</strong> / {run.results.length} passed
          </span>
        )}
        <Badge tone="blue">
          {run ? "Real browser evidence" : "Ready to inspect"}
        </Badge>
      </div>
      {run ? (
        <>
          <div className="results-list">
            {run.results.map((r, i) => (
              <button
                className={"result-row " + r.status}
                key={r.criterion_id}
                onClick={() => onEvidence(r)}
              >
                <span className="result-symbol">
                  {r.status === "passed" ? (
                    <CheckCircle2 size={21} />
                  ) : r.status === "review" ? (
                    <Eye size={21} />
                  ) : (
                    <AlertCircle size={21} />
                  )}
                </span>
                <span className="result-main">
                  <small>CRITERION 0{i + 1}</small>
                  <strong>{r.title}</strong>
                  <span>{r.observed}</span>
                </span>
                <Badge
                  tone={
                    r.status === "passed"
                      ? "success"
                      : r.status === "review"
                        ? "amber"
                        : "danger"
                  }
                >
                  {r.status === "passed"
                    ? "Passed"
                    : r.status === "review"
                      ? "Human review"
                      : r.status === "blocked"
                        ? "Blocked"
                        : "Failed"}
                </Badge>
                <span className="evidence-link">
                  View evidence <ArrowUpRight size={14} />
                </span>
              </button>
            ))}
          </div>
          <div className="run-footer">
            <span>
              {run.engine} · {(run.duration_ms / 1000).toFixed(1)} seconds · Run{" "}
              {p.runs.length}
            </span>
            <span>Bound to SHA-256 {run.agreement_hash.slice(0, 12)}…</span>
          </div>
          {p.state === "NEEDS_FIX" && (
            <div className="next-step">
              <div>
                <h3>The evidence tells you what to fix.</h3>
                <p>
                  Submit the fixed target, then rerun the checks against the
                  same agreement.
                </p>
              </div>
              <button className="secondary" onClick={onDelivery}>
                Submit a fix <ArrowRight size={15} />
              </button>
            </div>
          )}
          {p.state === "NEEDS_HUMAN_REVIEW" && (
            <div className="next-step">
              <div>
                <h3>Some things need a human eye.</h3>
                <p>
                  {role === "client"
                    ? "Open the mobile evidence and confirm whether the layout is usable."
                    : "Switch to the client to review the mobile screenshot."}
                </p>
              </div>
            </div>
          )}
          {p.state === "VERIFIED" && (
            <div className="proof-banner">
              <div className="proof-seal">
                <ShieldCheck size={40} />
              </div>
              <div>
                <span className="eyebrow">EVERY CRITERION ACCOUNTED FOR</span>
                <h2>A promise, with proof.</h2>
                <p>Both people agreed. Every required check passed.</p>
              </div>
              <button className="primary" onClick={onProof}>
                Open Proof of Done <ArrowUpRight size={17} />
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="verification-empty">
          <ShieldCheck size={42} />
          <h3>Five checks. One clear answer.</h3>
          <p>
            The browser will sign in, inspect analytics, verify OTP, download
            the CSV, and check the mobile layout.
          </p>
        </div>
      )}
    </div>
  );
}

function ActivityFeed({ pact }: { pact: Pact }) {
  return (
    <div className="activity-screen">
      <div className="eyebrow">A RECORD, NOT A CHAT LOG</div>
      <h2>Every decision has a history.</h2>
      <p>Shared events only. Private briefs never appear here.</p>
      <div className="activity-list">
        {[...pact.events].reverse().map((e) => (
          <div className="activity-entry" key={e.id}>
            <span className={"agent-icon " + e.actor}>
              {e.actor === "verifier" ? (
                <ShieldCheck size={18} />
              ) : e.actor === "mediator" ? (
                <Scale size={18} />
              ) : (
                <FileText size={18} />
              )}
            </span>
            <div>
              <small>{roleNames[e.actor]}</small>
              <h3>{e.title}</h3>
              <p>{e.detail}</p>
            </div>
            <time>
              {new Date(e.at).toLocaleTimeString("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </time>
          </div>
        ))}
      </div>
    </div>
  );
}

function ApproveDialog({
  pact,
  role,
  busy,
  close,
  approve,
}: {
  pact: Pact;
  role: Role;
  busy: string;
  close: () => void;
  approve: () => void;
}) {
  const [checked, setChecked] = useState(false);
  return (
    <Modal
      title={`Approve Agreement v${pact.current!.version}`}
      onClose={close}
    >
      <div className="modal-content">
        <div className="approval-summary">
          <Lock size={25} />
          <div>
            <strong>{pact.name}</strong>
            <p>
              {money(pact.current!.price_minor)} · Delivery{" "}
              {date(pact.current!.deadline)}
            </p>
          </div>
        </div>
        <p>
          You are approving as the <strong>{role}</strong>. Agents cannot do
          this for you. Any edit requires both people to approve a new version.
        </p>
        <div className="hash-display">
          <small>SHA-256 · THIS EXACT VERSION</small>
          <code>{pact.hash}</code>
        </div>
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
          />
          <span>
            I reviewed the scope, price, deadline and acceptance criteria.
          </span>
        </label>
      </div>
      <div className="modal-actions">
        <button className="secondary" onClick={close}>
          Keep reviewing
        </button>
        <button
          className="primary"
          disabled={!checked || !!busy}
          onClick={approve}
        >
          Approve Agreement v{pact.current!.version} <Check size={16} />
        </button>
      </div>
    </Modal>
  );
}

function CreateDialog({
  close,
  created,
}: {
  close: () => void;
  created: (p: Pact) => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      created(
        await api<Pact>("/projects", "POST", {
          name: f.get("name"),
          brief: f.get("brief"),
          client: f.get("client"),
          builder: f.get("builder"),
          requirements: String(f.get("requirements"))
            .split("\n")
            .map((x) => x.trim())
            .filter(Boolean),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Start with a shared understanding." onClose={close}>
      <form onSubmit={submit}>
        <div className="modal-content">
          <p>A clear brief is the first step toward a better agreement.</p>
          <label className="field">
            Project name
            <input
              name="name"
              required
              minLength={3}
              maxLength={100}
              placeholder="e.g. Acme Admin Portal"
            />
          </label>
          <label className="field">
            Public brief
            <textarea
              name="brief"
              required
              minLength={10}
              maxLength={4000}
              rows={3}
              placeholder="What are you building, and why?"
            />
          </label>
          <div className="form-row">
            <label className="field">
              Client name
              <input
                name="client"
                required
                maxLength={80}
                placeholder="Alex Morgan"
              />
            </label>
            <label className="field">
              Builder name
              <input
                name="builder"
                required
                maxLength={80}
                placeholder="Jamie Chen"
              />
            </label>
          </div>
          <label className="field">
            Required deliverables
            <small>One per line. These become acceptance criteria.</small>
            <textarea
              name="requirements"
              required
              rows={4}
              placeholder={"Secure login\nAnalytics dashboard\nCSV export"}
            />
          </label>
          <div className="notice-box">
            <Info size={16} />
            <span>
              Custom projects use human-review criteria until a browser test
              contract is configured.
            </span>
          </div>
          {error && (
            <p className="inline-error" role="alert">
              {error}
            </p>
          )}
        </div>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={close}>
            Cancel
          </button>
          <button className="primary" disabled={busy}>
            Create pact <ArrowRight size={16} />
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ChangeDialog({
  close,
  busy,
  submit,
}: {
  close: () => void;
  busy: string;
  submit: (text: string) => void;
}) {
  const [text, setText] = useState(
    "Also add payments and dark mode. It should be small.",
  );
  return (
    <Modal title="Is that in the pact?" onClose={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(text);
        }}
      >
        <div className="modal-content">
          <p>
            Compare a new request with the locked scope. Nothing changes without
            a fresh agreement.
          </p>
          <label className="field">
            What would you like to change?
            <textarea
              required
              minLength={5}
              maxLength={2000}
              rows={4}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </label>
          <small>
            Scope matching is a conservative rules-based check. Ambiguous
            requests go to human review.
          </small>
        </div>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={close}>
            Cancel
          </button>
          <button className="primary" disabled={!!busy}>
            Check the scope <Scale size={16} />
          </button>
        </div>
      </form>
    </Modal>
  );
}

function AmendDialog({
  agreement: a,
  close,
  busy,
  submit,
}: {
  agreement: Agreement;
  close: () => void;
  busy: string;
  submit: (data: unknown) => void;
}) {
  return (
    <Modal title={`Propose Agreement v${a.version + 1}`} onClose={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          submit({
            included: String(f.get("scope"))
              .split("\n")
              .map((x) => x.trim())
              .filter(Boolean),
            price_minor: Math.round(Number(f.get("price")) * 100),
            deadline: f.get("deadline"),
          });
        }}
      >
        <div className="modal-content">
          <p>
            Version {a.version} remains active for delivery and verification.
            This proposal takes effect only after both participants approve it.
          </p>
          <label className="field">
            Included scope · one item per line
            <textarea
              name="scope"
              required
              rows={5}
              defaultValue={a.included.join("\n")}
            />
          </label>
          <div className="form-row">
            <label className="field">
              Project price · ₹
              <input
                type="number"
                name="price"
                required
                min={1}
                defaultValue={a.price_minor / 100}
              />
            </label>
            <label className="field">
              Delivery date
              <input
                type="date"
                name="deadline"
                required
                defaultValue={a.deadline}
              />
            </label>
          </div>
          <small>
            Amended scope uses human-review criteria. Existing test results
            cannot certify new scope.
          </small>
        </div>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={close}>
            Cancel
          </button>
          <button className="primary" disabled={!!busy}>
            Propose amendment <ArrowRight size={15} />
          </button>
        </div>
      </form>
    </Modal>
  );
}

function EvidenceDialog({
  result: r,
  pact,
  close,
  role,
  busy,
  confirm,
}: {
  result: Result;
  pact: Pact;
  close: () => void;
  role: Role;
  busy: string;
  confirm: (accepted: boolean) => void;
}) {
  const screenshot = r.evidence.find((e) => e.type === "screenshot"),
    csv = r.evidence.find((e) => e.type === "csv");
  const [view, setView] = useState(csv ? "file" : "screenshot");
  function download() {
    if (!csv) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([csv.content || ""], { type: "text/csv" }),
    );
    a.download = csv.name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  return (
    <Modal title={r.title + " · evidence"} onClose={close} wide>
      <div className="modal-content">
        <div className="evidence-summary">
          <Badge
            tone={
              r.status === "passed"
                ? "success"
                : r.status === "review"
                  ? "amber"
                  : "danger"
            }
          >
            {r.status === "review" ? "Needs human review" : r.status}
          </Badge>
          <p>{r.observed}</p>
        </div>
        <div className="evidence-tabs">
          <button
            className={view === "screenshot" ? "selected" : ""}
            onClick={() => setView("screenshot")}
          >
            Screenshot
          </button>
          {csv && (
            <button
              className={view === "file" ? "selected" : ""}
              onClick={() => setView("file")}
            >
              Downloaded CSV
            </button>
          )}
          <button
            className={view === "assertion" ? "selected" : ""}
            onClick={() => setView("assertion")}
          >
            Assertion
          </button>
        </div>
        {view === "screenshot" &&
          (screenshot ? (
            <div className="screenshot-frame">
              <img
                src={`/api/projects/${pact.id}/evidence/${screenshot.name}`}
                alt={`Browser evidence for ${r.title}`}
              />
            </div>
          ) : (
            <Empty title="No screenshot was captured.">
              The browser could not finish this check. Rerun when the target is
              available.
            </Empty>
          ))}
        {view === "file" && csv && (
          <div className="file-evidence">
            <div>
              <FileText size={20} />
              <strong>{csv.name}</strong>
              <span>
                {csv.rows} of {csv.expected_rows} rows
              </span>
              <button
                className="icon-button"
                aria-label="Download evidence CSV"
                onClick={download}
              >
                <Download size={18} />
              </button>
            </div>
            <pre>{csv.content}</pre>
          </div>
        )}
        {view === "assertion" && (
          <div className="assertion">
            <small>EXPECTED</small>
            <p>{r.expected}</p>
            <small>OBSERVED</small>
            <p>{r.observed}</p>
            <small>AGREEMENT HASH</small>
            <code>{pact.hash}</code>
          </div>
        )}
        {r.human_review && (
          <p className="fine-print">
            Client confirmed at {new Date(r.human_review.at).toLocaleString()}.
          </p>
        )}
      </div>
      {r.status === "review" && role === "client" && (
        <div className="modal-actions">
          <button
            className="secondary"
            disabled={!!busy}
            onClick={() => confirm(false)}
          >
            Needs changes
          </button>
          <button
            className="primary"
            disabled={!!busy}
            onClick={() => confirm(true)}
          >
            Confirm visual usability <Check size={16} />
          </button>
        </div>
      )}
    </Modal>
  );
}

function Architecture({ close }: { close: () => void }) {
  return (
    <Modal title="Built around the agreement." onClose={close}>
      <div className="modal-content">
        <p>
          Deterministic code holds authority. Models suggest terms; browsers
          collect evidence.
        </p>
        {[
          {
            name: "Next.js + FastAPI",
            text: "The interface and role-checked project lifecycle.",
            icon: Globe,
          },
          {
            name: "Modal · Qwen",
            text: "Private advocate inference, deployed as an authenticated GPU service.",
            icon: Sparkles,
          },
          {
            name: "Amazon Bedrock",
            text: "Supported provider. Initial live test hit the daily token quota.",
            icon: Server,
          },
          {
            name: "Persistent records",
            text: "Local SQLite; conditional-write DynamoDB adapter for AWS deployment.",
            icon: FileText,
          },
          {
            name: "Playwright Chromium",
            text: "Actual browser assertions, screenshots and downloaded CSV analysis.",
            icon: ShieldCheck,
          },
        ].map((s) => (
          <div className="architecture-row" key={s.name}>
            <s.icon size={21} />
            <div>
              <strong>{s.name}</strong>
              <p>{s.text}</p>
            </div>
          </div>
        ))}
        <div className="notice-box">
          <Lock size={16} /> Demo Theater uses synthetic participants and lets
          you switch roles. Production identity is a separate deployment
          requirement.
        </div>
      </div>
    </Modal>
  );
}

export function ProofView({ receipt: r }: { receipt: Receipt }) {
  return (
    <article className="proof-receipt">
      <div className="receipt-top">
        <Logo />
        <span className="eyebrow">VERIFICATION RECEIPT</span>
      </div>
      <div className="receipt-hero">
        <div className="proof-seal">
          <ShieldCheck size={45} />
        </div>
        <span className="eyebrow">AGREED. DELIVERED. VERIFIED.</span>
        <h1>
          Proof of Done<span>.</span>
        </h1>
        <p>{r.project}</p>
      </div>
      <div className="receipt-terms">
        <div>
          <small>AGREEMENT</small>
          <strong>Version {r.agreement.version}</strong>
        </div>
        <div>
          <small>PROJECT FEE</small>
          <strong>{money(r.agreement.price_minor)}</strong>
        </div>
        <div>
          <small>DELIVERY DATE</small>
          <strong>{date(r.agreement.deadline)}</strong>
        </div>
      </div>
      <div className="receipt-results">
        {r.run.results.map((c) => (
          <div key={c.criterion_id}>
            <CheckCircle2 size={16} />
            <span>{c.title}</span>
            <small>
              {c.human_review ? "Human confirmed" : "Browser verified"}
            </small>
          </div>
        ))}
      </div>
      <div className="receipt-signatures">
        <div>
          <Check size={14} />
          <span>
            {r.agreement.client}
            <small>Client approved</small>
          </span>
        </div>
        <div>
          <Check size={14} />
          <span>
            {r.agreement.builder}
            <small>Builder approved</small>
          </span>
        </div>
      </div>
      <div className="receipt-hash">
        <small>IMMUTABLE AGREEMENT · SHA-256</small>
        <code>{r.hash}</code>
      </div>
      <footer>
        <span>
          Evidence for this delivery at{" "}
          {new Date(r.run.at).toLocaleString("en-GB")}.
        </span>
        <p>
          This receipt records checks against agreed criteria. It is not a legal
          contract or a guarantee of future behavior.
        </p>
      </footer>
    </article>
  );
}
