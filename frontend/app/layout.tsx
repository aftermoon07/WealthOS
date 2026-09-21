import type { Metadata } from "next";
import "./globals.css";
import Navbar from "../components/Navbar";

export const metadata: Metadata = {
  title: "Finance Intelligence Engine",
  description: "Privacy-first, AI-powered personal finance tracker and portfolio analysis system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="bg-glow bg-glow-1"></div>
        <div className="bg-glow bg-glow-2"></div>
        <header className="app-header">
          <Navbar />
        </header>
        <main className="app-main">
          {children}
        </main>
      </body>
    </html>
  );
}
