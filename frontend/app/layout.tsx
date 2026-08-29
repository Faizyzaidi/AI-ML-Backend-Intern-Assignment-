import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Candidate Screening",
  description:
    "AI-powered role-based candidate screening system using a RAG-driven structured interview.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <div className="mx-auto max-w-3xl px-4 py-8">
          <header className="mb-8 flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white font-bold">
              AI
            </div>
            <div>
              <p className="text-sm font-semibold leading-none">
                Candidate Screening
              </p>
              <p className="text-xs text-slate-500">RAG-powered structured interviews</p>
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
