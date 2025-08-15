# Navigation Issue Fix - Agent Handoff

## Application Overview
StashHog is a React-based web application for managing and organizing media content. It integrates with a Stash server to provide enhanced functionality including job monitoring, scene analysis, and sync operations. The frontend is built with React 18, TypeScript, Ant Design UI components, and React Router v7.

## Current Issue Status
**PARTIALLY RESOLVED** - Navigation from the Jobs Monitor page (`/jobs`) to other pages was completely broken. Users could click navigation links, the URL would change, but the page content would remain stuck on Jobs Monitor. Through debugging, we've identified the root cause and have a working temporary fix in place.

## Problem Summary
When on the Jobs Monitor page, clicking any navigation menu item would:
- ✅ Change the URL correctly
- ✅ Update menu highlighting
- ❌ NOT change the page content (remained on Jobs Monitor)

## Root Cause Identified
The issue is caused by either:
1. **ActiveJobsSection component** (most likely) - A child component of JobMonitor that also uses WebSocket
2. **React.StrictMode** - May be contributing through double-rendering effects
3. **Or both in combination**

Currently, with both disabled, navigation works perfectly.

## Current Temporary Fix (In Place)
The following debugging changes are currently active and make navigation work:

1. **ActiveJobsSection is commented out** in `/frontend/src/pages/jobs/JobMonitor.tsx` (lines 928-933)
2. **React.StrictMode is commented out** in `/frontend/src/main.tsx` (lines 31-44)
3. **WebSocket Manager singleton pattern** has been implemented (keep this - it's good architecture)
4. **Location-based cleanup** added to JobMonitor (lines 112-121)

## Your Task
Fix the navigation issue properly so that:
1. ActiveJobsSection can be re-enabled
2. React.StrictMode can be re-enabled
3. Navigation works correctly from Jobs Monitor page
4. All WebSocket connections are properly managed

## Suggested Approach

### Step 1: Isolate the Exact Cause
1. Re-enable React.StrictMode (uncomment in `/frontend/src/main.tsx`)
2. Keep ActiveJobsSection disabled
3. Build and test navigation
4. If navigation works → ActiveJobsSection is the sole problem
5. If navigation breaks → Both contribute to the issue

### Step 2: Fix ActiveJobsSection
File: `/frontend/src/pages/jobs/ActiveJobsSection.tsx`

Likely issues to check:
- WebSocket connection cleanup on unmount
- Event handlers that might prevent default navigation
- State updates after component unmount
- Consider if it needs its own cleanup similar to JobMonitor's location check

The component currently uses: `const { lastMessage } = useWebSocket('/api/jobs/ws');`

### Step 3: Verify WebSocket Manager is Working
The new WebSocket manager (`/frontend/src/services/websocketManager.ts`) ensures only one connection per endpoint. This is good architecture and should be kept. Verify that:
- ActiveJobsSection properly uses the refactored `useWebSocket` hook
- Cleanup/unsubscribe happens on unmount
- No duplicate connections are created

### Step 4: Test Complete Fix
1. Re-enable both ActiveJobsSection and React.StrictMode
2. Test navigation from Jobs Monitor
3. Test with active jobs running
4. Test after jobs complete
5. Check browser console for errors

## Key Files and Directories

### Primary Files to Review/Fix:
- `/frontend/src/pages/jobs/ActiveJobsSection.tsx` - **Main suspect, needs fixing**
- `/frontend/src/pages/jobs/JobMonitor.tsx` - Has temporary fixes in place
- `/frontend/src/main.tsx` - StrictMode disabled here

### Supporting Files:
- `/frontend/src/hooks/useWebSocket.ts` - Refactored to use manager (good)
- `/frontend/src/services/websocketManager.ts` - New singleton manager (keep)
- @plans/navigation-issue.md - Complete investigation history and findings

### Build/Test Commands:
```bash
cd frontend
npm run build  # Build the application
npm run lint   # Check for linting issues
npm run dev    # Run development server
```

## Important Context
- The application works perfectly on all other pages
- Only the Jobs Monitor page has navigation issues
- Both JobMonitor and ActiveJobsSection connect to the same WebSocket endpoint: `/api/jobs/ws`
- The WebSocket manager singleton was created to prevent duplicate connections
- Navigation may work briefly while jobs are actively running, but breaks when idle

## Success Criteria
- [ ] Navigation works from Jobs Monitor to all other pages
- [ ] ActiveJobsSection is re-enabled and functional
- [ ] React.StrictMode is re-enabled
- [ ] No console errors during navigation
- [ ] WebSocket connections are properly managed
- [ ] No performance regressions

## Additional Notes
- The WebSocket manager implementation is solid and should be kept
- The issue has been narrowed down significantly - focus on ActiveJobsSection
- Test thoroughly with both active and completed jobs
- Document any additional findings in @plans/navigation-issue.md

Good luck! The debugging work has already isolated the problem - you just need to fix ActiveJobsSection's lifecycle management.