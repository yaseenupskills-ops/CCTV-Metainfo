import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  extractMetadata,
  listEvidenceAnalyses,
  runAnalysis,
  type AnalysisStart,
} from '../api/client'
import type { Analysis } from '../types'

const TERMINAL_STATUSES = new Set(['completed', 'failed'])

function hasActiveAnalysis(analyses: Analysis[] | undefined): boolean {
  return Boolean(analyses?.some((analysis) => !TERMINAL_STATUSES.has(analysis.status)))
}

/** Analyses for an evidence, auto-refreshing while any job is still running. */
export function useEvidenceAnalyses(evidenceId: string | undefined) {
  return useQuery({
    queryKey: ['evidence', evidenceId, 'analyses'],
    queryFn: () => listEvidenceAnalyses(evidenceId!),
    enabled: Boolean(evidenceId),
    refetchInterval: (query) => (hasActiveAnalysis(query.state.data) ? 2000 : false),
  })
}

/** Start a background analysis and refresh the list so polling picks it up. */
export function useStartAnalysis(evidenceId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: AnalysisStart) => runAnalysis(evidenceId!, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['evidence', evidenceId] })
      void queryClient.invalidateQueries({ queryKey: ['evidence', evidenceId, 'analyses'] })
    },
  })
}

/** Queue metadata extraction and refresh evidence detail until it lands. */
export function useExtractMetadata(evidenceId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => extractMetadata(evidenceId!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['evidence', evidenceId] })
    },
  })
}
