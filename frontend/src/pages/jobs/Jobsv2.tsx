import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Table,
  Tag,
  Progress,
  Button,
  Space,
  Tooltip,
  Typography,
  Badge,
  message,
  Empty,
  Segmented,
} from 'antd';
import { Link } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import {
  SyncOutlined,
  CloseCircleOutlined,
  RedoOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  TableOutlined,
  AppstoreOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { apiClient } from '@/services/apiClient';
import { Job } from '@/types/models';
import { useWebSocket } from '@/hooks/useWebSocket';
import { getJobTypeLabel, formatJobProgress } from '@/utils/jobUtils';
import styles from './Jobsv2.module.scss';

const { Text, Title } = Typography;

interface JobWithRelationship extends Job {
  key: string;
  isSubJob?: boolean;
  parentJobId?: string;
  parentJobName?: string;
  subJobs?: JobWithRelationship[];
  children?: JobWithRelationship[]; // For table tree structure
}

const Jobsv2: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card');
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);
  const { lastMessage } = useWebSocket('/api/jobs/ws');

  const fetchJobs = async () => {
    try {
      const response = await apiClient.getJobs({ limit: 100 });
      const jobsArray = Array.isArray(response) ? response : [];
      setJobs(jobsArray);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      void message.error('Failed to fetch jobs');
      setJobs([]);
    }
  };

  useEffect(() => {
    setLoading(true);
    void fetchJobs().finally(() => setLoading(false));

    const interval = setInterval(() => {
      void fetchJobs();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Handle WebSocket updates
  useEffect(() => {
    if (lastMessage && typeof lastMessage === 'object') {
      const update = lastMessage as { type: string; job: Job };

      if (update.type === 'job_update' && update.job) {
        setJobs((prevJobs) => {
          const jobIndex = prevJobs.findIndex((j) => j.id === update.job.id);

          if (jobIndex >= 0) {
            const newJobs = [...prevJobs];
            newJobs[jobIndex] = update.job;
            return newJobs;
          } else {
            return [update.job, ...prevJobs];
          }
        });
      }
    }
  }, [lastMessage]);

  // Process jobs to establish relationships
  const processedJobs = useMemo(() => {
    const jobsWithRelationships: JobWithRelationship[] = jobs.map((job) => ({
      ...job,
      key: job.id,
      isSubJob: !!job.metadata?.parent_job_id,
      parentJobId: job.metadata?.parent_job_id as string | undefined,
    }));

    // Create a map for quick lookup
    const jobMap = new Map<string, JobWithRelationship>();
    jobsWithRelationships.forEach((job) => {
      jobMap.set(job.id, job);
    });

    // Establish parent-child relationships
    const rootJobs: JobWithRelationship[] = [];
    jobsWithRelationships.forEach((job) => {
      if (job.parentJobId) {
        const parentJob = jobMap.get(job.parentJobId);
        if (parentJob) {
          if (!parentJob.subJobs) {
            parentJob.subJobs = [];
          }
          if (!parentJob.children) {
            parentJob.children = [];
          }
          job.parentJobName = parentJob.name || getJobTypeLabel(parentJob.type);
          parentJob.subJobs.push(job);
          parentJob.children.push(job);
        } else {
          // Parent job not found, treat as root job
          rootJobs.push(job);
        }
      } else {
        rootJobs.push(job);
      }
    });

    // Sort root jobs by created_at desc
    rootJobs.sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    return rootJobs;
  }, [jobs]);

  const handleCancel = async (jobId: string) => {
    try {
      await apiClient.cancelJob(jobId);
      void message.success('Job cancelled successfully');
      await fetchJobs();
    } catch (error) {
      console.error('Failed to cancel job:', error);
      void message.error('Failed to cancel job');
    }
  };

  const handleRetry = async (jobId: string) => {
    try {
      await apiClient.retryJob(jobId);
      void message.success('Job retry initiated');
      await fetchJobs();
    } catch (error) {
      console.error('Failed to retry job:', error);
      void message.error('Failed to retry job');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'cancelled':
        return <CloseCircleOutlined style={{ color: '#ff7a45' }} />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'orange';
      case 'running':
        return 'processing';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'warning';
      default:
        return 'default';
    }
  };

  const formatDuration = (start?: string, end?: string) => {
    if (!start) return '-';
    const startTime = new Date(start).getTime();
    const endTime = end ? new Date(end).getTime() : Date.now();
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

  const getJobTypeIndicator = (job: JobWithRelationship) => {
    if (job.type === 'process_new_scenes') {
      return <Tag color="purple">WORKFLOW</Tag>;
    } else if (job.isSubJob) {
      return <Tag color="cyan">SUB-JOB</Tag>;
    } else {
      return <Tag color="green">STANDALONE</Tag>;
    }
  };

  const renderJobCard = (job: JobWithRelationship, isSubJob = false) => {
    const isWorkflow = job.type === 'process_new_scenes';

    return (
      <div key={job.id} className={styles.jobCardWrapper}>
        {isSubJob && (
          <div className={styles.subjobConnector}>
            <div className={styles.connectorLine} />
          </div>
        )}
        <Card
          className={`${styles.jobCard} ${isWorkflow ? styles.workflowJob : ''} ${
            isSubJob ? styles.subjob : ''
          }`}
          title={
            <div className={styles.cardHeader}>
              <Space>
                {getStatusIcon(job.status)}
                <Text strong>{job.name || getJobTypeLabel(job.type)}</Text>
                {getJobTypeIndicator(job)}
              </Space>
              <Tag color={getStatusColor(job.status)}>
                {job.status.toUpperCase()}
              </Tag>
            </div>
          }
          extra={
            <Space>
              {job.status === 'running' && (
                <Button
                  type="text"
                  danger
                  icon={<CloseCircleOutlined />}
                  size="small"
                  onClick={() => void handleCancel(job.id)}
                />
              )}
              {job.status === 'failed' && (
                <Button
                  type="text"
                  icon={<RedoOutlined />}
                  size="small"
                  onClick={() => void handleRetry(job.id)}
                />
              )}
            </Space>
          }
        >
          {isSubJob && job.parentJobName && (
            <div className={styles.subjobIndicator}>
              <Text type="secondary">SUB-JOB OF: {job.parentJobName}</Text>
            </div>
          )}

          {isWorkflow &&
            job.metadata?.current_step &&
            job.metadata?.total_steps && (
              <div className={styles.workflowStep}>
                <Text>
                  Current Step: {job.metadata.current_step as number}/
                  {job.metadata.total_steps as number} -{' '}
                  {job.metadata.step_name as string}
                </Text>
              </div>
            )}

          <div className={styles.progressSection}>
            <Progress
              percent={job.progress}
              status={
                job.status === 'failed'
                  ? 'exception'
                  : job.status === 'completed'
                    ? 'success'
                    : 'active'
              }
            />
            <Text type="secondary">
              {formatJobProgress(
                job.type,
                job.processed_items,
                job.total,
                job.progress
              )}
            </Text>
          </div>

          <div className={styles.jobMeta}>
            <Space size="middle">
              <Text type="secondary">
                <ClockCircleOutlined />{' '}
                {formatDuration(job.started_at, job.completed_at)}
              </Text>
              <Text type="secondary">
                Created: {new Date(job.created_at).toLocaleTimeString()}
              </Text>
            </Space>
          </div>

          <div className={styles.jobId}>
            <Text copyable type="secondary" style={{ fontSize: '11px' }}>
              Job ID: {job.id}
            </Text>
          </div>

          {job.error && (
            <div className={styles.error}>
              <Text type="danger">{job.error}</Text>
            </div>
          )}

          {/* Action buttons */}
          <Space className={styles.actionButtons} wrap>
            {job.type === 'scene_analysis' && job.result?.plan_id ? (
              <Link to={`/analysis/plans/${job.result.plan_id as string}`}>
                <Button icon={<FileTextOutlined />} size="small">
                  View Analysis Plan
                </Button>
              </Link>
            ) : null}
            {job.metadata?.scene_ids &&
            Array.isArray(job.metadata.scene_ids) ? (
              <Link
                to={`/scenes?scene_ids=${(job.metadata.scene_ids as string[]).join(',')}`}
              >
                <Button icon={<VideoCameraOutlined />} size="small">
                  View {(job.metadata.scene_ids as string[]).length} Scenes
                </Button>
              </Link>
            ) : null}
          </Space>
        </Card>

        {/* Render sub-jobs */}
        {job.subJobs && job.subJobs.length > 0 && (
          <div className={styles.subjobsContainer}>
            {job.subJobs.map((subJob) => renderJobCard(subJob, true))}
          </div>
        )}
      </div>
    );
  };

  // Table columns
  const columns: ColumnsType<JobWithRelationship> = [
    {
      title: 'Job Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: JobWithRelationship) => (
        <Space>
          <Text strong>{name || getJobTypeLabel(record.type)}</Text>
        </Space>
      ),
    },
    {
      title: 'Type',
      key: 'type',
      width: 140,
      render: (_: unknown, record: JobWithRelationship) =>
        getJobTypeIndicator(record),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Space>
          {getStatusIcon(status)}
          <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
        </Space>
      ),
    },
    {
      title: 'Progress',
      key: 'progress',
      width: 200,
      render: (_: unknown, record: Job) => (
        <div>
          <Progress
            percent={record.progress}
            size="small"
            status={
              record.status === 'failed'
                ? 'exception'
                : record.status === 'completed'
                  ? 'success'
                  : 'active'
            }
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {formatJobProgress(
              record.type,
              record.processed_items,
              record.total,
              record.progress
            )}
          </Text>
        </div>
      ),
    },
    {
      title: 'Duration',
      key: 'duration',
      width: 100,
      render: (_: unknown, record: Job) => (
        <Text type="secondary">
          {formatDuration(record.started_at, record.completed_at)}
        </Text>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => (
        <Tooltip title={new Date(date).toLocaleString()}>
          <Text>{new Date(date).toLocaleTimeString()}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: Job) => (
        <Space>
          {record.status === 'running' && (
            <Button
              type="text"
              danger
              icon={<CloseCircleOutlined />}
              size="small"
              onClick={() => void handleCancel(record.id)}
            />
          )}
          {record.status === 'failed' && (
            <Button
              type="text"
              icon={<RedoOutlined />}
              size="small"
              onClick={() => void handleRetry(record.id)}
            />
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className={styles.jobsv2}>
      <div className={styles.header}>
        <Title level={2}>Jobs v2</Title>
        <Space>
          <Badge
            count={jobs.filter((j) => j.status === 'running').length}
            showZero
            color="blue"
          >
            <Tag color="blue">Running</Tag>
          </Badge>
          <Badge
            count={jobs.filter((j) => j.status === 'pending').length}
            showZero
            color="orange"
          >
            <Tag color="orange">Pending</Tag>
          </Badge>
          <Badge
            count={jobs.filter((j) => j.status === 'failed').length}
            showZero
            color="red"
          >
            <Tag color="red">Failed</Tag>
          </Badge>
        </Space>
      </div>

      <Card
        extra={
          <Space>
            <Segmented
              value={viewMode}
              options={[
                {
                  label: 'Hierarchical Cards',
                  value: 'card',
                  icon: <AppstoreOutlined />,
                },
                {
                  label: 'Hierarchical Table',
                  value: 'table',
                  icon: <TableOutlined />,
                },
              ]}
              onChange={(value: string) =>
                setViewMode(value as 'card' | 'table')
              }
            />
            <Button
              icon={<SyncOutlined />}
              onClick={() => void fetchJobs()}
              loading={loading}
            >
              Refresh
            </Button>
          </Space>
        }
      >
        {viewMode === 'card' ? (
          <div className={styles.cardView}>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <LoadingOutlined style={{ fontSize: 24 }} />
              </div>
            ) : processedJobs.length === 0 ? (
              <Empty description="No jobs found" />
            ) : (
              processedJobs.map((job) => renderJobCard(job))
            )}
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={processedJobs}
            loading={loading}
            rowKey="key"
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `Total ${total} jobs`,
            }}
            expandable={{
              expandedRowKeys,
              onExpandedRowsChange: setExpandedRowKeys,
              rowExpandable: (record) =>
                !!(record.children && record.children.length > 0),
            }}
            rowClassName={(record) => {
              if (record.type === 'process_new_scenes')
                return styles.tableWorkflowRow;
              if (record.isSubJob) return styles.tableSubjobRow;
              return '';
            }}
          />
        )}
      </Card>
    </div>
  );
};

export default Jobsv2;
