import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "NIFTY AI Trader",
  description: "Institutional F&O Research and Paper Trading System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased h-screen w-screen overflow-hidden flex bg-[var(--color-surface)] text-[var(--color-primary)]`}
      >
        <Sidebar />
        <main className="flex-1 h-full overflow-y-auto bg-[var(--color-surface)] p-4 md:p-6">
          {children}
        </main>
      </body>
    </html>
  );
}
