import { useState, useCallback, useMemo } from 'react'
import { message } from 'antd'
import api from '@/services/api'
import type { ProposedChange } from '@/components/analysis'

export interface ChangeFilter {
  field?: string
  status?: 'pending' | 'accepted' | 'rejected'
  confidenceMin?: number
  confidenceMax?: number
  sceneId?: string
}

export interface ChangeSort {
  field: 'confidence' | 'field' | 'scene'
  order: 'asc' | 'desc'
}

export interface ChangeHistory {
  changeId: string
  timestamp: number
  action: 'accept' | 'reject' | 'edit' | 'undo'
  previousValue?: any
  newValue?: any
}

export interface UseChangeManagerReturn {
  // Filtering and sorting
  filter: ChangeFilter
  setFilter: (filter: ChangeFilter) => void
  sort: ChangeSort
  setSort: (sort: ChangeSort) => void
  
  // Bulk operations
  acceptByFilter: () => Promise<void>
  rejectByFilter: () => Promise<void>
  acceptByConfidence: (threshold: number) => Promise<void>
  acceptByField: (field: string) => Promise<void>
  
  // History and undo
  history: ChangeHistory[]
  canUndo: boolean
  canRedo: boolean
  undo: () => void
  redo: () => void
  clearHistory: () => void
  
  // Export
  exportChanges: (format: 'json' | 'csv' | 'markdown') => void
  
  // Apply changes
  applyChanges: (selectedOnly?: string[]) => Promise<void>
  applyProgress: {
    total: number
    completed: number
    failed: number
    inProgress: boolean
  }
}

