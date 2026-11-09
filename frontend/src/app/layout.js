import { Plus_Jakarta_Sans, Inter, JetBrains_Mono, Noto_Sans_Bengali } from 'next/font/google'
import '../styles/tokens.css'
import '../styles/base.css'
import '../styles/layout.css'
import '../styles/components.css'

const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  weight: ['600', '700'],
  variable: '--font-jakarta',
  display: 'swap',
})

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-inter',
  display: 'swap',
})

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-jetbrains',
  display: 'swap',
})

const bengali = Noto_Sans_Bengali({
  subsets: ['bengali'],
  weight: ['400', '600'],
  variable: '--font-bengali',
  display: 'swap',
})

export const metadata = { title: 'Bizora Operations', description: 'Business operations workspace' }

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${jakarta.variable} ${inter.variable} ${jetbrains.variable} ${bengali.variable}`}
    >
      <body>{children}</body>
    </html>
  )
}
