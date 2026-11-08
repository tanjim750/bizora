import './globals.css'

export const metadata = { title: 'Bizora Operations', description: 'Business operations workspace' }

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
