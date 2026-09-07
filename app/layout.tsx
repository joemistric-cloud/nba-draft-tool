import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "NBA Draft Tool",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-gray-950 text-gray-100">
        <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6 shrink-0">
          <Link href="/" className="text-sm font-medium text-gray-400 hover:text-white transition-colors">
            Big Board
          </Link>
          <Link href="/outcomes" className="text-sm font-medium text-gray-400 hover:text-white transition-colors">
            Historical Outcomes
          </Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
