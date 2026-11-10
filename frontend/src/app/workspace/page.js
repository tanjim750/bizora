import { redirect } from 'next/navigation'
import { getSession } from '@/lib/serverApi'
import { WorkspacePickerClient } from './WorkspacePickerClient'

export const metadata = {
  title: 'Choose a workspace',
}

export default async function WorkspacePage() {
  const session = await getSession()
  if (!session?.authenticated) {
    redirect('/login')
  }

  return <WorkspacePickerClient session={session} />
}
