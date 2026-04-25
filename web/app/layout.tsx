import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "../components/Nav";

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://plasma-bubble.ifsp.dev";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "EPB Detector — Equatorial Plasma Bubbles, automated",
  description:
    "Open scientific platform for the detection and classification of equatorial plasma bubbles using GNSS data, built on top of pyOASIS.",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/mark-128.webp", type: "image/webp", sizes: "128x128" },
      { url: "/mark-128.png", type: "image/png", sizes: "128x128" },
    ],
    apple: { url: "/mark-256.webp", sizes: "256x256" },
  },
  openGraph: {
    title: "Equatorial plasma bubbles, automatically detected",
    description:
      "Bulk GNSS ingest, weak labels (Pi 1997 / Cherniak 2014), XGBoost baseline, geomagnetic-storm context. Built on pyOASIS.",
    url: SITE_URL,
    siteName: "EPB Detector",
    images: [{ url: "/og.jpg", width: 1200, height: 630, alt: "EPB Detector" }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "EPB Detector",
    description: "Equatorial plasma bubbles, automatically detected from GNSS.",
    images: ["/og.jpg"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <Nav />
        <main className="flex-1">{children}</main>
        <footer className="border-t border-[#1c2236] mt-24 py-10 text-sm text-[var(--fg-muted)]">
          <div className="max-w-6xl mx-auto px-6 flex flex-wrap justify-between gap-4">
            <span>EPB Detector · CC BY-NC 4.0 · Built on pyOASIS</span>
            <span className="font-mono text-xs">
              data: IBGE RBMC · GFZ MGEX · NOAA OMNIWeb
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
