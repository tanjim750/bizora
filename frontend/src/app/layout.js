import { IBM_Plex_Sans, IBM_Plex_Mono, Noto_Sans_Bengali } from 'next/font/google'
import '../styles/tokens.css'
import '../styles/base.css'
import '../styles/layout.css'
import '../styles/components.css'

const plexSans = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-plex',
  display: 'swap',
})

const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-plex-mono',
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
      className={`${plexSans.variable} ${plexMono.variable} ${bengali.variable}`}
    >
      <head>
        <script id="theme-init">{`try{var t=localStorage.getItem('bizora_theme');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t)}catch(e){}`}</script>
      </head>
      <body>{children}</body>
    </html>
  )
}
