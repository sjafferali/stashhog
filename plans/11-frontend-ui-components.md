# Task 11: Frontend UI Components Implementation

## Current State
- React app structure is set up
- Routing and state management configured
- No actual UI components implemented
- API client ready for use

## Objective
Implement reusable UI components using Ant Design, create custom components for specific features, and build a cohesive component library.

## Requirements

### Common Components

1. **src/components/common/LoadingSpinner.tsx**:
   ```typescript
   // Props:
   - size?: 'small' | 'default' | 'large'
   - text?: string
   - fullScreen?: boolean
   
   // Features:
   - Centered spinner
   - Optional loading text
   - Full screen overlay option
   ```

2. **src/components/common/ErrorBoundary.tsx**:
   ```typescript
   // Features:
   - Catch React errors
   - Display fallback UI
   - Log errors
   - Reset capability
   ```

3. **src/components/common/PageHeader.tsx**:
   ```typescript
   // Props:
   - title: string
   - subtitle?: string
   - actions?: ReactNode
   - breadcrumbs?: BreadcrumbItem[]
   
   // Features:
   - Consistent page headers
   - Action buttons
   - Breadcrumb navigation
   ```

4. **src/components/common/EmptyState.tsx**:
   ```typescript
   // Props:
   - icon?: ReactNode
   - title: string
   - description?: string
   - action?: ReactNode
   
   // Features:
   - Empty data states
   - Call-to-action buttons
   - Custom icons
   ```

5. **src/components/common/ConfirmModal.tsx**:
   ```typescript
   // Props:
   - title: string
   - content: string | ReactNode
   - onConfirm: () => Promise<void>
   - danger?: boolean
   
   // Features:
   - Confirmation dialogs
   - Loading state
   - Danger styling
   ```

### Data Display Components

6. **src/components/common/DataTable.tsx**:
   ```typescript
   // Generic table component
   // Props:
   - columns: ColumnType<T>[]
   - data: T[]
   - loading?: boolean
   - pagination?: PaginationConfig
   - onRow?: (record: T) => TableRowProps
   
   // Features:
   - Sortable columns
   - Pagination
   - Row selection
   - Responsive design
   ```

7. **src/components/common/FilterPanel.tsx**:
   ```typescript
   // Props:
   - filters: FilterConfig[]
   - values: Record<string, any>
   - onChange: (values: Record<string, any>) => void
   - onReset: () => void
   
   // Features:
   - Dynamic filter inputs
   - Collapsible sections
   - Reset functionality
   ```

8. **src/components/common/StatCard.tsx**:
   ```typescript
   // Props:
   - title: string
   - value: string | number
   - icon?: ReactNode
   - trend?: { value: number; isPositive: boolean }
   - loading?: boolean
   
   // Features:
   - Dashboard statistics
   - Trend indicators
   - Loading skeletons
   ```

### Scene Components

9. **src/components/scenes/SceneCard.tsx**:
   ```typescript
   // Props:
   - scene: Scene
   - onClick?: (scene: Scene) => void
   - actions?: SceneAction[]
   
   // Features:
   - Thumbnail preview
   - Basic metadata
   - Quick actions
   - Hover effects
   ```

10. **src/components/scenes/SceneGrid.tsx**:
    ```typescript
    // Props:
    - scenes: Scene[]
    - loading?: boolean
    - onSceneClick?: (scene: Scene) => void
    - layout?: 'grid' | 'list'
    
    // Features:
    - Grid/list view toggle
    - Responsive columns
    - Virtual scrolling
    - Selection mode
    ```

11. **src/components/scenes/SceneDetail.tsx**:
    ```typescript
    // Props:
    - scene: Scene
    - onEdit?: (field: string) => void
    - onAnalyze?: () => void
    
    // Features:
    - Full scene metadata
    - Edit capabilities
    - Related scenes
    - Action toolbar
    ```

12. **src/components/scenes/SceneFilters.tsx**:
    ```typescript
    // Props:
    - filters: SceneFilterValues
    - onChange: (filters: SceneFilterValues) => void
    - performers: Performer[]
    - tags: Tag[]
    - studios: Studio[]
    
    // Features:
    - Multi-select dropdowns
    - Date range picker
    - Search input
    - Quick filters
    ```

### Analysis Components

