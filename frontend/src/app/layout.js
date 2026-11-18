import '../styles/tokens.css'
import '../styles/base.css'
import '../styles/layout.css'
import '../styles/components.css'

export const metadata = {
  title: {
    default: 'Bizora Operations',
    template: '%s · Bizora',
  },
  description: 'Enterprise operations and business intelligence platform',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script id="theme-init">{`try{var t=localStorage.getItem('bizora_theme');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t)}catch(e){}`}</script>
      </head>
      <body>{children}</body>
    </html>
  )
}
