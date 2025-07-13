# Task 13: Diff Viewer and Change Management

## Current State
- Scene browser is implemented
- Analysis service can generate plans
- No UI for viewing/managing changes
- No diff visualization

## Objective
Implement a comprehensive diff viewer for reviewing and managing proposed changes from analysis plans.

## Requirements

### Analysis Plans Page

1. **src/pages/Analysis/index.tsx** - Main analysis page:
   ```typescript
   // Features:
   - List of analysis plans
   - Plan creation button
   - Filter by status
   - Sort by date
   - Quick stats
   
   // Sections:
   - Active plans
   - Completed plans
   - Plan templates
   ```

### Plan List Component

2. **src/pages/Analysis/components/PlanList.tsx**:
   ```typescript
   // Features:
   - Plan cards with summary
   - Status indicators
   - Progress for active plans
   - Quick actions
   - Pagination
   
   // Plan card shows:
   - Name and description
   - Created date
   - Scene count
   - Change count
   - Status badge
   ```

### Plan Detail Page

3. **src/pages/Analysis/PlanDetail/index.tsx**:
   ```typescript
   // Features:
   - Plan overview header
   - Scene change list
   - Bulk actions toolbar
   - Apply changes button
   - Export plan
   
   // Layout:
   - Split view (scenes list + changes)
   - Responsive design
   - Keyboard navigation
   ```

### Change Diff Viewer

4. **src/pages/Analysis/components/DiffViewer/index.tsx**:
   ```typescript
   // Main diff viewer component
   // Features:
   - Side-by-side comparison
   - Inline diff mode
   - Syntax highlighting
   - Line numbers
   - Expand/collapse sections
   
   // Props:
   - change: ProposedChange
   - viewMode: 'split' | 'unified'
   - onAccept: () => void
   - onReject: () => void
   - onEdit: (value: any) => void
   ```

### Specialized Diff Components

5. **src/pages/Analysis/components/DiffViewer/TextDiff.tsx**:
   ```typescript
   // For text fields (title, details)
   // Features:
   - Character-level diff
   - Word-level diff
   - Whitespace visualization
   - Copy buttons
   ```

6. **src/pages/Analysis/components/DiffViewer/ListDiff.tsx**:
   ```typescript
   // For arrays (performers, tags)
   // Features:
   - Added items (green)
   - Removed items (red)
   - Unchanged items
   - Reorder visualization
   ```

7. **src/pages/Analysis/components/DiffViewer/MetadataDiff.tsx**:
   ```typescript
   // For complex metadata
   // Features:
   - Nested object diff
   - Property changes
   - Type changes
   - JSON view option
   ```

### Change Management Components

8. **src/pages/Analysis/components/ChangeControls.tsx**:
   ```typescript
   // Controls for each change
   // Features:
   - Accept/Reject buttons
   - Edit proposed value
   - Confidence indicator
   - AI reasoning display
   - Undo/redo
   ```

9. **src/pages/Analysis/components/BulkActions.tsx**:
   ```typescript
   // Bulk operations toolbar
   // Actions:
   - Accept all changes
   - Reject all changes
   - Accept by type
   - Accept by confidence
   - Filter changes
   ```

### Scene Changes View

10. **src/pages/Analysis/components/SceneChanges.tsx**:
    ```typescript
    // Shows all changes for one scene
    // Features:
    - Scene preview
    - Grouped changes
    - Collapse/expand
    - Quick navigation
    - Change statistics
    ```

### Interactive Editing

11. **src/pages/Analysis/components/InlineEditor.tsx**:
    ```typescript
    // Inline editing for proposed values
    // Features:
    - Edit in place
    - Validation
    - Auto-save
    - Cancel changes
    - Format preservation
    ```

### Plan Application

12. **src/pages/Analysis/components/ApplyPlanModal.tsx**:
    ```typescript
    // Modal for applying changes
    // Features:
    - Summary of changes
    - Confirmation step
    - Progress tracking
    - Error handling
    - Partial application
    ```

### Hooks and State

13. **src/pages/Analysis/hooks/usePlanDetail.ts**:
    ```typescript
    // Hook for plan data
    export function usePlanDetail(planId: number) {
      // Fetch plan
      // Fetch changes
      // Group by scene
      // Track acceptance state
    }
    ```

14. **src/pages/Analysis/hooks/useChangeManager.ts**:
    ```typescript
    // Hook for managing changes
    export function useChangeManager(planId: number) {
      // Accept/reject changes
      // Edit values
      // Track modifications
      // Bulk operations
      // Undo/redo support
    }
    ```

### Diff Algorithms

15. **src/pages/Analysis/utils/diff.ts**:
    ```typescript
    // Diff calculation utilities
    - textDiff(old: string, new: string): DiffResult
    - arrayDiff<T>(old: T[], new: T[]): ArrayDiff<T>
    - objectDiff(old: object, new: object): ObjectDiff
    - formatDiffHtml(diff: DiffResult): string
    ```

### Styling

16. **src/pages/Analysis/styles/diff.scss**:
    ```scss
    // Diff viewer styles
    - Addition highlighting (green)
    - Deletion highlighting (red)
    - Line numbers
    - Syntax highlighting
    - Responsive layout
    ```

### Export Functionality

17. **src/pages/Analysis/components/ExportPlan.tsx**:
    ```typescript
    // Export plan options
    // Formats:
    - JSON (full plan)
    - CSV (summary)
    - Markdown (report)
    - PDF (with styling)
    ```

## Expected Outcome

After completing this task:
- Complete diff viewing interface
- Changes can be reviewed efficiently
- Individual changes can be accepted/rejected
- Bulk operations work
- Changes can be edited inline
- Plans can be applied with tracking

## Integration Points
- Uses analysis API endpoints
- Integrates with job system
- Updates scene data after apply
- WebSocket for progress
- Works with scene browser

## Success Criteria
1. Diff viewer clearly shows changes
2. Accept/reject works per change
3. Bulk actions apply correctly
4. Inline editing saves properly
5. Progress tracks during apply
6. Keyboard navigation works
7. Performance with many changes
8. Export formats are useful
9. Mobile responsive design