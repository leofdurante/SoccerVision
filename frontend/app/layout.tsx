import type { Metadata } from "next";
import { Archivo, Geist_Mono } from "next/font/google";
import "./globals.css";

// Archivo is a sturdy, wide-aperture grotesk — legible on a sideline tablet
// at a glance, and characterful enough at display sizes to carry headings
// without needing a second display face.
const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  display: "swap",
});

// Mono is used only for clock times and track IDs, where digit alignment
// matters more than warmth.
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "SoccerVision — Tactical Video Analysis",
  description:
    "Upload a soccer match video and get automated computer-vision tactical analysis: player tracking, team shape, and AI-generated insights.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${archivo.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-paper text-ink">{children}</body>
    </html>
  );
}
