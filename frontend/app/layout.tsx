import type { Metadata } from "next";
import "./globals.css";
import Navbar from "../components/Navbar";

export const metadata: Metadata = {
  title: "WealthOS",
  description: "Privacy-first, AI-powered personal finance tracker and portfolio analysis system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
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