export function useChangeManager(
  planId: number,
  changes: ProposedChange[],
  onChangeUpdate: (changeId: string, update: Partial<ProposedChange>) => void
): UseChangeManagerReturn {
  const [filter, setFilter] = useState<ChangeFilter>({})
  const [sort, setSort] = useState<ChangeSort>({ field: 'confidence', order: 'desc' })
  const [history, setHistory] = useState<ChangeHistory[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [applyProgress, setApplyProgress] = useState({
    total: 0,
    completed: 0,
    failed: 0,
    inProgress: false
  })

  // Add to history
  const addToHistory = useCallback((entry: Omit<ChangeHistory, 'timestamp'>) => {
    const newEntry = { ...entry, timestamp: Date.now() }
    
    // Remove any history after current index
    const newHistory = history.slice(0, historyIndex + 1)
    newHistory.push(newEntry)
    
    // Keep only last 50 actions
    if (newHistory.length > 50) {
      newHistory.shift()
    }
    
    setHistory(newHistory)
    setHistoryIndex(newHistory.length - 1)
  }, [history, historyIndex])

  // Filter changes
  const filteredChanges = useMemo(() => {
    return changes.filter(change => {
      if (filter.field && change.field !== filter.field) return false
      if (filter.status) {
        if (filter.status === 'accepted' && !change.accepted) return false
        if (filter.status === 'rejected' && !change.rejected) return false
        if (filter.status === 'pending' && (change.accepted || change.rejected)) return false
      }
      if (filter.confidenceMin && change.confidence < filter.confidenceMin) return false
      if (filter.confidenceMax && change.confidence > filter.confidenceMax) return false
      if (filter.sceneId && change.sceneId !== filter.sceneId) return false
      return true
    })
  }, [changes, filter])

  // Accept all filtered changes
  const acceptByFilter = async () => {
    const toAccept = filteredChanges.filter(c => !c.accepted && !c.rejected)
    
    for (const change of toAccept) {
      onChangeUpdate(change.id, { accepted: true, rejected: false })
      addToHistory({
        changeId: change.id,
        action: 'accept',
        previousValue: { accepted: change.accepted, rejected: change.rejected }
      })
    }
    
    message.success(`Accepted ${toAccept.length} changes`)
  }

  // Reject all filtered changes
  const rejectByFilter = async () => {
    const toReject = filteredChanges.filter(c => !c.accepted && !c.rejected)
    
    for (const change of toReject) {
      onChangeUpdate(change.id, { accepted: false, rejected: true })
      addToHistory({
        changeId: change.id,
        action: 'reject',
        previousValue: { accepted: change.accepted, rejected: change.rejected }
      })
    }
    
    message.success(`Rejected ${toReject.length} changes`)
  }

  // Accept by confidence threshold
  const acceptByConfidence = async (threshold: number) => {
    const toAccept = changes.filter(c => 
      !c.accepted && !c.rejected && c.confidence >= threshold
    )
    
    for (const change of toAccept) {
      onChangeUpdate(change.id, { accepted: true, rejected: false })
      addToHistory({
        changeId: change.id,
        action: 'accept',
        previousValue: { accepted: change.accepted, rejected: change.rejected }
      })
    }
    
    message.success(`Accepted ${toAccept.length} high-confidence changes`)
  }

  // Accept by field
  const acceptByField = async (field: string) => {
    const toAccept = changes.filter(c => 
      !c.accepted && !c.rejected && c.field === field
    )
    
    for (const change of toAccept) {
      onChangeUpdate(change.id, { accepted: true, rejected: false })
      addToHistory({
        changeId: change.id,
        action: 'accept',
        previousValue: { accepted: change.accepted, rejected: change.rejected }
      })
    }
    
    message.success(`Accepted ${toAccept.length} ${field} changes`)
  }

  // Undo last action
  const undo = () => {
    if (historyIndex < 0) return
    
    const action = history[historyIndex]
    
    // Revert the action
    if (action.action === 'accept' || action.action === 'reject') {
      onChangeUpdate(action.changeId, action.previousValue || {})
    } else if (action.action === 'edit') {
      onChangeUpdate(action.changeId, { proposedValue: action.previousValue })
    }
    
    setHistoryIndex(historyIndex - 1)
    message.info('Action undone')
  }

  // Redo action
  const redo = () => {
    if (historyIndex >= history.length - 1) return
    
    const action = history[historyIndex + 1]
    
    // Redo the action
    if (action.action === 'accept') {
      onChangeUpdate(action.changeId, { accepted: true, rejected: false })
    } else if (action.action === 'reject') {
      onChangeUpdate(action.changeId, { accepted: false, rejected: true })
    } else if (action.action === 'edit') {
      onChangeUpdate(action.changeId, { proposedValue: action.newValue })
    }
    
    setHistoryIndex(historyIndex + 1)
    message.info('Action redone')
  }

  // Export changes
  const exportChanges = (format: 'json' | 'csv' | 'markdown') => {
    const acceptedChanges = changes.filter(c => c.accepted)
    
    let content = ''
    let filename = `changes_${planId}_${new Date().toISOString().split('T')[0]}`
    
    if (format === 'json') {
      content = JSON.stringify(acceptedChanges, null, 2)
      filename += '.json'
    } else if (format === 'csv') {
      // CSV header
      content = 'Scene ID,Field,Current Value,Proposed Value,Confidence\n'
      acceptedChanges.forEach(change => {
        content += `"${change.sceneId}","${change.field}","${change.currentValue}","${change.proposedValue}",${change.confidence}\n`
      })
      filename += '.csv'
    } else if (format === 'markdown') {
      content = `# Analysis Plan Changes - ${new Date().toLocaleDateString()}\n\n`
      content += `Total Changes: ${acceptedChanges.length}\n\n`
      
      // Group by scene
      const byScene = acceptedChanges.reduce((acc, change) => {
        if (!acc[change.sceneId]) acc[change.sceneId] = []
        acc[change.sceneId].push(change)
        return acc
      }, {} as Record<string, ProposedChange[]>)
      
      Object.entries(byScene).forEach(([sceneId, sceneChanges]) => {
        content += `## Scene ${sceneId}\n\n`
        sceneChanges.forEach(change => {
          content += `- **${change.fieldLabel}**: ${change.currentValue} → ${change.proposedValue} (${Math.round(change.confidence * 100)}% confidence)\n`
        })
        content += '\n'
      })
      
      filename += '.md'
    }
    
    // Download file
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    
    message.success(`Exported ${acceptedChanges.length} changes`)
  }

  // Apply changes to Stash
  const applyChanges = async (selectedOnly?: string[]) => {
    const toApply = changes.filter(c => 
      c.accepted && (!selectedOnly || selectedOnly.includes(c.id))
    )
    
    if (toApply.length === 0) {
      message.warning('No accepted changes to apply')
      return
    }
    
    setApplyProgress({
      total: toApply.length,
      completed: 0,
      failed: 0,
      inProgress: true
    })
    
    try {
      const response = await api.post(`/analysis/plans/${planId}/apply`, {
        change_ids: toApply.map(c => c.id),
        background: true
      })
      
      // If background job, we'll need to monitor progress via websocket
      if (response.data.job_id) {
        message.info('Changes are being applied in the background')
        // TODO: Connect to websocket for progress updates
      } else {
        setApplyProgress(prev => ({
          ...prev,
          completed: toApply.length,
          inProgress: false
        }))
        message.success('All changes applied successfully')
      }
    } catch (error) {
      setApplyProgress(prev => ({
        ...prev,
        failed: toApply.length,
        inProgress: false
      }))
      message.error('Failed to apply changes')
    }
  }

  return {
    filter,
    setFilter,
    sort,
    setSort,
    acceptByFilter,
    rejectByFilter,
    acceptByConfidence,
    acceptByField,
    history,
    canUndo: historyIndex >= 0,
    canRedo: historyIndex < history.length - 1,
    undo,
    redo,
    clearHistory: () => {
      setHistory([])
      setHistoryIndex(-1)
    },
    exportChanges,
    applyChanges,
    applyProgress
  }
}