import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Compliance Copilot",
  description: "AI-assisted compliance review for immigration, tax, and corporate workflows",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen`}>
        <header className="border-b border-stone-200 bg-white px-6 py-4">
          <div className="mx-auto max-w-5xl flex items-center justify-between">
            <h1 className="text-lg font-semibold text-stone-800">Compliance Copilot</h1>
            <span className="text-xs text-stone-400">MVP</span>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
