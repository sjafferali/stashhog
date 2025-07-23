import React, { useEffect, useState, useRef } from 'react';
import {
  Card,
  Progress,
  Space,
  Button,
  Typography,
  Timeline,
  Tag,
  Alert,
  Spin,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  DownOutlined,
  UpOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { Job } from '@/types/models';
import { getJobTypeLabel } from '@/utils/jobUtils';
// import { useWebSocketStore } from '@/store/websocket';
import styles from './JobProgress.module.scss';

const { Text, Title } = Typography;

export interface JobProgressProps {
  jobId: string;
  onComplete?: (result: Record<string, unknown>) => void;
  showDetails?: boolean;
  autoScroll?: boolean;
  maxLogEntries?: number;
}

interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
}

export const JobProgress: React.FC<JobProgressProps> = ({
  jobId,
  // onComplete,
  showDetails = true,
  autoScroll = true,
  // maxLogEntries = 100,
}) => {
  const [job, setJob] = useState<Job | null>(null);
  const [logs] = useState<LogEntry[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // const { subscribe, unsubscribe } = useWebSocketStore();

  useEffect(() => {
    // Fetch initial job data
    void fetchJob();

    // Subscribe to job updates
    // TODO: Implement WebSocket subscription when available
    // const unsubscribeJob = subscribe(`job:${jobId}`, (data) => {
    //   if (data.type === 'job_update') {
    //     setJob(data.job);
    //     if (data.job.status === 'completed' && onComplete) {
    //       onComplete(data.job.result);
    //     }
    //   } else if (data.type === 'job_log') {
    //     addLog(data.log);
    //   }
    // });

    // Poll for updates as a temporary solution
    const interval = setInterval(() => {
      if (job && (job.status === 'running' || job.status === 'pending')) {
        void fetchJob();
      }
    }, 2000);

    return () => {
      clearInterval(interval);
      // unsubscribeJob();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]); // fetchJob is stable and job dependency would cause re-polling issues

  useEffect(() => {
    if (autoScroll && showLogs && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, showLogs, autoScroll]);

  const fetchJob = async () => {
    try {
      const response = await fetch(`/api/jobs/${jobId}`);
      const data = await response.json();
      setJob(data);
      setIsLoading(false);
    } catch (error) {
      console.error('Failed to fetch job:', error);
      setIsLoading(false);
    }
  };

  // const _addLog = (log: LogEntry) => {
  //   setLogs((prev) => {
  //     const newLogs = [...prev, log];
  //     if (newLogs.length > maxLogEntries) {
  //       return newLogs.slice(-maxLogEntries);
  //     }
  //     return newLogs;
  //   });
  // };

  const handleCancel = async () => {
    try {
      await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
    } catch (error) {
      console.error('Failed to cancel job:', error);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <Spin tip="Loading job details..." />
      </Card>
    );
  }

  if (!job) {
    return (
      <Alert
        message="Job not found"
        description={`Job with ID ${jobId} could not be found.`}
        type="error"
      />
    );
  }

  const progressPercent = job.progress; // job.progress is already a percentage (0-100)

  const getStatusIcon = () => {
    switch (job.status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
    }
  };

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'warning':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      default:
        return <SyncOutlined style={{ color: '#1890ff' }} />;
    }
  };

  const getLogColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'red';
      case 'warning':
        return 'orange';
      case 'success':
        return 'green';
      default:
        return 'blue';
    }
  };

  return (
    <Card className={styles.jobProgress}>
      <div className={styles.header}>
        <Space>
          {getStatusIcon()}
          <Title level={4}>
            {job.name || `${getJobTypeLabel(job.type)} Job`}
          </Title>
          <Tag
            color={
              job.status === 'completed'
                ? 'green'
                : job.status === 'failed'
                  ? 'red'
                  : 'blue'
            }
          >
            {job.status.toUpperCase()}
          </Tag>
        </Space>

        {job.status === 'running' && (
          <Button danger onClick={() => void handleCancel()}>
            Cancel
          </Button>
        )}
      </div>

      <div className={styles.progressSection}>
        <div className={styles.progressInfo}>
          <Text>
            Progress:{' '}
            {job.total && job.processed_items !== undefined
              ? `${job.processed_items} / ${job.total}`
              : `${Math.round(job.progress)}%`}
          </Text>
          <Text type="secondary">{progressPercent.toFixed(0)}%</Text>
        </div>
        <Progress
          percent={progressPercent}
          status={
            job.status === 'failed'
              ? 'exception'
              : job.status === 'completed'
                ? 'success'
                : 'active'
          }
          strokeColor={
            job.status === 'running'
              ? { '0%': '#108ee9', '100%': '#87d068' }
              : undefined
          }
        />
      </div>

      {job.error && (
        <Alert
          message="Job Failed"
          description={job.error}
          type="error"
          showIcon
          className={styles.error}
        />
      )}

      {showDetails && logs.length > 0 && (
        <div className={styles.logsSection}>
          <div className={styles.logsHeader}>
            <Text strong>Activity Log</Text>
            <Button
              type="text"
              size="small"
              icon={showLogs ? <UpOutlined /> : <DownOutlined />}
              onClick={() => setShowLogs(!showLogs)}
            >
              {showLogs ? 'Hide' : 'Show'} Logs
            </Button>
          </div>

          {showLogs && (
            <div className={styles.logs}>
              <Timeline>
                {logs.map((log, index) => (
                  <Timeline.Item
                    key={index}
                    dot={getLogIcon(log.level)}
                    color={getLogColor(log.level)}
                  >
                    <div className={styles.logEntry}>
                      <Space>
                        <Text type="secondary" className={styles.timestamp}>
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </Text>
                        <Tag color={getLogColor(log.level)}>{log.level}</Tag>
                      </Space>
                      <Text>{log.message}</Text>
                    </div>
                  </Timeline.Item>
                ))}
              </Timeline>
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      )}

      {job.result && job.status === 'completed' && (
        <>
          <Alert
            message="Job Completed"
            description={
              <div>
                <Text>Result:</Text>
                <pre className={styles.result}>
                  {JSON.stringify(job.result, null, 2)}
                </pre>
              </div>
            }
            type="success"
            showIcon
          />
          {(job.type === 'scene_analysis' || job.type === 'analysis') &&
            job.result.plan_id && (
              <div className={styles.planLink}>
                <Link to={`/analysis/plans/${job.result.plan_id}`}>
                  <Button
                    type="primary"
                    icon={<FileTextOutlined />}
                    size="large"
                  >
                    View Created Analysis Plan
                  </Button>
                </Link>
              </div>
            )}
        </>
      )}
    </Card>
  );
};
