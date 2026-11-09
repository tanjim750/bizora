import { notFound, redirect } from 'next/navigation'
import { RESOURCES } from '@/lib/catalog'
import { resolveRecordDetailUrl } from '@/lib/domain/redirects'

export const dynamic = 'force-dynamic'

export default async function RecordPage({ params, searchParams }) {
  const { businessId, resource, id } = await params
  const query = await searchParams

  if (!RESOURCES.includes(resource) || !/^\d+$/.test(id)) {
    notFound()
  }

  const destination = resolveRecordDetailUrl(businessId, resource, id, query)
  if (!destination) {
    notFound()
  }

  redirect(destination)
}
