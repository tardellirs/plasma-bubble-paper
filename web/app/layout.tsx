import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "../components/Nav";

export const metadata: Metadata = {
  title: "EPB Detector — Equatorial Plasma Bubbles, automated",
  description:
    "Open scientific platform for the detection and classification of equatorial plasma bubbles using GNSS data, built on top of pyOASIS.",
  metadataBase: new URL("http://localhost:3000"),
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
