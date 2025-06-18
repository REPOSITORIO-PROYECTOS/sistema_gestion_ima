import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../styles/globals.css"

const inter = Inter({ 
  variable: "--font-inter",
  subsets: ['latin'] 
});

export const metadata: Metadata = {
  title: "Jugos Swing",
  description: "Gestión de Empresas - Desarrollado por TAUP Agency",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} antialiased `} >
      <body>
        {children}
      </body>
    </html>
  );
}
