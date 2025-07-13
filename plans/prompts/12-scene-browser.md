# Task 12: Scene Browser Implementation

## Current State
- UI components are implemented
- API client is configured
- No scene browsing functionality
- No integration between components

## Objective
Implement a full-featured scene browser with search, filtering, pagination, and multiple view modes.

## Requirements

### Main Scene Browser Page

1. **src/pages/Scenes/index.tsx** - Main scenes page:
   ```typescript
   // Features:
   - Scene grid/list view
   - Search and filters
   - Pagination
   - View mode toggle
   - Sync button
   - Selection mode
   
   // State management:
   - Filter state in URL params
   - View preferences in localStorage
   - Selected scenes in component state
   ```

### Scene List Container

2. **src/pages/Scenes/components/SceneListContainer.tsx**:
   ```typescript
   // Features:
   - Data fetching with React Query
   - Filter application
   - Sort handling
   - Pagination control
   - Loading/error states
   
   // Props:
   - filters: SceneFilters
   - viewMode: 'grid' | 'list'
   - onSceneSelect: (scene: Scene) => void
   ```

### Search and Filter Bar

3. **src/pages/Scenes/components/SearchBar.tsx**:
   ```typescript
   // Features:
   - Search input with debounce
   - Quick filter chips
   - Advanced filter toggle
   - Clear all filters
   - Search suggestions
   
   // Integration:
   - Updates URL parameters
   - Syncs with filter panel
   ```

### Advanced Filter Panel

4. **src/pages/Scenes/components/AdvancedFilters.tsx**:
   ```typescript
   // Filter options:
   - Performers (multi-select)
   - Tags (multi-select)
   - Studios (single-select)
   - Date range (created/scene date)
   - Organized status
   - Has details
   - Path contains
   
   // Features:
   - Collapsible sections
   - Filter counts
   - Reset per section
   - Save filter presets
   ```

### View Mode Components

5. **src/pages/Scenes/components/GridView.tsx**:
   ```typescript
   // Features:
   - Responsive grid layout
   - Thumbnail previews
   - Hover details
   - Quick actions
   - Lazy loading images
   - Virtual scrolling for performance
   
   // Grid sizes:
   - Small (6 cols)
   - Medium (4 cols)
   - Large (3 cols)
   ```

6. **src/pages/Scenes/components/ListView.tsx**:
   ```typescript
   // Features:
   - Table layout
   - Sortable columns
   - Inline actions
   - Row selection
   - Expandable rows
   
   // Columns:
   - Thumbnail
   - Title
   - Studio
   - Performers
   - Tags
   - Date
   - Actions
   ```

### Scene Actions

7. **src/pages/Scenes/components/SceneActions.tsx**:
   ```typescript
   // Single scene actions:
   - View details
   - Analyze
   - Resync
   - Edit metadata
   - Copy ID
   
   // Bulk actions:
   - Analyze selected
   - Add tag to selected
   - Remove tag from selected
   - Export selected
   ```

### Data Fetching Hooks

8. **src/pages/Scenes/hooks/useScenes.ts**:
   ```typescript
   // React Query hook for scenes
   export function useScenes(params: SceneQueryParams) {
     return useQuery({
       queryKey: ['scenes', params],
       queryFn: () => apiClient.getScenes(params),
       keepPreviousData: true,
     });
   }
   ```

9. **src/pages/Scenes/hooks/useSceneFilters.ts**:
   ```typescript
   // Hook for managing filter state
   export function useSceneFilters() {
     // Parse from URL
     // Update URL on change
     // Provide filter values
     // Reset functionality
   }
   ```

### Scene Detail Modal

10. **src/pages/Scenes/components/SceneDetailModal.tsx**:
    ```typescript
    // Features:
    - Full scene information
    - Tabbed interface
    - Edit mode
    - Related scenes
    - Analysis history
    - Action toolbar
    
    // Tabs:
    - Overview
    - Files/Paths
    - Analysis
    - History
    ```

### Sync Integration

11. **src/pages/Scenes/components/SyncButton.tsx**:
    ```typescript
    // Features:
    - Sync status indicator
    - Dropdown menu
    - Full sync option
    - Incremental sync option
    - Last sync time
    - Progress modal
    ```

### Performance Optimizations

12. **src/pages/Scenes/hooks/useVirtualization.ts**:
    ```typescript
    // Virtual scrolling for large lists
    // Features:
    - Dynamic row heights
    - Smooth scrolling
    - Memory efficient
    - Responsive to window resize
    ```

### State Management

13. **src/store/slices/scenes.ts** - Scenes state:
    ```typescript
    interface ScenesState {
      selectedScenes: Set<string>;
      viewMode: 'grid' | 'list';
      gridSize: 'small' | 'medium' | 'large';
      
      selectScene: (id: string) => void;
      deselectScene: (id: string) => void;
      clearSelection: () => void;
      setViewMode: (mode: 'grid' | 'list') => void;
      setGridSize: (size: 'small' | 'medium' | 'large') => void;
    }
    ```

### Utility Functions

14. **src/pages/Scenes/utils/filters.ts**:
    ```typescript
    // Filter utilities:
    - buildFilterQuery(filters: SceneFilters): URLSearchParams
    - parseFilterQuery(params: URLSearchParams): SceneFilters
    - getActiveFilterCount(filters: SceneFilters): number
    - getDefaultFilters(): SceneFilters
    ```

15. **src/pages/Scenes/utils/export.ts**:
    ```typescript
    // Export functionality:
    - exportToCSV(scenes: Scene[]): void
    - exportToJSON(scenes: Scene[]): void
    - generateExportData(scenes: Scene[]): ExportData
    ```

## Expected Outcome

After completing this task:
- Full scene browsing interface works
- Search and filtering is responsive
- Multiple view modes available
- Performance is good with many scenes
- Selection and bulk actions work
- Integration with sync and analysis

## Integration Points
- Uses scene API endpoints
- Integrates with job system for sync
- Links to analysis functionality
- Uses common UI components
- Updates URL for shareable filters

## Success Criteria
1. Can browse all scenes
2. Search works with debounce
3. Filters apply correctly
4. Pagination works smoothly
5. Grid/list views toggle
6. Selection mode works
7. Bulk actions execute
8. Performance with 1000+ scenes
9. URL updates with filters