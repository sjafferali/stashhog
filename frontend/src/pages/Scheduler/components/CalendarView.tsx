import React, { MouseEvent } from 'react';
import { Calendar, Badge, Typography, Space, Tooltip } from 'antd';
import { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { Schedule, ScheduleRun } from '../types';
import {} from '@ant-design/icons';

const { Text } = Typography;

interface CalendarViewProps {
  schedules: Schedule[];
  runs: ScheduleRun[];
  onScheduleClick?: (schedule: Schedule) => void;
}

interface CalendarEvent {
  type: 'scheduled' | 'completed' | 'failed' | 'running';
  schedule: Schedule;
  run?: ScheduleRun;
  time: string;
}

const CalendarView: React.FC<CalendarViewProps> = ({
  schedules,
  runs,
  onScheduleClick,
}) => {
  const getEventsForDate = (date: Dayjs): CalendarEvent[] => {
    const events: CalendarEvent[] = [];
    const dateStr = date.format('YYYY-MM-DD');

    // Add completed/failed runs
    runs.forEach((run) => {
      const runDate = dayjs(run.started_at);
      if (runDate.format('YYYY-MM-DD') === dateStr) {
        const schedule = schedules.find((s) => s.id === run.schedule_id);
        if (schedule) {
          events.push({
            type:
              run.status === 'running'
                ? 'running'
                : run.status === 'success'
                  ? 'completed'
                  : 'failed',
            schedule,
            run,
            time: runDate.format('HH:mm'),
          });
        }
      }
    });

    // Add scheduled runs (based on cron expressions)
    schedules.forEach((schedule) => {
      if (!schedule.enabled) return;

      // This is a simplified check - in production, you'd parse the cron expression
      // and determine if it runs on this date
      const isToday = date.isSame(dayjs(), 'day');
      const isFuture = date.isAfter(dayjs(), 'day');

      if ((isToday || isFuture) && schedule.next_run) {
        const nextRun = dayjs(schedule.next_run);
        if (nextRun.format('YYYY-MM-DD') === dateStr) {
          events.push({
            type: 'scheduled',
            schedule,
            time: nextRun.format('HH:mm'),
          });
        }
      }
    });

    return events.sort((a, b) => a.time.localeCompare(b.time));
  };

  const getStatusBadge = (
    type: CalendarEvent['type']
  ): 'success' | 'error' | 'warning' | 'processing' => {
    switch (type) {
      case 'scheduled':
        return 'processing';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'warning';
    }
  };

  const dateCellRender = (date: Dayjs) => {
    const events = getEventsForDate(date);

    if (events.length === 0) return null;

    return (
      <Space direction="vertical" size={2} style={{ width: '100%' }}>
        {events.slice(0, 3).map((event, index) => (
          <Tooltip
            key={index}
            title={
              <Space direction="vertical" size={0}>
                <Text style={{ color: 'white' }}>{event.schedule.name}</Text>
                <Text
                  style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: 12 }}
                >
                  {event.time} - {event.type}
                </Text>
                {event.run && event.run.duration && (
                  <Text
                    style={{ color: 'rgba(255, 255, 255, 0.8)', fontSize: 12 }}
                  >
                    Duration: {Math.round(event.run.duration / 60)}m
                  </Text>
                )}
              </Space>
            }
          >
            <div
              style={{
                cursor: 'pointer',
                padding: '2px 4px',
                borderRadius: 4,
                background: 'rgba(0, 0, 0, 0.02)',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
              onClick={(e: MouseEvent<HTMLDivElement>) => {
                e.stopPropagation();
                onScheduleClick?.(event.schedule);
              }}
            >
              <Badge status={getStatusBadge(event.type)} />
              <Text
                ellipsis
                style={{
                  fontSize: 11,
                  flex: 1,
                  color: event.type === 'failed' ? '#ff4d4f' : undefined,
                }}
              >
                {event.time} {event.schedule.name}
              </Text>
            </div>
          </Tooltip>
        ))}
        {events.length > 3 && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            +{events.length - 3} more
          </Text>
        )}
      </Space>
    );
  };

  const monthCellRender = (date: Dayjs) => {
    const monthStart = date.startOf('month');
    const monthEnd = date.endOf('month');

    let totalRuns = 0;
    let successfulRuns = 0;
    let failedRuns = 0;

    runs.forEach((run) => {
      const runDate = dayjs(run.started_at);
      if (runDate.isAfter(monthStart) && runDate.isBefore(monthEnd)) {
        totalRuns++;
        if (run.status === 'success') successfulRuns++;
        if (run.status === 'failed') failedRuns++;
      }
    });

    if (totalRuns === 0) return null;

    return (
      <Space size={4}>
        <Badge count={successfulRuns} style={{ backgroundColor: '#52c41a' }} />
        {failedRuns > 0 && (
          <Badge count={failedRuns} style={{ backgroundColor: '#ff4d4f' }} />
        )}
      </Space>
    );
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Text type="secondary">Click on events to view details</Text>
        <Space size={16}>
          <Space size={4}>
            <Badge status="processing" />
            <Text type="secondary">Scheduled</Text>
          </Space>
          <Space size={4}>
            <Badge status="success" />
            <Text type="secondary">Completed</Text>
          </Space>
          <Space size={4}>
            <Badge status="error" />
            <Text type="secondary">Failed</Text>
          </Space>
          <Space size={4}>
            <Badge status="warning" />
            <Text type="secondary">Running</Text>
          </Space>
        </Space>
      </Space>

      <Calendar
        dateCellRender={dateCellRender}
        monthCellRender={monthCellRender}
      />
    </div>
  );
};

export default CalendarView;
