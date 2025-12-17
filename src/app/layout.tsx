import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import Providers from "@/components/providers/session-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Rune-X - AI Semantic Archaeologist",
  description: "Interpreting the Past. Empowering the Future. Advanced multimodal AI platform for ancient script interpretation, reconstruction, and semantic analysis.",
  keywords: ["ancient languages", "AI translation", "cultural heritage", "glyph recognition", "archaeology", "linguistics", "epigraphy", "ancient scripts", "heritage AI"],
  authors: [{ name: "Zhicong Technology" }],
  icons: {
    icon: "/logo.svg",
  },
  openGraph: {
    title: "Rune-X",
    description: "Advanced multimodal AI platform for ancient script interpretation and reconstruction",
    url: "https://rune-x.com",
    siteName: "Rune-X",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Rune-X",
    description: "Advanced multimodal AI platform for ancient script interpretation and reconstruction",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
