import { diffLines, diffWords, diffChars, Change } from 'diff'

export interface DiffResult {
  changes: DiffChange[]
  additions: number
  deletions: number
  hasChanges: boolean
}

export interface DiffChange {
  type: 'add' | 'remove' | 'equal'
  value: string
  count?: number
  lineNumbers?: {
    old?: number
    new?: number
  }
}

export interface ArrayDiff<T> {
  added: T[]
  removed: T[]
  unchanged: T[]
  moved: Array<{ item: T; from: number; to: number }>
}

export interface ObjectDiff {
  added: Record<string, any>
  removed: Record<string, any>
  changed: Record<string, { old: any; new: any }>
  unchanged: Record<string, any>
}

// Convert diff library Change to our DiffChange format
function convertChanges(changes: Change[]): DiffChange[] {
  return changes.map(change => ({
    type: change.added ? 'add' : change.removed ? 'remove' : 'equal',
    value: change.value,
    count: change.count
  }))
}

// Calculate line numbers for diff changes
function addLineNumbers(changes: DiffChange[]): DiffChange[] {
  let oldLine = 1
  let newLine = 1
  
  return changes.map(change => {
    const lines = change.value.split('\n').length - 1
    const result = { ...change }
    
    if (change.type === 'remove') {
      result.lineNumbers = { old: oldLine }
      oldLine += lines
    } else if (change.type === 'add') {
      result.lineNumbers = { new: newLine }
      newLine += lines
    } else {
      result.lineNumbers = { old: oldLine, new: newLine }
      oldLine += lines
      newLine += lines
    }
    
    return result
  })
}

// Text diff with different granularities
export function textDiff(
  oldText: string, 
  newText: string, 
  mode: 'lines' | 'words' | 'chars' = 'lines'
): DiffResult {
  let changes: Change[]
  
  switch (mode) {
    case 'words':
      changes = diffWords(oldText, newText)
      break
    case 'chars':
      changes = diffChars(oldText, newText)
      break
    default:
      changes = diffLines(oldText, newText)
  }
  
  const diffChanges = convertChanges(changes)
  const withLineNumbers = mode === 'lines' ? addLineNumbers(diffChanges) : diffChanges
  
  const additions = diffChanges.filter(c => c.type === 'add').length
  const deletions = diffChanges.filter(c => c.type === 'remove').length
  
  return {
    changes: withLineNumbers,
    additions,
    deletions,
    hasChanges: additions > 0 || deletions > 0
  }
}

// Array diff with order tracking
export function arrayDiff<T>(
  oldArray: T[], 
  newArray: T[],
  keyFn?: (item: T) => string
): ArrayDiff<T> {
  const getKey = keyFn || ((item: T) => JSON.stringify(item))
  
  const oldMap = new Map(oldArray.map((item, index) => [getKey(item), { item, index }]))
  const newMap = new Map(newArray.map((item, index) => [getKey(item), { item, index }]))
  
  const added: T[] = []
  const removed: T[] = []
  const unchanged: T[] = []
  const moved: Array<{ item: T; from: number; to: number }> = []
  
  // Find removed and unchanged items
  oldMap.forEach(({ item, index: oldIndex }, key) => {
    if (newMap.has(key)) {
      const newIndex = newMap.get(key)!.index
      unchanged.push(item)
      if (oldIndex !== newIndex) {
        moved.push({ item, from: oldIndex, to: newIndex })
      }
    } else {
      removed.push(item)
    }
  })
  
  // Find added items
  newMap.forEach(({ item }, key) => {
    if (!oldMap.has(key)) {
      added.push(item)
    }
  })
  
  return { added, removed, unchanged, moved }
}

// Deep object diff
export function objectDiff(oldObj: any, newObj: any): ObjectDiff {
  const added: Record<string, any> = {}
  const removed: Record<string, any> = {}
  const changed: Record<string, { old: any; new: any }> = {}
  const unchanged: Record<string, any> = {}
  
  const allKeys = new Set([
    ...Object.keys(oldObj || {}),
    ...Object.keys(newObj || {})
  ])
  
  allKeys.forEach(key => {
    const oldValue = oldObj?.[key]
    const newValue = newObj?.[key]
    
    if (oldValue === undefined && newValue !== undefined) {
      added[key] = newValue
    } else if (oldValue !== undefined && newValue === undefined) {
      removed[key] = oldValue
    } else if (JSON.stringify(oldValue) !== JSON.stringify(newValue)) {
      changed[key] = { old: oldValue, new: newValue }
    } else {
      unchanged[key] = oldValue
    }
  })
  
  return { added, removed, changed, unchanged }
}

// Format diff for HTML display
export function formatDiffHtml(diff: DiffResult): string {
  return diff.changes
    .map(change => {
      const className = 
        change.type === 'add' ? 'diff-add' :
        change.type === 'remove' ? 'diff-remove' :
        'diff-equal'
      
      const escaped = escapeHtml(change.value)
      const lines = escaped.split('\n')
      
      return lines
        .map((line, i) => {
          if (i === lines.length - 1 && line === '') return ''
          
          const lineNum = change.lineNumbers
          let prefix = ''
          
          if (lineNum) {
            if (change.type === 'remove') {
              prefix = `<span class="line-num old">${lineNum.old}</span>`
            } else if (change.type === 'add') {
              prefix = `<span class="line-num new">${lineNum.new}</span>`
            } else {
              prefix = `<span class="line-num">${lineNum.old}</span>`
            }
          }
          
          return `<div class="${className}">${prefix}${line}</div>`
        })
        .join('\n')
    })
    .join('\n')
}

// Utility to escape HTML
function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  
  return text.replace(/[&<>"']/g, m => map[m])
}

// Calculate similarity percentage between two strings
export function calculateSimilarity(oldText: string, newText: string): number {
  const diff = textDiff(oldText, newText, 'chars')
  const totalChars = Math.max(oldText.length, newText.length)
  
  if (totalChars === 0) return 100
  
  const changedChars = diff.changes
    .filter(c => c.type !== 'equal')
    .reduce((sum, c) => sum + c.value.length, 0)
  
  return Math.round(((totalChars - changedChars) / totalChars) * 100)
}

// Smart diff that chooses the best mode based on content
export function smartDiff(oldValue: any, newValue: any): DiffResult | ArrayDiff<any> | ObjectDiff {
  // Handle null/undefined
  if (oldValue == null || newValue == null) {
    return textDiff(String(oldValue || ''), String(newValue || ''))
  }
  
  // Arrays
  if (Array.isArray(oldValue) && Array.isArray(newValue)) {
    return arrayDiff(oldValue, newValue)
  }
  
  // Objects
  if (typeof oldValue === 'object' && typeof newValue === 'object') {
    return objectDiff(oldValue, newValue)
  }
  
  // Numbers, booleans, strings
  const oldStr = String(oldValue)
  const newStr = String(newValue)
  
  // For short strings, use character diff
  if (oldStr.length < 50 && newStr.length < 50) {
    return textDiff(oldStr, newStr, 'chars')
  }
  
  // For longer strings, use word diff
  if (oldStr.includes(' ') || newStr.includes(' ')) {
    return textDiff(oldStr, newStr, 'words')
  }
  
  // Default to line diff
  return textDiff(oldStr, newStr, 'lines')
}