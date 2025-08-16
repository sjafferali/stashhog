import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Table,
  Card,
  Badge,
  Space,
  Button,
  Tooltip,
  Tag,
  Typography,
  message,
  Progress,
} from 'antd';
import {
  PlayCircleOutlined,
  SyncOutlined,
  UpOutlined,
  DownOutlined,
  ClockCircleOutlined,
  StopOutlined,
  InfoCircleOutlined,
  CloseCircleOutlined,
  RedoOutlined,
  FileTextOutlined,
  VideoCameraOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import { useWebSocket } from '@/hooks/useWebSocket';
import { getJobTypeLabel, getJobTypeColor } from '@/utils/jobUtils';

import { Job } from '@/types/models';

const { Text } = Typography;

interface ActiveJobsSectionProps {
  onCancel: (jobId: string) => Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
  onRefresh: () => void;
  className?: string;
}

const ActiveJobsSection: React.FC<ActiveJobsSectionProps> = ({
  onCancel,
  onRetry,
  onRefresh,
  className,
}) => {
  // FULL ORIGINAL FUNCTIONALITY RESTORED - Test 7
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  // TEMPORARILY DISABLED - removing this state that was causing issues
  // const [previousActiveJobIds, setPreviousActiveJobIds] = useState<Set<string>>(
  //   new Set()
  // );
  const isMountedRef = useRef(true);
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const onRefreshRef = useRef(onRefresh);
  const previousActiveJobIdsRef = useRef<Set<string>>(new Set());
  const { lastMessage } = useWebSocket('/api/jobs/ws');

  // Keep onRefresh ref current
  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  const fetchActiveJobs = useCallback(async () => {
    if (!isMountedRef.current) return;

    // RESTORED: Real API call now that the issue is fixed
    try {
      setLoading(true);
      const jobs = await apiClient.getActiveJobs();
      if (isMountedRef.current) {
        setActiveJobs(jobs);
      }
    } catch (error) {
      console.error('Failed to fetch active jobs:', error);
      if (isMountedRef.current) {
        void message.error('Failed to fetch active jobs');
        setActiveJobs([]);
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  // Initial fetch and cleanup
  useEffect(() => {
    isMountedRef.current = true;
    void fetchActiveJobs();

    return () => {
      isMountedRef.current = false;
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
        refreshTimeoutRef.current = null;
      }
    };
  }, [fetchActiveJobs]);

  // Handle WebSocket updates for real-time active job changes
  useEffect(() => {
    if (!isMountedRef.current) return;

    if (lastMessage && typeof lastMessage === 'object') {
      const update = lastMessage as { type: string; job: Job };

      if (update.type === 'job_update' && update.job) {
        const job = update.job;

        // Handle active job statuses (pending, running, cancelling)
        const isActiveJob = ['pending', 'running', 'cancelling'].includes(
          job.status
        );

        if (isMountedRef.current) {
          setActiveJobs((prevJobs) => {
            const jobIndex = prevJobs.findIndex((j) => j.id === job.id);

            if (isActiveJob) {
              if (jobIndex >= 0) {
                // Update existing active job
                const newJobs = [...prevJobs];
                newJobs[jobIndex] = job;
                return newJobs;
              } else {
                // Add new active job
                return [...prevJobs, job];
              }
            } else {
              // Job completed/failed/cancelled - remove from active jobs
              if (jobIndex >= 0) {
                return prevJobs.filter((j) => j.id !== job.id);
              }
            }

            return prevJobs;
          });
        }
      }
    }
  }, [lastMessage]);

  // SAFE job completion tracking using refs instead of state
  useEffect(() => {
    if (!isMountedRef.current) return;

    const currentActiveJobIds = new Set(activeJobs.map((job) => job.id));
    const previousIds = previousActiveJobIdsRef.current;

    // Check if any jobs that were previously active are no longer active
    const completedJobs = Array.from(previousIds).filter(
      (id) => !currentActiveJobIds.has(id)
    );

    // If jobs completed, refresh the historical jobs list
    if (completedJobs.length > 0 && previousIds.size > 0) {
      // Clear any existing timeout
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }

      // Only set new timeout if component is still mounted
      if (isMountedRef.current) {
        refreshTimeoutRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            onRefreshRef.current();
          }
          refreshTimeoutRef.current = null;
        }, 100);
      }
    }

    // Update the previous job IDs in ref (not state!)
    previousActiveJobIdsRef.current = currentActiveJobIds;
  }, [activeJobs]); // Only depends on activeJobs, not the ref

  // PREVIOUSLY DISABLED - This entire useEffect was causing React Error #185
  // The previousActiveJobIds tracking logic is problematic
  // useEffect(() => {
  //   if (!isMountedRef.current) return;
  //   const currentActiveJobIds = new Set(activeJobs.map((job) => job.id));
  //   const completedJobs = Array.from(previousActiveJobIds).filter(
  //     (id) => !currentActiveJobIds.has(id)
  //   );
  //   if (completedJobs.length > 0 && previousActiveJobIds.size > 0) {
  //     if (refreshTimeoutRef.current) {
  //       clearTimeout(refreshTimeoutRef.current);
  //     }
  //     if (isMountedRef.current) {
  //       refreshTimeoutRef.current = setTimeout(() => {
  //         if (isMountedRef.current) {
  //           onRefreshRef.current();
  //         }
  //         refreshTimeoutRef.current = null;
  //       }, 100);
  //     }
  //   }
  //   setPreviousActiveJobIds(currentActiveJobIds);
  //   return () => {
  //     if (refreshTimeoutRef.current) {
  //       clearTimeout(refreshTimeoutRef.current);
  //       refreshTimeoutRef.current = null;
  //     }
  //   };
  // }, [activeJobs, previousActiveJobIds]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'cancelling':
        return <StopOutlined style={{ color: '#ff7a45' }} />;
      default:
        return <InfoCircleOutlined />;
    }
  };

  const formatDuration = (start?: string) => {
    if (!start) return '-';
    const startTime = new Date(start).getTime();
    const endTime = Date.now();
    const duration = endTime - startTime;

    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  const getJobSceneIds = (job: Job): string[] | null => {
    if (job.metadata?.scene_ids && Array.isArray(job.metadata.scene_ids)) {
      return job.metadata.scene_ids as string[];
    }
    if (job.parameters?.scene_ids && Array.isArray(job.parameters.scene_ids)) {
      return job.parameters.scene_ids as string[];
    }
    return null;
  };

  const shouldShowViewScenesButton = (job: Job): boolean => {
    const qualifyingTypes = [
      'sync',
      'sync_scenes',
      'scene_sync',
      'analysis',
      'scene_analysis',
      'apply_plan',
    ];

    if (!qualifyingTypes.includes(job.type)) {
      return false;
    }

    const sceneIds = getJobSceneIds(job);
    return sceneIds !== null && sceneIds.length > 0;
  };

  const getActiveJobColumns = (): ColumnsType<Job> => [
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string, record: Job) => {
        const icon = getStatusIcon(status);
        const lastMessage = record.metadata?.last_message;

        return (
          <Space>
            {icon}
            <Tag
              color={
                status === 'running'
                  ? 'processing'
                  : status === 'pending'
                    ? 'orange'
                    : status === 'cancelling'
                      ? 'warning'
                      : 'default'
              }
            >
              {status.toUpperCase()}
            </Tag>
            {lastMessage && status === 'running' && (
              <Tooltip title={lastMessage}>
                <Badge status="processing" />
              </Tooltip>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Job Type',
      dataIndex: 'type',
      key: 'type',
      width: 150,
      render: (type: string) => {
        return <Tag color={getJobTypeColor(type)}>{getJobTypeLabel(type)}</Tag>;
      },
    },
    {
      title: 'Progress',
      key: 'progress',
      width: 200,
      render: (_: unknown, record: Job) => {
        const percent = Math.round(record.progress || 0);
        const hasMessage = record.metadata?.last_message;

        return (
          <div style={{ minWidth: 150 }}>
            <Progress
              percent={percent}
              status={
                record.status === 'running'
                  ? 'active'
                  : record.status === 'cancelling'
                    ? 'exception'
                    : 'normal'
              }
              size="small"
              format={(percent: number | undefined) => (
                <Space size={4}>
                  <span>{percent}%</span>
                  {hasMessage && record.status === 'running' && (
                    <Tooltip
                      title={record.metadata?.last_message}
                      placement="top"
                    >
                      <FileTextOutlined style={{ fontSize: 12 }} />
                    </Tooltip>
                  )}
                </Space>
              )}
            />
            {record.processed_items !== undefined &&
              record.total !== undefined &&
              record.total !== null && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {record.processed_items} / {record.total} items
                </Text>
              )}
          </div>
        );
      },
    },
    {
      title: 'Duration',
      key: 'duration',
      width: 120,
      render: (_: unknown, record: Job) => (
        <Text type="secondary">{formatDuration(record.started_at)}</Text>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: Job) => (
        <Space size="small">
          <Tooltip title="View Details">
            <Button type="text" icon={<InfoCircleOutlined />} size="small" />
          </Tooltip>

          {shouldShowViewScenesButton(record) && (
            <Tooltip title="View Scenes">
              <Link to={`/scenes?job_ids=${record.id}`}>
                <Button
                  type="text"
                  icon={<VideoCameraOutlined />}
                  size="small"
                />
              </Link>
            </Tooltip>
          )}

          {['running', 'pending'].includes(record.status) && (
            <Tooltip title="Cancel Job">
              <Button
                type="text"
                danger
                icon={<CloseCircleOutlined />}
                size="small"
                onClick={() => void onCancel(record.id)}
              />
            </Tooltip>
          )}

          {record.status === 'failed' && (
            <Tooltip title="Retry Job">
              <Button
                type="text"
                icon={<RedoOutlined />}
                size="small"
                onClick={() => void onRetry(record.id)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  if (activeJobs.length === 0) {
    return null; // Don't show section if no active jobs
  }

  const runningCount = activeJobs.filter(
    (job) => job.status === 'running'
  ).length;
  const pendingCount = activeJobs.filter(
    (job) => job.status === 'pending'
  ).length;
  const cancellingCount = activeJobs.filter(
    (job) => job.status === 'cancelling'
  ).length;

  return (
    <Card
      className={className}
      title={
        <Space>
          <PlayCircleOutlined />
          <span>Active Jobs</span>
          <Badge count={runningCount} showZero={false} color="blue" />
          <Badge count={pendingCount} showZero={false} color="orange" />
          <Badge count={cancellingCount} showZero={false} color="red" />
        </Space>
      }
      extra={
        <Space>
          <Button
            type="text"
            size="small"
            icon={collapsed ? <DownOutlined /> : <UpOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? 'Show' : 'Hide'}
          </Button>
          <Tooltip title="Refresh Active Jobs">
            <Button
              type="text"
              size="small"
              icon={<SyncOutlined />}
              onClick={() => void fetchActiveJobs()}
              loading={loading}
            />
          </Tooltip>
          <Tooltip title="Refresh Historical Jobs">
            <Button
              type="text"
              size="small"
              icon={<LoadingOutlined />}
              onClick={() => onRefreshRef.current()}
            />
          </Tooltip>
        </Space>
      }
      size="small"
      style={{ marginBottom: 16 }}
    >
      {!collapsed && (
        <Table
          columns={getActiveJobColumns()}
          dataSource={activeJobs.map((job) => ({ ...job, key: job.id }))}
          pagination={false}
          size="small"
          scroll={{ x: 800 }}
        />
      )}
    </Card>
  );
};

export default ActiveJobsSection;
