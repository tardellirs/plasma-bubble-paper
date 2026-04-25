import Link from "next/link";

const links = [
  { href: "/map", label: "Map" },
  { href: "/storms", label: "Storms" },
  { href: "/dataset", label: "Dataset" },
  { href: "/methods", label: "Methods" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-30 border-b border-[#1c2236] bg-[var(--bg)]/85 backdrop-blur">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-3 group"
          aria-label="EPB Detector home"
        >
          <span className="relative inline-flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent)]/10 ring-1 ring-[var(--accent)]/40">
            <span className="absolute inset-0 rounded-full bg-[var(--accent)]/20 animate-ping" />
            <span className="relative h-2 w-2 rounded-full bg-[var(--accent)]" />
          </span>
          <span className="font-display text-base font-semibold tracking-tight">
            epb<span className="text-[var(--accent)]">.</span>detector
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="rounded-full px-3 py-1.5 text-sm text-[var(--fg-muted)] hover:text-white hover:bg-white/5 transition"
            >
              {l.label}
            </Link>
          ))}
          <a
            className="btn btn-ghost ml-2 text-xs"
            href="https://github.com/giorgiopicanco/OASIS"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
}
