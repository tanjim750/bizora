import React from 'react'
import { notFound, redirect } from 'next/navigation'
import AppShell from '@/components/AppShell'
import { getSession } from '@/lib/serverApi'

export const dynamic = 'force-dynamic'

export default async function BusinessLayout({ children, params }) {
  const { businessId } = await params
  const session = await getSession()
  if (!session.authenticated) {
    redirect(`/login?next=/business/${businessId}/overview`)
  }

  const business = session.businesses?.find((item) => String(item.id) === String(businessId))
  if (!business) {
    notFound()
  }

  return (
    <AppShell session={session} business={business}>
      {children}
    </AppShell>
  )
}
