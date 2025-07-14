# Task 14: Task Scheduler Implementation

## Current State
- Manual sync and analysis operations work
- APScheduler configured in backend
- No UI for scheduling tasks
- No schedule management

## Objective
Implement a task scheduling interface that allows users to create, manage, and monitor scheduled tasks for sync and analysis operations.

## Requirements

### Scheduler Page

1. **src/pages/Scheduler/index.tsx** - Main scheduler page:
   ```typescript
   // Features:
   - List of scheduled tasks
   - Create new schedule button
   - Enable/disable tasks
   - Run history
   - Calendar view
   
   // Sections:
   - Active schedules
   - Task history
   - Upcoming runs
   ```

### Schedule List

2. **src/pages/Scheduler/components/ScheduleList.tsx**:
   ```typescript
   // Features:
   - Task cards
   - Status toggles
   - Next run time
   - Last run status
   - Quick actions
   
   // Task info:
   - Name and description
   - Schedule expression
   - Task type
   - Configuration
   - Run statistics
   ```

### Create Schedule Modal

3. **src/pages/Scheduler/components/CreateScheduleModal.tsx**:
   ```typescript
   // Features:
   - Task type selection
   - Schedule builder
   - Configuration options
   - Preview next runs
   - Validation
   
   // Steps:
   1. Select task type
   2. Configure task
   3. Set schedule
   4. Review and create
   ```

### Schedule Builder

4. **src/pages/Scheduler/components/ScheduleBuilder.tsx**:
   ```typescript
   // Features:
   - Visual cron builder
   - Common presets
   - Natural language input
   - Cron expression input
   - Next run preview
   
   // Presets:
   - Every hour
   - Daily at midnight
   - Weekly on Sunday
   - Monthly on 1st
   - Custom
   ```

### Task Configuration

5. **src/pages/Scheduler/components/TaskConfigurator.tsx**:
   ```typescript
   // Dynamic config based on task type
   
   // Sync task options:
   - Full or incremental
   - Entity types
   - Force update
   
   // Analysis task options:
   - Scene filters
   - Analysis options
   - Plan name template
   - Auto-apply threshold
   ```

### Calendar View

6. **src/pages/Scheduler/components/CalendarView.tsx**:
   ```typescript
   // Features:
   - Monthly calendar
   - Scheduled runs marked
   - Completed runs shown
   - Click for details
   - Navigate months
   
   // Uses:
   - Ant Design Calendar
   - Custom event rendering
   ```

### Run History

7. **src/pages/Scheduler/components/RunHistory.tsx**:
   ```typescript
   // Features:
   - Execution history table
   - Status filtering
   - Duration stats
   - Error details
   - Link to job details
   
   // Columns:
   - Task name
   - Run time
   - Duration
   - Status
   - Result summary
   ```

### Schedule Details

8. **src/pages/Scheduler/components/ScheduleDetail.tsx**:
   ```typescript
   // Detailed view of schedule
   // Features:
   - Edit schedule
   - View configuration
   - Run history chart
   - Manual trigger
   - Delete schedule
   
   // Statistics:
   - Success rate
   - Average duration
   - Last 10 runs
   ```

### Cron Expression Helper

9. **src/pages/Scheduler/components/CronHelper.tsx**:
   ```typescript
   // Features:
   - Expression breakdown
   - Field explanations
   - Validation
   - Examples
   - Cheat sheet
   ```

### Natural Language Parser

10. **src/pages/Scheduler/utils/naturalLanguage.ts**:
    ```typescript
    // Parse natural language to cron
    // Examples:
    - "every day at 3am" -> "0 3 * * *"
    - "every Monday" -> "0 0 * * 1"
    - "twice a day" -> "0 0,12 * * *"
    - "every 2 hours" -> "0 */2 * * *"
    ```

### API Integration

11. **src/pages/Scheduler/hooks/useSchedules.ts**:
    ```typescript
    // Hooks for schedule management
    
    export function useSchedules() {
      // List schedules
      // Create schedule
      // Update schedule
      // Delete schedule
      // Toggle enabled
    }
    
    export function useScheduleHistory(scheduleId?: number) {
      // Get run history
      // Filter by status
      // Pagination
    }
    ```

### Schedule Types

12. **src/pages/Scheduler/types.ts**:
    ```typescript
    interface Schedule {
      id: number;
      name: string;
      task_type: 'sync' | 'analysis' | 'cleanup';
      schedule: string; // cron expression
      config: Record<string, any>;
      enabled: boolean;
      last_run?: Date;
      next_run?: Date;
      created_at: Date;
    }
    
    interface ScheduleRun {
      id: number;
      schedule_id: number;
      started_at: Date;
      completed_at?: Date;
      status: 'success' | 'failed' | 'running';
      job_id?: string;
      result?: any;
      error?: string;
    }
    ```

### Notifications

13. **src/pages/Scheduler/components/NotificationSettings.tsx**:
    ```typescript
    // Configure notifications
    // Options:
    - Email on failure
    - Email on success
    - In-app notifications
    - Webhook URL
    ```

### Advanced Features

14. **src/pages/Scheduler/components/DependencyChain.tsx**:
    ```typescript
    // Chain tasks together
    // Features:
    - Task dependencies
    - Conditional execution
    - Failure handling
    - Visual flow editor
    ```

15. **src/pages/Scheduler/components/ScheduleMonitor.tsx**:
    ```typescript
    // Real-time monitoring
    // Features:
    - Currently running tasks
    - Live logs
    - Resource usage
    - Cancel capability
    ```

## Expected Outcome

After completing this task:
- Complete scheduling interface
- Tasks can be scheduled with cron
- Visual schedule builder works
- History is tracked
- Calendar view shows runs
- Manual triggers work

## Integration Points
- Uses scheduler API endpoints
- Triggers jobs via job system
- Shows job progress
- Updates on completion
- Integrates with notifications

## Success Criteria
1. Schedules can be created/edited
2. Cron builder is intuitive
3. Natural language works
4. Calendar view is useful
5. History shows all runs
6. Manual trigger works
7. Enable/disable works
8. Validation prevents errors
9. Mobile responsive