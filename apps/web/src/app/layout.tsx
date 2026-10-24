import "~/styles/globals.css";

import type { Metadata, Viewport } from "next";
import { Archivo, Martian_Mono } from "next/font/google";

export const metadata: Metadata = {
  title: {
    default: "Spottr",
    template: "%s · Spottr",
  },
  description:
    "An AI lifting coach that answers from your training log, not from guesses.",
  applicationName: "Spottr",
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#110E0E",
};

const archivo = Archivo({
  subsets: ["latin"],
  axes: ["wdth"],
  variable: "--font-archivo",
  display: "swap",
});

const martianMono = Martian_Mono({
  subsets: ["latin"],
  variable: "--font-martian",
  display: "swap",
});

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${archivo.variable} ${martianMono.variable} antialiased`}
    >
      <body>{children}</body>
    </html>
  );
}