13. **src/components/analysis/ChangePreview.tsx**:
    ```typescript
    // Props:
    - change: ProposedChange
    - onAccept?: () => void
    - onReject?: () => void
    - onEdit?: (value: any) => void
    
    // Features:
    - Side-by-side diff
    - Confidence indicator
    - Accept/reject buttons
    - Inline editing
    ```

14. **src/components/analysis/DiffViewer.tsx**:
    ```typescript
    // Props:
    - current: any
    - proposed: any
    - type: 'text' | 'array' | 'object'
    
    // Features:
    - Syntax highlighting
    - Line-by-line diff
    - Collapsed view
    - Copy functionality
    ```

15. **src/components/analysis/PlanSummary.tsx**:
    ```typescript
    // Props:
    - plan: AnalysisPlan
    - onApply?: () => void
    - onDelete?: () => void
    
    // Features:
    - Statistics overview
    - Change breakdown
    - Action buttons
    - Status indicator
    ```

16. **src/components/analysis/SceneChangesList.tsx**:
    ```typescript
    // Props:
    - sceneChanges: SceneChanges[]
    - onSelectScene?: (sceneId: string) => void
    - selectedSceneId?: string
    
    // Features:
    - Grouped by scene
    - Change counts
    - Expand/collapse
    - Bulk selection
    ```

### Job Components

17. **src/components/jobs/JobCard.tsx**:
    ```typescript
    // Props:
    - job: Job
    - onCancel?: () => void
    - onRetry?: () => void
    - compact?: boolean
    
    // Features:
    - Progress bar
    - Status icon
    - Time elapsed
    - Action buttons
    ```

18. **src/components/jobs/JobProgress.tsx**:
    ```typescript
    // Props:
    - jobId: string
    - onComplete?: (result: any) => void
    - showDetails?: boolean
    
    // Features:
    - Real-time updates
    - Progress animation
    - Log messages
    - Cancel button
    ```

19. **src/components/jobs/JobList.tsx**:
    ```typescript
    // Props:
    - jobs: Job[]
    - onJobClick?: (job: Job) => void
    - showFilters?: boolean
    
    // Features:
    - Status filtering
    - Type filtering
    - Auto-refresh
    - Pagination
    ```

### Form Components

20. **src/components/forms/SettingsForm.tsx**:
    ```typescript
    // Props:
    - settings: Settings
    - onSave: (settings: Settings) => Promise<void>
    - onTest?: (type: 'stash' | 'openai') => Promise<void>
    
    // Features:
    - Grouped sections
    - Validation
    - Test connections
    - Save indicator
    ```

21. **src/components/forms/AnalysisOptionsForm.tsx**:
    ```typescript
    // Props:
    - options: AnalysisOptions
    - onChange: (options: AnalysisOptions) => void
    - showAdvanced?: boolean
    
    // Features:
    - Option toggles
    - Advanced settings
    - Tooltips
    - Presets
    ```

### Utility Components

22. **src/components/common/CopyButton.tsx**:
    ```typescript
    // Props:
    - text: string
    - size?: 'small' | 'default'
    
    // Features:
    - Click to copy
    - Success feedback
    - Tooltip
    ```

23. **src/components/common/JsonViewer.tsx**:
    ```typescript
    // Props:
    - data: any
    - collapsed?: boolean
    - theme?: 'light' | 'dark'
    
    // Features:
    - Syntax highlighting
    - Expand/collapse
    - Search
    - Copy functionality
    ```

24. **src/components/common/TagList.tsx**:
    ```typescript
    // Props:
    - tags: string[] | Tag[]
    - editable?: boolean
    - onAdd?: (tag: string) => void
    - onRemove?: (tag: string) => void
    
    // Features:
    - Tag display
    - Add/remove tags
    - Auto-complete
    - Color coding
    ```

## Expected Outcome

After completing this task:
- All UI components are implemented
- Components are reusable and typed
- Ant Design is properly integrated
- Components handle loading/error states
- Responsive design works

## Integration Points
- Components use API client
- State management via Zustand
- WebSocket for real-time updates
- React Query for data fetching
- TypeScript for type safety

## Success Criteria
1. All components render without errors
2. Props are properly typed
3. Loading states work correctly
4. Error states display properly
5. Components are responsive
6. Interactions feel smooth
7. Accessibility is considered
8. Components are documented
9. No console warnings