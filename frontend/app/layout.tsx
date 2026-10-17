import type { Metadata } from "next";
import "./globals.css";
import Navbar from "../components/Navbar";

export const metadata: Metadata = {
  title: "WealthOS — AI-powered personal finance",
  description: "Privacy-first, AI-powered personal finance tracker and portfolio analysis system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Preconnect to Google Fonts CDN so fonts don't block first paint */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
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
