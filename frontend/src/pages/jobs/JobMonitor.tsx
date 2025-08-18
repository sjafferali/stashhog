import React, {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
} from 'react';
import {
  Card,
  Table,
  Tag,
  Progress,
  Button,
  Space,
  Tooltip,
  Modal,
  Descriptions,
  Typography,
  Row,
  Col,
  Alert,
  Badge,
  message,
  Empty,
  Select,
  Collapse,
  Segmented,
  Input,
} from 'antd';
import { Link, useSearchParams, useLocation } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import {
  SyncOutlined,
  CloseCircleOutlined,
  RedoOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  ExpandOutlined,
  FileTextOutlined,
  BugOutlined,
  VideoCameraOutlined,
  TableOutlined,
  AppstoreOutlined,
  CodeOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { apiClient } from '@/services/apiClient';
import { Job } from '@/types/models';
import {
  AnalysisJobResult,
  AnalysisJobResultData,
} from '@/components/jobs/AnalysisJobResult';
import { JobCard } from '@/components/jobs/JobCard';
import { WorkflowJobModal } from '@/components/jobs/WorkflowJobModal';
import { HandledDownloadsModal } from '@/components/jobs/HandledDownloadsModal';
import ActiveJobsSection from './ActiveJobsSection';
import { useWebSocket } from '@/hooks/useWebSocket';
import {
  getJobTypeLabel,
  getJobTypeColor,
  JOB_TYPE_LABELS,
} from '@/utils/jobUtils';
import styles from './JobMonitor.module.scss';

const { Text, Title, Paragraph } = Typography;

interface JobWithExpanded extends Job {
  key: string;
}

const JobMonitor: React.FC = () => {
  const location = useLocation();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);
  const [totalJobs, setTotalJobs] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [workflowModalVisible, setWorkflowModalVisible] = useState(false);
  const [selectedWorkflowJob, setSelectedWorkflowJob] = useState<Job | null>(
    null
  );
  const [rawDataModalVisible, setRawDataModalVisible] = useState(false);
  const [selectedRawDataJob, setSelectedRawDataJob] = useState<Job | null>(
    null
  );
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [isPageVisible, setIsPageVisible] = useState(true);
  const [searchParams, setSearchParams] = useSearchParams();
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    searchParams.get('status') || undefined
  );
  const [typeFilter, setTypeFilter] = useState<string | undefined>(
    searchParams.get('type') || undefined
  );
  const [jobIdFilter, setJobIdFilter] = useState<string | undefined>(
    searchParams.get('job_id') || undefined
  );
  const [viewMode, setViewMode] = useState<'table' | 'card'>(
    (searchParams.get('view') as 'table' | 'card') || 'table'
  );
  const [handledDownloadsModalVisible, setHandledDownloadsModalVisible] =
    useState(false);
  const [selectedHandledDownloadsJobId, setSelectedHandledDownloadsJobId] =
    useState<string | null>(null);
  const { lastMessage } = useWebSocket('/api/jobs/ws');

  // Force unmount if not on jobs route
  useEffect(() => {
    if (!location.pathname.startsWith('/jobs')) {
      // Clear all intervals and state immediately
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
    }
  }, [location.pathname]);

  const fetchJobs = useCallback(async () => {
    try {
      // If job ID filter is set, fetch that specific job and its sub-jobs
      if (jobIdFilter) {
        try {
          const job = await apiClient.getJob(jobIdFilter);
          const jobsToShow = [job];

          // If it's a workflow job, also fetch its sub-jobs
          if (job.type === 'process_new_scenes' && job.metadata?.sub_job_ids) {
            const subJobIds = job.metadata.sub_job_ids;
            if (Array.isArray(subJobIds)) {
              const subJobPromises = subJobIds.map((id: string) =>
                apiClient.getJob(id).catch((err) => {
                  console.error(`Failed to fetch sub-job ${id}:`, err);
                  return null;
                })
              );
              const subJobs = await Promise.all(subJobPromises);
              jobsToShow.push(...(subJobs.filter((j) => j !== null) as Job[]));
            }
          }

          setJobs(jobsToShow);
          setTotalJobs(jobsToShow.length);
        } catch (error) {
          console.error('Failed to fetch job by ID:', error);
          void message.error('Failed to fetch job by ID');
          setJobs([]);
          setTotalJobs(0);
        }
      } else {
        // Normal job list fetch with pagination
        const offset = (currentPage - 1) * pageSize;
        const params: Record<
          string,
          string | number | boolean | string[] | undefined
        > = {
          limit: pageSize,
          offset: offset,
        };

        if (statusFilter) params.status = statusFilter;
        if (typeFilter) params.job_type = typeFilter;

        const response = await apiClient.getJobs(params);

        setJobs(response.jobs);
        setTotalJobs(response.total);
      }
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      void message.error('Failed to fetch jobs');
      setJobs([]); // Ensure state is always an array
      setTotalJobs(0);
    }
  }, [jobIdFilter, currentPage, pageSize, statusFilter, typeFilter]);

  // Initial fetch when dependencies change
  useEffect(() => {
    setLoading(true);
    void fetchJobs().finally(() => setLoading(false));
  }, [jobIdFilter, currentPage, pageSize, statusFilter, typeFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  // Page visibility detection
  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsPageVisible(!document.hidden);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () =>
      document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
    };
  }, []);

  // Store fetchJobs in a ref to avoid recreation issues
  const fetchJobsRef = useRef(fetchJobs);
  fetchJobsRef.current = fetchJobs;

  // Set up auto-refresh interval (only on mount/unmount, respects page visibility)
  useEffect(() => {
    // Don't set up interval if page is not visible
    if (!isPageVisible) return;

    const interval = setInterval(() => {
      // Double-check page is still visible before fetching
      if (document.hidden === false) {
        void fetchJobsRef.current();
      }
    }, 10000);
    refreshIntervalRef.current = interval;

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
    };
  }, [isPageVisible]); // Only depend on page visibility, not fetchJobs

  // Handle WebSocket updates for real-time job changes (historical jobs only)
  useEffect(() => {
    if (lastMessage && typeof lastMessage === 'object') {
      const update = lastMessage as { type: string; job: Job };

      if (update.type === 'job_update' && update.job) {
        const job = update.job;

        // Only handle historical job statuses (completed, failed, cancelled)
        const isHistoricalJob = ['completed', 'failed', 'cancelled'].includes(
          job.status
        );

        if (isHistoricalJob) {
          setJobs((prevJobs) => {
            const jobIndex = prevJobs.findIndex((j) => j.id === job.id);

            if (jobIndex >= 0) {
              // Update existing job
              const newJobs = [...prevJobs];
              newJobs[jobIndex] = job;
              return newJobs;
            } else {
              // Add newly completed job at the beginning
              return [job, ...prevJobs];
            }
          });
        }

        // Always update selected job if it's the same one (for modal details)
        if (selectedJob && selectedJob.id === job.id) {
          setSelectedJob(job);
        }
      }
    }
  }, [lastMessage, selectedJob]);

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

  const showJobDetails = (job: Job) => {
    if (job.type === 'process_new_scenes') {
      setSelectedWorkflowJob(job);
      setWorkflowModalVisible(true);
    } else {
      setSelectedJob(job);
      setDetailModalVisible(true);
    }
  };

  const showRawJobData = (job: Job) => {
    setSelectedRawDataJob(job);
    setRawDataModalVisible(true);
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
        return <InfoCircleOutlined />;
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
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  const getJobSceneIds = (job: Job): string[] | null => {
    // Check different places where scene IDs might be stored

    // 1. Check metadata.scene_ids (for sync jobs)
    if (job.metadata?.scene_ids && Array.isArray(job.metadata.scene_ids)) {
      return job.metadata.scene_ids as string[];
    }

    // 2. Check parameters.scene_ids (for some sync jobs)
    if (job.parameters?.scene_ids && Array.isArray(job.parameters.scene_ids)) {
      return job.parameters.scene_ids as string[];
    }

    // 3. For analysis jobs, check if we have analyzed_scene_ids in result
    if (
      job.result?.analyzed_scene_ids &&
      Array.isArray(job.result.analyzed_scene_ids)
    ) {
      return job.result.analyzed_scene_ids as string[];
    }

    // 4. For stash_generate jobs, check if we have scenes_updated in result
    if (
      job.result?.scenes_updated &&
      Array.isArray(job.result.scenes_updated)
    ) {
      return job.result.scenes_updated as string[];
    }

    // 5. For analysis jobs with scenes_analyzed count but no explicit IDs
    // We can't determine specific scene IDs in this case
    if (job.type === 'scene_analysis' || job.type === 'analysis') {
      // Check if there's a way to get scene IDs from the result
      if (job.result?.scene_ids && Array.isArray(job.result.scene_ids)) {
        return job.result.scene_ids as string[];
      }
    }

    return null;
  };

  const shouldShowViewScenesButton = (job: Job): boolean => {
    // Check if this is a qualifying job type
    const qualifyingTypes = [
      'sync',
      'sync_scenes',
      'scene_sync',
      'analysis',
      'scene_analysis',
      'apply_plan',
      'stash_generate', // Add stash_generate to the list
    ];

    if (!qualifyingTypes.includes(job.type)) {
      return false;
    }

    // Check if we can extract scene IDs
    const sceneIds = getJobSceneIds(job);
    return sceneIds !== null && sceneIds.length > 0;
  };

  const expandedRowRender = (record: Job) => {
    const hasLargeContent =
      record.result && JSON.stringify(record.result).length > 1000;

    return (
      <div className={styles.expandedContent}>
        {hasLargeContent && (
          <div
            style={{
              textAlign: 'right',
              marginBottom: 8,
              fontSize: 12,
              color: '#8c8c8c',
              fontStyle: 'italic',
            }}
          >
            Scroll to see more content ↓
          </div>
        )}
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Card size="small" title="Job Information">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Job ID">
                  <Space>
                    <Text>{record.id}</Text>
                    <Tooltip title="Copy Job ID">
                      <Button
                        type="link"
                        icon={<CopyOutlined />}
                        size="small"
                        onClick={() => {
                          void navigator.clipboard.writeText(record.id);
                          void message.success('Job ID copied to clipboard');
                        }}
                      />
                    </Tooltip>
                  </Space>
                </Descriptions.Item>
                {record.name && (
                  <Descriptions.Item label="Name">
                    {record.name}
                  </Descriptions.Item>
                )}
                <Descriptions.Item label="Duration">
                  {formatDuration(record.started_at, record.completed_at)}
                </Descriptions.Item>
                <Descriptions.Item label="Progress">
                  {record.processed_items !== undefined &&
                  record.total !== undefined &&
                  record.total !== null ? (
                    <Text>
                      {record.processed_items} / {record.total} items
                    </Text>
                  ) : (
                    <Text>{record.progress}%</Text>
                  )}
                </Descriptions.Item>
                {record.type === 'process_new_scenes' && record.metadata && (
                  <>
                    {record.metadata.current_step &&
                      record.metadata.total_steps && (
                        <Descriptions.Item label="Workflow Step">
                          <Text>
                            {record.metadata.current_step as number} /{' '}
                            {record.metadata.total_steps as number}
                          </Text>
                        </Descriptions.Item>
                      )}
                    {record.metadata.step_name && (
                      <Descriptions.Item label="Current Step">
                        <Text>{record.metadata.step_name as string}</Text>
                      </Descriptions.Item>
                    )}
                    {record.metadata.active_sub_job && (
                      <Descriptions.Item label="Active Sub-Job">
                        <Space direction="vertical" size="small">
                          <Tag
                            color={getJobTypeColor(
                              (
                                record.metadata.active_sub_job as {
                                  type: string;
                                  progress: number;
                                }
                              ).type
                            )}
                          >
                            {getJobTypeLabel(
                              (
                                record.metadata.active_sub_job as {
                                  type: string;
                                  progress: number;
                                }
                              ).type
                            )}
                          </Tag>
                          <Progress
                            percent={
                              (
                                record.metadata.active_sub_job as {
                                  type: string;
                                  progress: number;
                                }
                              ).progress
                            }
                            size="small"
                            status="active"
                          />
                        </Space>
                      </Descriptions.Item>
                    )}
                  </>
                )}
              </Descriptions>
            </Card>
          </Col>

          <Col span={12}>
            <Card size="small" title="Status & Messages">
              {record.metadata?.last_message && (
                <div style={{ marginBottom: 16 }}>
                  <Text strong>Last Message:</Text>
                  <Paragraph
                    style={{
                      marginTop: 8,
                      padding: 8,
                      background: '#f5f5f5',
                      borderRadius: 4,
                    }}
                  >
                    {record.metadata.last_message}
                  </Paragraph>
                </div>
              )}

              {record.error && (
                <Alert
                  message="Error Details"
                  description={record.error}
                  type="error"
                  showIcon
                  icon={<BugOutlined />}
                />
              )}
            </Card>
          </Col>
        </Row>

        {record.result && Object.keys(record.result).length > 0 && (
          <Card
            size="small"
            title="Result Details"
            style={{ marginTop: 16 }}
            extra={
              <Button
                type="link"
                size="small"
                icon={<ExpandOutlined />}
                onClick={() => showJobDetails(record)}
              >
                View Full Details
              </Button>
            }
          >
            {record.type === 'scene_analysis' ||
            record.type === 'analysis' ||
            record.type === 'non_ai_analysis' ? (
              <>
                <AnalysisJobResult
                  result={record.result as unknown as AnalysisJobResultData}
                />
                {((record.result &&
                  'plan_id' in record.result &&
                  record.result.plan_id) ||
                  (record.metadata &&
                    'plan_id' in record.metadata &&
                    record.metadata.plan_id)) && (
                  <div style={{ marginTop: 16 }}>
                    <Link
                      to={`/analysis/plans/${
                        (record.result && 'plan_id' in record.result
                          ? record.result.plan_id
                          : record.metadata?.plan_id) as string
                      }`}
                    >
                      <Button type="primary" icon={<FileTextOutlined />}>
                        View{' '}
                        {record.status === 'running' ? 'Current' : 'Created'}{' '}
                        Analysis Plan
                      </Button>
                    </Link>
                  </div>
                )}
              </>
            ) : (
              <pre className={styles.resultPreview}>
                {JSON.stringify(record.result, null, 2)}
              </pre>
            )}
          </Card>
        )}
      </div>
    );
  };

  const columns: ColumnsType<JobWithExpanded> = [
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string, record: JobWithExpanded) => {
        const icon = getStatusIcon(status);
        const lastMessage = record.metadata?.last_message;

        return (
          <Space>
            {icon}
            <Tag
              color={
                status === 'completed'
                  ? 'success'
                  : status === 'failed'
                    ? 'error'
                    : status === 'running'
                      ? 'processing'
                      : status === 'pending'
                        ? 'orange'
                        : status === 'cancelled'
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
        const hasMessage = !!record.metadata?.last_message;
        const isWorkflow = record.type === 'process_new_scenes';
        const currentStep = record.metadata?.current_step as number | undefined;
        const totalSteps = record.metadata?.total_steps as number | undefined;
        const stepName = record.metadata?.step_name as string | undefined;
        const activeSubJob = record.metadata?.active_sub_job as
          | {
              id: string;
              type: string;
              status: string;
              progress: number;
            }
          | undefined;

        return (
          <div style={{ minWidth: 150 }}>
            <Progress
              percent={percent}
              status={
                record.status === 'failed'
                  ? 'exception'
                  : record.status === 'cancelled' ||
                      record.status === 'cancelling'
                    ? 'exception'
                    : record.status === 'completed'
                      ? 'success'
                      : 'active'
              }
              size="small"
              strokeColor={
                record.status === 'cancelled' ? '#ff4d4f' : undefined
              }
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
            {isWorkflow && currentStep && totalSteps && stepName ? (
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Step {currentStep}/{totalSteps}: {stepName}
                </Text>
                {activeSubJob && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {getJobTypeLabel(activeSubJob.type)}
                    </Text>
                    <Progress
                      key={`${activeSubJob.id}-${activeSubJob.progress}`}
                      percent={activeSubJob.progress}
                      size="small"
                      showInfo={false}
                      strokeWidth={4}
                      style={{ marginTop: 2 }}
                    />
                  </div>
                )}
              </div>
            ) : record.processed_items !== undefined &&
              record.total !== undefined &&
              record.total !== null &&
              (record.processed_items > 0 ||
                record.total > 0 ||
                record.status === 'running') ? (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {record.processed_items} / {record.total} items
              </Text>
            ) : null}
          </div>
        );
      },
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => (
        <Tooltip title={new Date(date).toLocaleString()}>
          <Text>{new Date(date).toLocaleTimeString()}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Duration',
      key: 'duration',
      width: 120,
      render: (_: unknown, record: Job) => (
        <Text type="secondary">
          {formatDuration(record.started_at, record.completed_at)}
        </Text>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 250,
      render: (_: unknown, record: Job) => (
        <Space>
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<InfoCircleOutlined />}
              size="small"
              onClick={() => showJobDetails(record)}
            />
          </Tooltip>

          <Tooltip title="View Raw Data">
            <Button
              type="text"
              icon={<CodeOutlined />}
              size="small"
              onClick={() => showRawJobData(record)}
            />
          </Tooltip>

          {(record.type === 'scene_analysis' ||
            record.type === 'analysis' ||
            record.type === 'non_ai_analysis') &&
          ((record.status === 'completed' &&
            record.result &&
            'plan_id' in record.result &&
            record.result.plan_id) ||
            (record.status === 'running' &&
              record.metadata &&
              'plan_id' in record.metadata &&
              record.metadata.plan_id)) ? (
            <Tooltip title="View Plan">
              <Link
                to={`/analysis/plans/${
                  (record.result && 'plan_id' in record.result
                    ? record.result.plan_id
                    : record.metadata?.plan_id) as string
                }`}
              >
                <Button
                  type="text"
                  icon={<FileTextOutlined />}
                  size="small"
                  style={{ color: '#1890ff' }}
                />
              </Link>
            </Tooltip>
          ) : null}

          {shouldShowViewScenesButton(record) && (
            <Tooltip title="View Impacted Scenes">
              <Link
                to={`/scenes?scene_ids=${getJobSceneIds(record)?.join(',') || ''}`}
              >
                <Button
                  type="text"
                  icon={<VideoCameraOutlined />}
                  size="small"
                  style={{ color: '#52c41a' }}
                />
              </Link>
            </Tooltip>
          )}

          {/* View Processed Files for process_downloads jobs */}
          {record.type === 'process_downloads' &&
            record.processed_items !== undefined &&
            record.processed_items !== null &&
            record.processed_items > 0 && (
              <Tooltip title="View Processed Files">
                <Button
                  type="text"
                  icon={<FileTextOutlined />}
                  size="small"
                  style={{ color: '#722ed1' }}
                  onClick={() => {
                    setSelectedHandledDownloadsJobId(record.id);
                    setHandledDownloadsModalVisible(true);
                  }}
                />
              </Tooltip>
            )}

          {['running', 'pending'].includes(record.status) && (
            <Tooltip title="Cancel Job">
              <Button
                type="text"
                danger
                icon={<CloseCircleOutlined />}
                size="small"
                onClick={() => void handleCancel(record.id)}
              />
            </Tooltip>
          )}

          {record.status === 'failed' && (
            <Tooltip title="Retry Job">
              <Button
                type="text"
                icon={<RedoOutlined />}
                size="small"
                onClick={() => void handleRetry(record.id)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // Add keys to jobs for table
  const jobsWithKeys = useMemo(
    () =>
      (Array.isArray(jobs) ? jobs : []).map((job) => ({ ...job, key: job.id })),
    [jobs]
  );

  // Filter jobs by status and type (skip if job ID filter is active)
  const filteredJobs = useMemo(() => {
    // If job ID filter is set, don't apply other filters
    if (jobIdFilter) {
      return jobsWithKeys;
    }

    let filtered = jobsWithKeys;

    if (statusFilter) {
      filtered = filtered.filter((job) => job.status === statusFilter);
    }

    if (typeFilter) {
      filtered = filtered.filter((job) => job.type === typeFilter);
    }

    return filtered;
  }, [jobsWithKeys, statusFilter, typeFilter, jobIdFilter]);

  // Note: failedJobs removed since we no longer display failed job count in header

  const handleStatusFilterChange = (value: string | undefined) => {
    setStatusFilter(value);
    setCurrentPage(1); // Reset to first page when changing filters
    updateSearchParams({
      status: value,
      type: typeFilter,
      job_id: jobIdFilter,
    });
  };

  const handleTypeFilterChange = (value: string | undefined) => {
    setTypeFilter(value);
    setCurrentPage(1); // Reset to first page when changing filters
    updateSearchParams({
      status: statusFilter,
      type: value,
      job_id: jobIdFilter,
    });
  };

  const handleJobIdFilterChange = (value: string) => {
    const trimmedValue = value.trim();
    setJobIdFilter(trimmedValue || undefined);
    setCurrentPage(1); // Reset to first page when changing filters
    updateSearchParams({
      status: statusFilter,
      type: typeFilter,
      job_id: trimmedValue || undefined,
    });
  };

  const updateSearchParams = (params: {
    status?: string;
    type?: string;
    job_id?: string;
  }) => {
    const newParams: Record<string, string> = {};
    if (params.status) newParams.status = params.status;
    if (params.type) newParams.type = params.type;
    if (params.job_id) newParams.job_id = params.job_id;
    if (viewMode !== 'table') newParams.view = viewMode;
    setSearchParams(newParams);
  };

  return (
    <div className={styles.jobMonitor}>
      <div className={styles.header}>
        <Title level={2}>Job Monitor</Title>
      </div>

      <ActiveJobsSection
        onCancel={handleCancel}
        onRetry={handleRetry}
        onRefresh={() => void fetchJobs()}
        onShowDetails={showJobDetails}
        onShowRawData={showRawJobData}
      />

      <Card
        title={`Job History (${totalJobs} total)`}
        className={styles.mainCard}
        extra={
          <Space>
            <Segmented
              value={viewMode}
              options={[
                { label: 'Table', value: 'table', icon: <TableOutlined /> },
                { label: 'Cards', value: 'card', icon: <AppstoreOutlined /> },
              ]}
              onChange={(value: string) => {
                setViewMode(value as 'table' | 'card');
                const newParams = new URLSearchParams(searchParams);
                newParams.set('view', value);
                setSearchParams(newParams);
              }}
            />
            <Select
              placeholder="Filter by status"
              allowClear
              value={statusFilter}
              onChange={handleStatusFilterChange}
              style={{ width: 150 }}
              options={[
                { label: 'All Historical', value: undefined },
                { label: 'Completed', value: 'completed' },
                { label: 'Failed', value: 'failed' },
                { label: 'Cancelled', value: 'cancelled' },
              ]}
            />
            <Select
              placeholder="Filter by type"
              allowClear
              value={typeFilter}
              onChange={handleTypeFilterChange}
              style={{ width: 180 }}
              options={[
                { label: 'All', value: undefined },
                ...Object.entries(JOB_TYPE_LABELS).map(([value, label]) => ({
                  label,
                  value,
                })),
              ]}
            />
            <Input
              placeholder="Filter by Job ID"
              value={jobIdFilter}
              onChange={(e) => handleJobIdFilterChange(e.target.value)}
              onPressEnter={() => void fetchJobs()}
              allowClear
              style={{ width: 200 }}
            />
            <Tooltip
              title={`Refresh Historical Jobs ${!isPageVisible ? '(Auto-refresh paused)' : '(Auto-refresh: 10s)'}`}
            >
              <Button
                icon={<SyncOutlined />}
                onClick={() => void fetchJobs()}
                loading={loading}
                style={{ opacity: !isPageVisible ? 0.6 : 1 }}
              >
                Refresh
              </Button>
            </Tooltip>
          </Space>
        }
      >
        {viewMode === 'table' ? (
          <Table
            columns={columns}
            dataSource={filteredJobs}
            loading={loading}
            rowKey="key"
            expandable={{
              expandedRowRender,
              expandedRowKeys,
              onExpandedRowsChange: setExpandedRowKeys,
              expandRowByClick: false, // Disabled to prevent navigation issues
              rowExpandable: (record: JobWithExpanded) =>
                !!record.metadata?.last_message ||
                !!record.error ||
                !!record.result,
            }}
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total: totalJobs,
              showSizeChanger: true,
              showTotal: (total: number, range: [number, number]) =>
                `${range[0]}-${range[1]} of ${total} historical jobs`,
              onChange: (page: number, size?: number) => {
                setCurrentPage(page);
                if (size && size !== pageSize) {
                  setPageSize(size);
                  setCurrentPage(1); // Reset to first page when changing page size
                }
              },
            }}
            locale={{
              emptyText: (
                <Empty
                  description="No historical jobs found"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              ),
            }}
            rowClassName={(record) =>
              record.status === 'cancelled' ? 'cancelled-job-row' : ''
            }
          />
        ) : (
          <div className={styles.cardView}>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <LoadingOutlined style={{ fontSize: 24 }} />
              </div>
            ) : filteredJobs.length === 0 ? (
              <Empty
                description="No historical jobs found"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ) : (
              <Row gutter={[16, 16]}>
                {filteredJobs.map((job) => (
                  <Col
                    key={job.id}
                    xs={24}
                    sm={24}
                    md={12}
                    lg={12}
                    xl={8}
                    xxl={8}
                  >
                    <JobCard
                      job={job}
                      onCancel={() => void handleCancel(job.id)}
                      onRetry={() => void handleRetry(job.id)}
                      onDelete={() =>
                        void message.info('Delete not implemented yet')
                      }
                      onViewRawData={() => showRawJobData(job)}
                      onViewProcessedFiles={() => {
                        setSelectedHandledDownloadsJobId(job.id);
                        setHandledDownloadsModalVisible(true);
                      }}
                      showDetails={true}
                    />
                  </Col>
                ))}
              </Row>
            )}
          </div>
        )}
      </Card>

      {/* Job Detail Modal */}
      <Modal
        title={
          <Space>
            <InfoCircleOutlined />
            Job Details
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={800}
        bodyStyle={{
          maxHeight: 'calc(80vh - 108px)',
          overflowY: 'auto',
          overflowX: 'hidden',
          position: 'relative',
        }}
        className={styles.jobDetailModalWrapper}
      >
        {selectedJob && (
          <div className={styles.jobDetailModal}>
            <Collapse defaultActiveKey={['basic', 'result']}>
              <Collapse.Panel header="Basic Information" key="basic">
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="Job ID" span={2}>
                    <Space>
                      <Text>{selectedJob.id}</Text>
                      <Tooltip title="Copy Job ID">
                        <Button
                          type="link"
                          icon={<CopyOutlined />}
                          size="small"
                          onClick={() => {
                            void navigator.clipboard.writeText(selectedJob.id);
                            void message.success('Job ID copied to clipboard');
                          }}
                        />
                      </Tooltip>
                    </Space>
                  </Descriptions.Item>
                  <Descriptions.Item label="Type">
                    <Tag color={getJobTypeColor(selectedJob.type)}>
                      {getJobTypeLabel(selectedJob.type)}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Status">
                    <Space>
                      {getStatusIcon(selectedJob.status)}
                      <Tag
                        color={
                          selectedJob.status === 'completed'
                            ? 'success'
                            : selectedJob.status === 'failed'
                              ? 'error'
                              : selectedJob.status === 'running'
                                ? 'processing'
                                : selectedJob.status === 'pending'
                                  ? 'orange'
                                  : selectedJob.status === 'cancelled'
                                    ? 'warning'
                                    : 'default'
                        }
                      >
                        {selectedJob.status.toUpperCase()}
                      </Tag>
                    </Space>
                  </Descriptions.Item>
                  <Descriptions.Item label="Progress" span={2}>
                    <Progress
                      percent={selectedJob.progress}
                      status={
                        selectedJob.status === 'failed'
                          ? 'exception'
                          : selectedJob.status === 'cancelled' ||
                              selectedJob.status === 'cancelling'
                            ? 'exception'
                            : selectedJob.status === 'completed'
                              ? 'success'
                              : 'active'
                      }
                      strokeColor={
                        selectedJob.status === 'cancelled'
                          ? '#ff4d4f'
                          : undefined
                      }
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="Created">
                    {new Date(selectedJob.created_at).toLocaleString()}
                  </Descriptions.Item>
                  <Descriptions.Item label="Duration">
                    {formatDuration(
                      selectedJob.started_at,
                      selectedJob.completed_at
                    )}
                  </Descriptions.Item>
                </Descriptions>

                {selectedJob.metadata?.last_message && (
                  <div style={{ marginTop: 16 }}>
                    <Alert
                      message="Last Message"
                      description={selectedJob.metadata.last_message}
                      type="info"
                      showIcon
                    />
                  </div>
                )}

                {selectedJob.error && (
                  <div style={{ marginTop: 16 }}>
                    <Alert
                      message="Job Failed"
                      description={selectedJob.error}
                      type="error"
                      showIcon
                    />
                  </div>
                )}
              </Collapse.Panel>

              {selectedJob.parameters &&
                Object.keys(selectedJob.parameters).length > 0 && (
                  <Collapse.Panel header="Parameters" key="parameters">
                    <pre className={styles.codeBlock}>
                      {JSON.stringify(selectedJob.parameters, null, 2)}
                    </pre>
                  </Collapse.Panel>
                )}

              {selectedJob.result &&
                Object.keys(selectedJob.result).length > 0 && (
                  <Collapse.Panel header="Result" key="result">
                    {selectedJob.type === 'scene_analysis' ||
                    selectedJob.type === 'analysis' ||
                    selectedJob.type === 'non_ai_analysis' ? (
                      <>
                        <AnalysisJobResult
                          result={
                            selectedJob.result as unknown as AnalysisJobResultData
                          }
                        />
                        {((selectedJob.result &&
                          'plan_id' in selectedJob.result &&
                          selectedJob.result.plan_id) ||
                          (selectedJob.metadata &&
                            'plan_id' in selectedJob.metadata &&
                            selectedJob.metadata.plan_id)) && (
                          <div style={{ marginTop: 16 }}>
                            <Link
                              to={`/analysis/plans/${
                                (selectedJob.result &&
                                'plan_id' in selectedJob.result
                                  ? selectedJob.result.plan_id
                                  : selectedJob.metadata?.plan_id) as string
                              }`}
                            >
                              <Button
                                type="primary"
                                icon={<FileTextOutlined />}
                              >
                                View{' '}
                                {selectedJob.status === 'running'
                                  ? 'Current'
                                  : 'Created'}{' '}
                                Analysis Plan
                              </Button>
                            </Link>
                          </div>
                        )}
                      </>
                    ) : (
                      <pre className={styles.codeBlock}>
                        {JSON.stringify(selectedJob.result, null, 2)}
                      </pre>
                    )}
                  </Collapse.Panel>
                )}

              {selectedJob.metadata &&
                Object.keys(selectedJob.metadata).length > 1 && (
                  <Collapse.Panel header="Metadata" key="metadata">
                    <pre className={styles.codeBlock}>
                      {JSON.stringify(
                        Object.fromEntries(
                          Object.entries(selectedJob.metadata).filter(
                            ([key]) => key !== 'last_message'
                          )
                        ),
                        null,
                        2
                      )}
                    </pre>
                  </Collapse.Panel>
                )}
            </Collapse>
          </div>
        )}
      </Modal>

      {/* Workflow Job Modal */}
      {selectedWorkflowJob && (
        <WorkflowJobModal
          job={selectedWorkflowJob}
          visible={workflowModalVisible}
          onClose={() => {
            setWorkflowModalVisible(false);
            setSelectedWorkflowJob(null);
          }}
          onCancel={
            selectedWorkflowJob.status === 'running'
              ? () => void handleCancel(selectedWorkflowJob.id)
              : undefined
          }
          onRetry={
            selectedWorkflowJob.status === 'failed'
              ? () => void handleRetry(selectedWorkflowJob.id)
              : undefined
          }
          onDelete={() => void message.info('Delete not implemented yet')}
        />
      )}

      {/* Raw Job Data Modal */}
      <Modal
        title={
          <Space>
            <CodeOutlined />
            Raw Job Data
          </Space>
        }
        open={rawDataModalVisible}
        onCancel={() => {
          setRawDataModalVisible(false);
          setSelectedRawDataJob(null);
        }}
        footer={[
          <Button
            key="close"
            onClick={() => {
              setRawDataModalVisible(false);
              setSelectedRawDataJob(null);
            }}
          >
            Close
          </Button>,
        ]}
        width={800}
        bodyStyle={{
          maxHeight: 'calc(80vh - 108px)',
          overflowY: 'auto',
        }}
      >
        {selectedRawDataJob && (
          <div>
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="Job ID">
                <Space>
                  <Text>{selectedRawDataJob.id}</Text>
                  <Tooltip title="Copy Job ID">
                    <Button
                      type="link"
                      icon={<CopyOutlined />}
                      size="small"
                      onClick={() => {
                        void navigator.clipboard.writeText(
                          selectedRawDataJob.id
                        );
                        void message.success('Job ID copied to clipboard');
                      }}
                    />
                  </Tooltip>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Name">
                {selectedRawDataJob.name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Type">
                <Tag color={getJobTypeColor(selectedRawDataJob.type)}>
                  {getJobTypeLabel(selectedRawDataJob.type)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag
                  color={
                    selectedRawDataJob.status === 'completed'
                      ? 'success'
                      : selectedRawDataJob.status === 'failed'
                        ? 'error'
                        : selectedRawDataJob.status === 'running'
                          ? 'processing'
                          : selectedRawDataJob.status === 'pending'
                            ? 'orange'
                            : selectedRawDataJob.status === 'cancelled'
                              ? 'warning'
                              : 'default'
                  }
                >
                  {selectedRawDataJob.status.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Progress">
                {selectedRawDataJob.progress}%
              </Descriptions.Item>
              <Descriptions.Item label="Created At">
                {new Date(selectedRawDataJob.created_at).toLocaleString()}
              </Descriptions.Item>
              {selectedRawDataJob.started_at && (
                <Descriptions.Item label="Started At">
                  {new Date(selectedRawDataJob.started_at).toLocaleString()}
                </Descriptions.Item>
              )}
              {selectedRawDataJob.completed_at && (
                <Descriptions.Item label="Completed At">
                  {new Date(selectedRawDataJob.completed_at).toLocaleString()}
                </Descriptions.Item>
              )}
            </Descriptions>

            <Title level={5} style={{ marginTop: 16 }}>
              Full JSON Data
            </Title>
            <pre
              style={{
                background: '#f5f5f5',
                padding: '12px',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '12px',
                fontFamily: 'monospace',
              }}
            >
              {JSON.stringify(selectedRawDataJob, null, 2)}
            </pre>
          </div>
        )}
      </Modal>

      {/* Handled Downloads Modal */}
      {selectedHandledDownloadsJobId && (
        <HandledDownloadsModal
          jobId={selectedHandledDownloadsJobId}
          visible={handledDownloadsModalVisible}
          onClose={() => {
            setHandledDownloadsModalVisible(false);
            setSelectedHandledDownloadsJobId(null);
          }}
        />
      )}
    </div>
  );
};

export default JobMonitor;
