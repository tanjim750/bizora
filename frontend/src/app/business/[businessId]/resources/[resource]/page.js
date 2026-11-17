import { notFound, redirect } from 'next/navigation'
import { RESOURCES } from '@/lib/catalog'
import { resolveResourceListUrl } from '@/lib/domain/redirects'

export const dynamic = 'force-dynamic'

export default async function CanonicalResourcePage({ params, searchParams }) {
  const { businessId, resource } = await params
  const query = await searchParams

  if (!RESOURCES.includes(resource)) {
    notFound()
  }

  const destination = resolveResourceListUrl(businessId, resource, query)
  if (!destination) {
    notFound()
  }

  redirect(destination)
}
