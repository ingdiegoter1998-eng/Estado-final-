import { DetalleDiaClient } from './DetalleDiaClient'

interface PageProps {
  params: Promise<{ fecha: string }>
}

export default async function DetalleDiaPage({ params }: PageProps) {
  const { fecha } = await params
  
  return <DetalleDiaClient fecha={fecha} />
}
