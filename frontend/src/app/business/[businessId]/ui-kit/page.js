import { notFound } from 'next/navigation'
import { getSession } from '@/lib/serverApi'
import AppShell from '@/components/AppShell'
import UiKitGalleryClient from './UiKitGalleryClient'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'UI Kit Gallery · Bizora',
  description: 'Enterprise UI Kit component gallery and interactive test harness.',
}

export default async function UiKitPage({ params }) {
  if (process.env.NODE_ENV === 'production') {
    notFound()
  }

  const { businessId } = await params
  const session = await getSession()
  const business = session.businesses?.find((b) => String(b.id) === String(businessId)) ||
    session.businesses?.[0] || {
      id: businessId,
      name: 'Demo Business',
      currency: 'BDT',
      timezone: 'Asia/Dhaka',
      role: 'OWNER',
    }

  return (
    <AppShell session={session} business={business}>
      <UiKitGalleryClient business={business} />
    </AppShell>
  )
}
