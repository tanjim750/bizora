import '../styles/tokens.css'
import '../styles/base.css'
import '../styles/layout.css'
import '../styles/components.css'

export const metadata = { title: 'Bizora Operations', description: 'Business operations workspace' }

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
