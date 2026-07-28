import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Align Urgent Care Demo",
  description: "Multilingual urgent care intake and live clinician view.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
