# Jobs vs Daemons vs Scheduled Tasks: When to Use Each

This guide explains the differences between Jobs, Workflow Jobs, Daemons, and Scheduled Tasks in StashHog, helping you choose the right tool for your task.

## Overview

StashHog provides four distinct mechanisms for executing tasks:

1. **Jobs** - Single-purpose, finite tasks
2. **Workflow Jobs** - Multi-step orchestration jobs
3. **Scheduled Tasks** - Cron-based periodic jobs
4. **Daemons** - Continuous, long-running processes

## Jobs

### What are Jobs?

Jobs are discrete, finite tasks that:
- Have a clear start and end
- Run once per invocation
- Track progress from 0% to 100%
- Report completion status (COMPLETED, FAILED, CANCELLED)

### When to Use Jobs

Use Jobs when you need to:
- Process a batch of items
- Perform one-time operations
- Execute tasks with measurable progress
- Run operations that complete in minutes to hours

### Examples

- Scene synchronization (`SYNC_SCENES`)
- File analysis (`ANALYSIS`)
- Cleanup operations (`CLEANUP`)
- Metadata generation (`STASH_GENERATE`)

### Key Features

- Progress tracking with percentage and message
- Cancellation support
- Result storage in metadata
- Parent-child job relationships (subjobs)
- WebSocket real-time updates

## Workflow Jobs

### What are Workflow Jobs?

Workflow Jobs are specialized Jobs that:
- Orchestrate multiple steps
- Create and manage subjobs
- Track complex multi-phase operations
- Provide step-by-step progress

### When to Use Workflow Jobs

Use Workflow Jobs when you need to:
- Coordinate multiple related jobs
- Execute operations in sequence
- Handle complex pipelines
- Track progress across multiple phases

### Examples

- Processing new scenes (download → extract → analyze → import)
- Multi-step data migrations
- Complex import/export operations

### Key Features

- Step tracking in metadata
- Subjob creation and monitoring
- Conditional step execution
- Rollback capabilities

## Scheduled Tasks

### What are Scheduled Tasks?

Scheduled Tasks are Jobs that:
- Run on a schedule (cron expressions)
- Execute automatically at specified times
- Can be enabled/disabled
- Track last run and next run times

### When to Use Scheduled Tasks

Use Scheduled Tasks when you need to:
- Run maintenance at specific times
- Perform regular synchronization
- Execute cleanup on a schedule
- Generate reports periodically

### Examples

- Nightly full synchronization
- Hourly incremental sync
- Weekly cleanup of old data
- Daily backup operations

### Key Features

- Cron expression support
- Enable/disable without deletion
- Grace time for missed executions
- Integration with Job system

## Daemons

### What are Daemons?

Daemons are continuous processes that:
- Run indefinitely until stopped
- Monitor and react to system events
- Can launch and manage other jobs
- Provide real-time logging
- Maintain persistent state

### When to Use Daemons

Use Daemons when you need to:
- Monitor system state continuously
- React to events in real-time
- Orchestrate jobs based on conditions
- Maintain long-running connections
- Provide always-on services

### Examples

- Metadata generate watcher (monitors and manages generation jobs)
- File system watcher (detects new files)
- Queue processor (handles incoming requests)
- Health monitor (tracks system status)

### Key Features

- Start/stop/restart controls
- Auto-start on system startup
- Real-time log streaming
- Heartbeat monitoring
- Configuration management
- Job orchestration capabilities

## Comparison Table

| Feature | Jobs | Workflow Jobs | Scheduled Tasks | Daemons |
|---------|------|---------------|-----------------|---------|
| **Lifetime** | Finite | Finite | Finite (recurring) | Continuous |
| **Execution** | On-demand | On-demand | Scheduled | Always running |
| **Progress** | 0-100% | Steps + % | 0-100% | N/A (status) |
| **Cancellation** | ✓ | ✓ | ✓ (individual runs) | Stop daemon |
| **State** | In database | In database | In database | In memory + database |
| **Use Case** | Single tasks | Multi-step tasks | Periodic tasks | Monitoring/reacting |
| **Complexity** | Low | Medium | Low | High |
| **Resource Usage** | During execution | During execution | During execution | Continuous (low idle) |

## Decision Flow

```
Need to execute a task?
│
├─ Is it continuous/monitoring?
│  └─ Yes → Use a Daemon
│
├─ Does it run on a schedule?
│  └─ Yes → Use a Scheduled Task
│
├─ Does it have multiple steps?
│  └─ Yes → Use a Workflow Job
│
└─ Single operation → Use a Job
```

## Best Practices

### For Jobs
- Keep jobs focused on a single responsibility
- Implement proper progress reporting
- Handle cancellation gracefully
- Store results in metadata

### For Workflow Jobs
- Break down complex operations into clear steps
- Use subjobs for parallelizable work
- Implement rollback for failed steps
- Track step completion in metadata

### For Scheduled Tasks
- Use appropriate cron expressions
- Consider time zones
- Implement grace periods for missed runs
- Monitor execution history

### For Daemons
- Implement heartbeat monitoring
- Use configuration for flexibility
- Log at appropriate levels
- Handle shutdown gracefully
- Avoid blocking operations
- Use async/await patterns

## Resource Considerations

### Jobs and Workflow Jobs
- Use worker pool (default: 5 concurrent)
- Memory freed after completion
- Database records persist

### Scheduled Tasks
- Minimal overhead when not running
- Same resource usage as Jobs when active

### Daemons
- Continuous memory footprint (typically small)
- CPU usage varies by activity
- No worker pool limitations
- Run as asyncio tasks

## Error Handling

### Jobs
- Status changes to FAILED
- Error stored in result
- Can be retried manually

### Scheduled Tasks
- Individual run fails
- Next scheduled run proceeds
- Failed runs logged

### Daemons
- Errors logged but daemon continues
- Implement retry logic internally
- Status changes to ERROR for fatal issues
- Auto-restart capability

## Monitoring

### Jobs
- View in Jobs page
- Real-time status via WebSocket
- Historical data available

### Scheduled Tasks
- View in Schedules page
- See last/next run times
- Execution history

### Daemons
- Dedicated Daemons page
- Real-time log viewer
- Heartbeat monitoring
- Job launch history