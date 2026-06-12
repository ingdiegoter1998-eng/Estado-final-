import { Metadata } from 'next'
import VisorDocumentoClient from './VisorDocumentoClient'

export const metadata: Metadata = {
  title: 'Visor de Documento | Correspondencia',
}

export default async function DocumentoPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return <VisorDocumentoClient id={parseInt(id, 10)} />
}
