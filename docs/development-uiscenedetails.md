# Scene Details UI Development Guide

This document provides guidance for modifying and maintaining the scene details UI components in the Stashhog application.

## Overview

The scene details functionality is implemented across multiple components and pages. Understanding the relationship between these components is crucial for successful modifications.

## Component Architecture

### 1. SceneDetailModal Component
**Location**: `/frontend/src/pages/scenes/components/SceneDetailModal.tsx`

**Purpose**: 
- Modal popup that displays detailed scene information
- Used when clicking on a scene from the scene browser grid/list views
- Contains tabs for Overview, Files/Paths, Markers, Analysis, and History
- Provides action buttons in the footer

**Key Features**:
- Fetches full scene details via API
- Handles scene analysis
- Integrates with settings store for Stash URL
- Provides edit functionality via SceneEditModal

**Common Modifications**:
- Adding new action buttons: Add to the `footer` prop array (lines 582-613)
- Adding new tabs: Create a new `TabPane` component and corresponding render function
- Modifying scene data display: Update the relevant render functions (e.g., `renderOverviewTab`)

### 2. SceneDetail Component (Standalone)
**Location**: `/frontend/src/components/scenes/SceneDetail.tsx`

**Purpose**:
- Standalone component for displaying scene details
- Used in different contexts where a modal is not appropriate
- Similar functionality to SceneDetailModal but with different layout

**Key Features**:
- Card-based layout with actions sidebar
- Direct API endpoint access functionality
- Integration with Stash URL for external viewing

### 3. SceneDetail Page
**Location**: `/frontend/src/pages/scenes/SceneDetail.tsx`

**Purpose**:
- Full page view for scene details
- Accessed via direct URL routing (e.g., `/scenes/:id`)
- Uses similar data fetching patterns as the modal

## Common Issues and Solutions

### Issue 1: Button Not Appearing
**Problem**: Adding a button to the modal footer doesn't show up in the UI.

**Common Causes**:
1. Missing icon import from `@ant-design/icons`
2. Incorrect button placement in the footer array
3. Missing handler function

**Solution**:
```typescript
// 1. Import the icon
import { ApiOutlined } from '@ant-design/icons';

// 2. Add the handler function
const handleOpenInAPI = () => {
  const apiUrl = `${window.location.origin}/api/scenes/${scene.id}`;
  window.open(apiUrl, '_blank');
};

// 3. Add button to footer array
footer={[
  // ... existing buttons
  <Button
    key="api"
    icon={<ApiOutlined />}
    onClick={handleOpenInAPI}
  >
    Open in API
  </Button>,
  // ... other buttons
]}
```

### Issue 2: Data Not Displaying
**Problem**: Scene data fields are not showing in the UI.

**Common Causes**:
1. API response structure mismatch
2. Incorrect property access
3. Missing null/undefined checks

**Solution**:
- Always use optional chaining: `scene?.property`
- Provide fallback values: `scene.title || 'Untitled'`
- Check the API response structure in browser DevTools

## Adding New Features

### Adding a New Tab
1. Import any necessary icons
2. Create a render function for the tab content:
   ```typescript
   const renderNewTab = () => (
     <div>Tab content here</div>
   );
   ```
3. Add the TabPane to the Tabs component:
   ```typescript
   <TabPane
     tab={<span><IconName /> Tab Title</span>}
     key="unique-key"
   >
     {renderNewTab()}
   </TabPane>
   ```

### Adding a New Action Button
1. Import the icon from `@ant-design/icons`
2. Create the handler function
3. Add the button to the appropriate location:
   - Modal: Add to the `footer` array
   - Standalone component: Add to the actions Space/Card
   - Page: Add to the button group

## Data Flow

1. **Scene Data**: Fetched using React Query hooks
   - Basic scene data passed as prop
   - Full details fetched when component mounts
   - Cached for performance

2. **Settings**: Accessed via Zustand store
   - Used for Stash URL configuration
   - Loaded on component mount if not already available

3. **Analysis Results**: Separate API endpoint
   - Fetched independently from scene details
   - Displayed in the Analysis tab

## Best Practices

1. **Always handle loading states**: Use the `isLoading` flag from React Query
2. **Provide meaningful fallbacks**: Use 'N/A' or appropriate defaults for missing data
3. **Test with different data states**: Empty data, partial data, full data
4. **Maintain consistency**: Follow existing patterns for new features
5. **Check all scene detail components**: Changes often need to be made in multiple places

## File Reference

| File | Purpose | When to Modify |
|------|---------|----------------|
| `/frontend/src/pages/scenes/components/SceneDetailModal.tsx` | Modal popup for scene details | Adding features to the modal view |
| `/frontend/src/components/scenes/SceneDetail.tsx` | Reusable scene detail component | Modifying standalone scene displays |
| `/frontend/src/pages/scenes/SceneDetail.tsx` | Full page scene detail view | Changing the dedicated scene page |
| `/frontend/src/components/scenes/SceneEditModal.tsx` | Edit scene modal | Modifying scene editing functionality |
| `/frontend/src/types/models.ts` | TypeScript type definitions | Adding new scene properties |
| `/frontend/src/services/api.ts` | API client | Changing API endpoints |

## Testing Checklist

When modifying scene details UI:

- [ ] Test in modal view (from scene browser)
- [ ] Test in page view (direct URL)
- [ ] Test with scenes that have all data fields
- [ ] Test with scenes missing optional data
- [ ] Test action buttons work correctly
- [ ] Verify responsive behavior
- [ ] Check loading states
- [ ] Ensure error states are handled

## Common Pitfalls

1. **Forgetting to import icons**: Always import icons from `@ant-design/icons`
2. **Not checking multiple components**: Scene details exist in multiple places
3. **Assuming data exists**: Always use optional chaining and provide fallbacks
4. **Not testing edge cases**: Test with minimal and maximal data
5. **Ignoring TypeScript errors**: Fix type issues rather than using `any`

## Related Documentation

- [Ant Design Components](https://ant.design/components/overview)
- [React Query Documentation](https://react-query.tanstack.com/)
- [Frontend Architecture](./frontend-architecture.md)