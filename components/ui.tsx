"use client";
import { useEffect, useRef, type ReactNode } from "react";
import { Check, ShieldCheck, X, Lock, ArrowUpRight } from "lucide-react";
export function Logo() {
  return (
    <span className="brand">
      <span className="brand-icon">
        <Check size={21} />
      </span>
      proofpact<span className="brand-period">.</span>
    </span>
  );
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    el?.showModal();
    return () => el?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={"modal " + (wide ? "wide" : "")}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <header>
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </header>
      {children}
    </dialog>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty">
      <ShieldCheck size={32} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function PrivacyNote() {
  return (
    <div className="privacy-note">
      <Lock size={14} />
      <span>Private limits stay private. Only proposals enter this room.</span>
    </div>
  );
}
export function External({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="text-button">
      {children}
      <ArrowUpRight size={15} />
    </a>
  );
}
