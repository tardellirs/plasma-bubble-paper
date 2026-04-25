import Image from "next/image";
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
          <picture>
            <source srcSet="/mark-128.webp" type="image/webp" />
            <Image
              src="/mark-128.png"
              alt=""
              width={36}
              height={36}
              className="h-9 w-9 rounded-full ring-1 ring-[var(--accent)]/30 group-hover:ring-[var(--accent)]/70 transition"
              priority
              unoptimized
            />
          </picture>
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
