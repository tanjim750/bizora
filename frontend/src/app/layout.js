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

export const metadata = {
  title: {
    default: 'Bizora Operations',
    template: '%s · Bizora',
  },
  description: 'Enterprise operations and business intelligence platform',
}

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${jakarta.variable} ${inter.variable} ${jetbrains.variable} ${bengali.variable}`}
    >
      <head>
        <script id="theme-init">{`try{var t=localStorage.getItem('bizora_theme');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t)}catch(e){}`}</script>
      </head>
      <body>{children}</body>
    </html>
  )
}
