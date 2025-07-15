import React from 'react';
import {
  Table,
  Tag,
  Space,
  Typography,
  Select,
  Button,
  Tooltip,
  Progress,
  Card,
  Row,
  Col,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { ScheduleRun, Schedule } from '../types';
import { useScheduleHistory } from '../hooks/useSchedules';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import duration from 'dayjs/plugin/duration';

dayjs.extend(relativeTime);
dayjs.extend(duration);

const { Text, Title } = Typography;

interface RunHistoryProps {
  scheduleId?: number;
  onScheduleSelect?: (schedule: Schedule | null) => void;
  schedules: Schedule[];
}

const RunHistory: React.FC<RunHistoryProps> = ({
  scheduleId,
  onScheduleSelect,
  schedules,
}) => {
  const { runs, loading, stats, refetch } = useScheduleHistory(scheduleId);

  const filteredRuns = runs;

  const getStatusTag = (status: ScheduleRun['status']) => {
    switch (status) {
      case 'success':
        return (
          <Tag color="success">
            <CheckCircleOutlined /> Success
          </Tag>
        );
      case 'failed':
        return (
          <Tag color="error">
            <CloseCircleOutlined /> Failed
          </Tag>
        );
      case 'running':
        return (
          <Tag color="processing">
            <SyncOutlined spin /> Running
          </Tag>
        );
      case 'cancelled':
        return (
          <Tag color="default">
            <CloseCircleOutlined /> Cancelled
          </Tag>
        );
      default:
        return <Tag>{status}</Tag>;
    }
  };

  const formatDuration = (seconds: number | undefined) => {
    if (!seconds) return '-';

    const duration = dayjs.duration(seconds, 'seconds');
    if (seconds < 60) {
      return `${seconds}s`;
    } else if (seconds < 3600) {
      return `${Math.floor(duration.asMinutes())}m ${duration.seconds()}s`;
    } else {
      return `${Math.floor(duration.asHours())}h ${duration.minutes()}m`;
    }
  };

  const columns = [
    {
      title: 'Schedule',
      dataIndex: 'schedule_id',
      key: 'schedule',
      render: (schedule_id: number) => {
        const schedule = schedules.find((s) => s.id === schedule_id);
        return schedule ? (
          <Space direction="vertical" size={0}>
            <Text strong>{schedule.name}</Text>
            <Tag
              color={
                schedule.task_type === 'sync'
                  ? 'blue'
                  : schedule.task_type === 'analysis'
                    ? 'green'
                    : 'orange'
              }
            >
              {schedule.task_type.toUpperCase()}
            </Tag>
          </Space>
        ) : (
          '-'
        );
      },
      hidden: !!scheduleId,
    },
    {
      title: 'Started',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date: string) => (
        <Space direction="vertical" size={0}>
          <Text>{dayjs(date).format('YYYY-MM-DD HH:mm:ss')}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {dayjs(date).fromNow()}
          </Text>
        </Space>
      ),
      sorter: (a: ScheduleRun, b: ScheduleRun) =>
        dayjs(a.started_at).unix() - dayjs(b.started_at).unix(),
      defaultSortOrder: 'descend' as const,
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration: number | undefined, record: ScheduleRun) => {
        if (record.status === 'running') {
          const elapsed = dayjs().diff(dayjs(record.started_at), 'second');
          return (
            <Space>
              <Progress
                type="circle"
                percent={0}
                width={20}
                status="active"
                strokeWidth={10}
              />
              <Text>{formatDuration(elapsed)}</Text>
            </Space>
          );
        }
        return formatDuration(duration);
      },
      sorter: (a: ScheduleRun, b: ScheduleRun) =>
        (a.duration || 0) - (b.duration || 0),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: ScheduleRun['status']) => getStatusTag(status),
      filters: [
        { text: 'Success', value: 'success' },
        { text: 'Failed', value: 'failed' },
        { text: 'Running', value: 'running' },
        { text: 'Cancelled', value: 'cancelled' },
      ],
      onFilter: (value: React.Key | boolean, record: ScheduleRun) =>
        record.status === value,
    },
    {
      title: 'Job ID',
      dataIndex: 'job_id',
      key: 'job_id',
      render: (job_id?: string) =>
        job_id ? (
          <Tooltip title="View job details">
            <Button type="link" size="small">
              {job_id.substring(0, 8)}...
            </Button>
          </Tooltip>
        ) : (
          '-'
        ),
    },
    {
      title: 'Error',
      dataIndex: 'error',
      key: 'error',
      render: (error?: string) =>
        error ? (
          <Tooltip title={error}>
            <Text type="danger" ellipsis style={{ maxWidth: 200 }}>
              {error}
            </Text>
          </Tooltip>
        ) : (
          '-'
        ),
    },
  ];

  const displayColumns = columns.filter((col) => !col.hidden);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Row justify="space-between" align="middle">
        <Col>
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              {scheduleId ? 'Schedule Run History' : 'All Run History'}
            </Title>
            {scheduleId && (
              <Button type="link" onClick={() => onScheduleSelect?.(null)}>
                View all schedules
              </Button>
            )}
          </Space>
        </Col>
        <Col>
          <Space>
            <Select
              style={{ width: 180 }}
              placeholder="Filter by schedule"
              value={scheduleId || 'all'}
              onChange={(value) => {
                if (value === 'all') {
                  onScheduleSelect?.(null);
                } else {
                  const schedule = schedules.find((s) => s.id === value);
                  if (schedule) onScheduleSelect?.(schedule);
                }
              }}
              options={[
                { value: 'all', label: 'All Schedules' },
                ...schedules.map((schedule) => ({
                  value: schedule.id,
                  label: schedule.name,
                })),
              ]}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void refetch()}
              loading={loading}
            >
              Refresh
            </Button>
          </Space>
        </Col>
      </Row>

      {stats && (
        <Row gutter={16}>
          <Col xs={24} sm={8}>
            <Card size="small">
              <Space direction="vertical" size={0} style={{ width: '100%' }}>
                <Text type="secondary">Total Runs</Text>
                <Text style={{ fontSize: 24 }}>{stats.total_runs}</Text>
              </Space>
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card size="small">
              <Space direction="vertical" size={0} style={{ width: '100%' }}>
                <Text type="secondary">Success Rate</Text>
                <Text style={{ fontSize: 24, color: '#52c41a' }}>
                  {stats.total_runs > 0
                    ? Math.round(
                        (stats.successful_runs / stats.total_runs) * 100
                      )
                    : 0}
                  %
                </Text>
              </Space>
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card size="small">
              <Space direction="vertical" size={0} style={{ width: '100%' }}>
                <Text type="secondary">Avg Duration</Text>
                <Text style={{ fontSize: 24 }}>
                  {formatDuration(stats.average_duration)}
                </Text>
              </Space>
            </Card>
          </Col>
        </Row>
      )}

      <Table
        columns={displayColumns}
        dataSource={filteredRuns}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} runs`,
        }}
      />
    </Space>
  );
};

export default RunHistory;
