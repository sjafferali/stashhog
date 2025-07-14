import { useState, useEffect } from 'react'
import { message } from 'antd'
import api from '@/services/api'
import type { SceneChanges, ProposedChange } from '@/components/analysis'

export interface PlanDetailData {
  id: number
  name: string
  description?: string
  status: 'DRAFT' | 'REVIEWING' | 'APPLIED' | 'CANCELLED'
  created_at: string
  updated_at: string
  applied_at?: string
  total_scenes: number
  total_changes: number
  metadata: {
    model?: string
    temperature?: number
    confidence_threshold?: number
    options?: {
      detect_performers?: boolean
      detect_studios?: boolean
      detect_tags?: boolean
      detect_details?: boolean
      use_ai?: boolean
    }
  }
  scenes: SceneChanges[]
}

export interface UsePlanDetailReturn {
  plan: PlanDetailData | null
  loading: boolean
  error: Error | null
  refresh: () => Promise<void>
  updateChange: (changeId: string, proposedValue: any) => Promise<void>
  acceptChange: (changeId: string) => void
  rejectChange: (changeId: string) => void
  acceptAllChanges: (sceneId?: string) => void
  rejectAllChanges: (sceneId?: string) => void
  getStatistics: () => {
    totalChanges: number
    acceptedChanges: number
    rejectedChanges: number
    pendingChanges: number
    acceptanceRate: number
    averageConfidence: number
  }
}

export function usePlanDetail(planId: number): UsePlanDetailReturn {
  const [plan, setPlan] = useState<PlanDetailData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  // Fetch plan details
  const fetchPlan = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.get(`/analysis/plans/${planId}`)
      setPlan(response.data)
    } catch (err) {
      setError(err as Error)
      message.error('Failed to load plan details')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (planId) {
      fetchPlan()
    }
  }, [planId])

  // Update a specific change
  const updateChange = async (changeId: string, proposedValue: any) => {
    try {
      await api.patch(`/analysis/changes/${changeId}`, { proposed_value: proposedValue })
      
      // Update local state
      setPlan(prev => {
        if (!prev) return null
        
        return {
          ...prev,
          scenes: prev.scenes.map(scene => ({
            ...scene,
            changes: scene.changes.map(change => 
              change.id === changeId 
                ? { ...change, proposedValue, editedValue: proposedValue }
                : change
            )
          }))
        }
      })
      
      message.success('Change updated')
    } catch (err) {
      message.error('Failed to update change')
      throw err
    }
  }

  // Accept a change locally
  const acceptChange = (changeId: string) => {
    setPlan(prev => {
      if (!prev) return null
      
      return {
        ...prev,
        scenes: prev.scenes.map(scene => ({
          ...scene,
          changes: scene.changes.map(change => 
            change.id === changeId 
              ? { ...change, accepted: true, rejected: false }
              : change
          )
        }))
      }
    })
  }

  // Reject a change locally
  const rejectChange = (changeId: string) => {
    setPlan(prev => {
      if (!prev) return null
      
      return {
        ...prev,
        scenes: prev.scenes.map(scene => ({
          ...scene,
          changes: scene.changes.map(change => 
            change.id === changeId 
              ? { ...change, accepted: false, rejected: true }
              : change
          )
        }))
      }
    })
  }

  // Accept all changes for a scene or all scenes
  const acceptAllChanges = (sceneId?: string) => {
    setPlan(prev => {
      if (!prev) return null
      
      return {
        ...prev,
        scenes: prev.scenes.map(scene => {
          if (sceneId && scene.scene.id !== sceneId) return scene
          
          return {
            ...scene,
            changes: scene.changes.map(change => ({
              ...change,
              accepted: true,
              rejected: false
            }))
          }
        })
      }
    })
  }

  // Reject all changes for a scene or all scenes
  const rejectAllChanges = (sceneId?: string) => {
    setPlan(prev => {
      if (!prev) return null
      
      return {
        ...prev,
        scenes: prev.scenes.map(scene => {
          if (sceneId && scene.scene.id !== sceneId) return scene
          
          return {
            ...scene,
            changes: scene.changes.map(change => ({
              ...change,
              accepted: false,
              rejected: true
            }))
          }
        })
      }
    })
  }

  // Calculate statistics
  const getStatistics = () => {
    if (!plan) {
      return {
        totalChanges: 0,
        acceptedChanges: 0,
        rejectedChanges: 0,
        pendingChanges: 0,
        acceptanceRate: 0,
        averageConfidence: 0
      }
    }

    let totalChanges = 0
    let acceptedChanges = 0
    let rejectedChanges = 0
    let totalConfidence = 0

    plan.scenes.forEach(scene => {
      scene.changes.forEach(change => {
        totalChanges++
        if (change.accepted) acceptedChanges++
        else if (change.rejected) rejectedChanges++
        totalConfidence += change.confidence
      })
    })

    const pendingChanges = totalChanges - acceptedChanges - rejectedChanges
    const acceptanceRate = totalChanges > 0 ? (acceptedChanges / totalChanges) * 100 : 0
    const averageConfidence = totalChanges > 0 ? totalConfidence / totalChanges : 0

    return {
      totalChanges,
      acceptedChanges,
      rejectedChanges,
      pendingChanges,
      acceptanceRate,
      averageConfidence
    }
  }

  return {
    plan,
    loading,
    error,
    refresh: fetchPlan,
    updateChange,
    acceptChange,
    rejectChange,
    acceptAllChanges,
    rejectAllChanges,
    getStatistics
  }
}