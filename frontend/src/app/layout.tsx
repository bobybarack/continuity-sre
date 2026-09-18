import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CONTINUITY // Autonomous Stream Incident Commander",
  description:
    "Autonomous stream continuity and SRE incident commander powered by Google Cloud Gemini 3.7 Flash and Grafana Cloud MCP. Detects, diagnoses, and self-heals live 4K premiere streams in real time.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="min-h-[100dvh] bg-[#f8f9fb] text-[#111827] antialiased">
        {children}
      </body>
    </html>
  );
}
