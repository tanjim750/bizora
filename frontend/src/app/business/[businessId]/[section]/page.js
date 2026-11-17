import { notFound, redirect } from 'next/navigation'
import { getSession } from '@/lib/serverApi'
import { SECTIONS, MANAGER_ROLES } from '@/lib/catalog'
import { resolveLegacySectionUrl } from '@/lib/domain/redirects'

export const dynamic = 'force-dynamic'

export default async function SectionPage({ params, searchParams }) {
  const { businessId, section: sectionKey } = await params
  const query = await searchParams

  const session = await getSession()
  if (!session.authenticated) {
    redirect('/login')
  }

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) {
    notFound()
  }

  const section = SECTIONS.find((item) => item.key === sectionKey)
  if (!section || (section.manager && !MANAGER_ROLES.has(business.role))) {
    notFound()
  }

  const destination = resolveLegacySectionUrl(businessId, sectionKey, query)
  if (destination) {
    redirect(destination)
  }

  notFound()
}
