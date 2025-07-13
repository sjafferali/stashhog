# Task 10: Frontend Setup and Core Configuration

## Current State
- Backend API is complete
- Basic frontend structure exists
- No actual React application
- No routing or state management

## Objective
Set up the React frontend with TypeScript, configure build tools, implement routing, state management, and core application structure.

## Requirements

### Project Configuration

1. **package.json** - Complete dependencies:
   ```json
   {
     "name": "stashhog-frontend",
     "version": "0.1.0",
     "dependencies": {
       "react": "^18.2.0",
       "react-dom": "^18.2.0",
       "react-router-dom": "^6.20.0",
       "antd": "^5.12.0",
       "@ant-design/icons": "^5.2.6",
       "zustand": "^4.4.7",
       "axios": "^1.6.2",
       "dayjs": "^1.11.10",
       "react-query": "^3.39.3",
       "react-use-websocket": "^4.5.0",
       "classnames": "^2.3.2"
     },
     "devDependencies": {
       "@types/react": "^18.2.0",
       "@types/react-dom": "^18.2.0",
       "@vitejs/plugin-react": "^4.2.0",
       "typescript": "^5.3.0",
       "vite": "^5.0.0",
       "eslint": "^8.55.0",
       "@typescript-eslint/eslint-plugin": "^6.13.0",
       "@typescript-eslint/parser": "^6.13.0",
       "prettier": "^3.1.0",
       "sass": "^1.69.0"
     }
   }
   ```

2. **tsconfig.json** - TypeScript configuration:
   ```json
   {
     "compilerOptions": {
       "target": "ES2020",
       "useDefineForClassFields": true,
       "lib": ["ES2020", "DOM", "DOM.Iterable"],
       "module": "ESNext",
       "skipLibCheck": true,
       "moduleResolution": "bundler",
       "allowImportingTsExtensions": true,
       "resolveJsonModule": true,
       "isolatedModules": true,
       "noEmit": true,
       "jsx": "react-jsx",
       "strict": true,
       "noUnusedLocals": true,
       "noUnusedParameters": true,
       "noFallthroughCasesInSwitch": true,
       "paths": {
         "@/*": ["./src/*"]
       }
     }
   }
   ```

3. **vite.config.ts** - Vite configuration:
   ```typescript
   import { defineConfig } from 'vite';
   import react from '@vitejs/plugin-react';
   import path from 'path';
   
   export default defineConfig({
     plugins: [react()],
     resolve: {
       alias: {
         '@': path.resolve(__dirname, './src'),
       },
     },
     server: {
       port: 5173,
       proxy: {
         '/api': {
           target: 'http://localhost:8000',
           changeOrigin: true,
         },
         '/ws': {
           target: 'ws://localhost:8000',
           ws: true,
         },
       },
     },
   });
   ```

### Core Application Structure

4. **src/main.tsx** - Application entry:
   ```typescript
   // Set up:
   - React root
   - React Query provider
   - Router provider
   - Ant Design config provider
   - Error boundary
   ```

5. **src/App.tsx** - Main app component:
   ```typescript
   // Components:
   - Router configuration
   - Layout wrapper
   - Auth check (if needed)
   - Global message handler
   ```

### Routing Configuration

6. **src/router/index.tsx** - Route definitions:
   ```typescript
   // Routes:
   - / - Dashboard
   - /scenes - Scene browser
   - /scenes/:id - Scene detail
   - /analysis - Analysis page
   - /analysis/plans - Plan list
   - /analysis/plans/:id - Plan detail
   - /jobs - Job monitor
   - /settings - Settings page
   - /sync - Sync management
   ```

7. **src/router/PrivateRoute.tsx** - Protected routes:
   ```typescript
   // If authentication is needed
   ```

### State Management

8. **src/store/index.ts** - Zustand store setup:
   ```typescript
   // Main store combining slices
   ```

9. **src/store/slices/app.ts** - App state:
   ```typescript
   interface AppState {
     isLoading: boolean;
     error: string | null;
     notification: Notification | null;
     setLoading: (loading: boolean) => void;
     setError: (error: string | null) => void;
     showNotification: (notification: Notification) => void;
   }
   ```

10. **src/store/slices/settings.ts** - Settings state:
    ```typescript
    interface SettingsState {
      settings: Record<string, any>;
      isLoaded: boolean;
      loadSettings: () => Promise<void>;
      updateSetting: (key: string, value: any) => Promise<void>;
    }
    ```

### API Client Setup

11. **src/services/api.ts** - Axios configuration:
    ```typescript
    // Configure:
    - Base URL
    - Request/response interceptors
    - Error handling
    - Auth headers (if needed)
    ```

12. **src/services/apiClient.ts** - API methods:
    ```typescript
    // API client class with methods for:
    - Scenes
    - Analysis
    - Jobs
    - Settings
    - Sync
    ```

### WebSocket Setup

13. **src/services/websocket.ts** - WebSocket client:
    ```typescript
    // WebSocket manager for:
    - Job progress updates
    - Real-time notifications
    - Connection management
    - Auto-reconnect
    ```

### Type Definitions

14. **src/types/models.ts** - Data models:
    ```typescript
    // TypeScript interfaces for:
    - Scene
    - Performer
    - Tag
    - Studio
    - AnalysisPlan
    - Job
    - etc.
    ```

15. **src/types/api.ts** - API types:
    ```typescript
    // Request/response types:
    - PaginatedResponse<T>
    - ApiError
    - FilterParams
    - etc.
    ```

### Layout Components

16. **src/layouts/MainLayout.tsx** - App layout:
    ```typescript
    // Main layout with:
    - Header with navigation
    - Sidebar menu
    - Content area
    - Footer
    ```

17. **src/layouts/components/Header.tsx** - Header component:
    ```typescript
    // Header with:
    - App logo/title
    - Navigation menu
    - User menu (if auth)
    - Notifications
    ```

18. **src/layouts/components/Sidebar.tsx** - Sidebar navigation:
    ```typescript
    // Sidebar with:
    - Menu items
    - Active state
    - Collapse support
    - Icons
    ```

### Utility Functions

19. **src/utils/format.ts** - Formatting utilities:
    ```typescript
    // Utilities for:
    - Date formatting
    - Number formatting
    - File size formatting
    - Duration formatting
    ```

20. **src/utils/api.ts** - API utilities:
    ```typescript
    // Utilities for:
    - Error message extraction
    - Query string building
    - Response transformation
    ```

### Styling Setup

21. **src/styles/index.scss** - Global styles:
    ```scss
    // Global styles:
    - CSS reset
    - Ant Design overrides
    - Custom variables
    - Utility classes
    ```

22. **src/styles/variables.scss** - Style variables:
    ```scss
    // Variables for:
    - Colors
    - Spacing
    - Breakpoints
    - Animations
    ```

## Expected Outcome

After completing this task:
- React app runs with hot reload
- TypeScript is properly configured
- Routing works with all pages
- State management is set up
- API client can make requests
- WebSocket connections work
- Layout renders correctly
- All types are defined

## Integration Points
- API client connects to backend
- WebSocket connects for updates
- Router handles navigation
- Store manages global state
- Types match backend models

## Success Criteria
1. `npm run dev` starts the app
2. All routes are accessible
3. No TypeScript errors
4. API proxy works correctly
5. WebSocket connects successfully
6. Layout is responsive
7. State updates properly
8. Hot reload works
9. Build completes without errors