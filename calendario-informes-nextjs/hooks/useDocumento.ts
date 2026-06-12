import useSWR from 'swr'
import { getDocumentoMeta } from '@/lib/api/documento'
import { DocumentoMeta } from '@/types/documento'

export function useDocumento(id: number) {
  const { data, error, isLoading } = useSWR<DocumentoMeta>(
    id ? `documento-${id}` : null,
    () => getDocumentoMeta(id)
  )

  return { data, error, isLoading }
}
