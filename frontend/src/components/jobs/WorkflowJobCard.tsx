import React from 'react';
import {
  Card,
  Progress,
  Tag,
  Space,
  Button,
  Typography,
  Tooltip,
  Descriptions,
  Steps,
  Collapse,
  Badge,
} from 'antd';
import {
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  RedoOutlined,
  DeleteOutlined,
  LoadingOutlined,
  CaretRightOutlined,
} from '@ant-design/icons';
import { Job } from '@/types/models';
import { getJobTypeLabel } from '@/utils/jobUtils';
import styles from './WorkflowJobCard.module.scss';

const { Text, Title } = Typography;
const { Step } = Steps;

export interface WorkflowJobCardProps {
  job: Job;
  onCancel?: () => void;
  onRetry?: () => void;
  onDelete?: () => void;
}

interface WorkflowMetadata {
  current_step?: number;
  total_steps?: number;
  step_name?: string;
  active_sub_job?: {
    id: string;
    type: string;
    status: string;
    progress: number;
  };
  message?: string;
}

const WORKFLOW_STEPS = [
  { title: 'Process Downloads', description: 'Download and sync new content' },
  { title: 'Scan Metadata', description: 'Update Stash library metadata' },
  { title: 'Incremental Sync', description: 'Import new scenes' },
  { title: 'Analyze Scenes', description: 'Process unanalyzed scenes' },
  { title: 'Generate Metadata', description: 'Create previews and sprites' },
  { title: 'Complete', description: 'Workflow finished' },
];

export const WorkflowJobCard: React.FC<WorkflowJobCardProps> = ({
  job,
  onCancel,
  onRetry,
  onDelete,
}) => {
  const metadata = job.metadata as WorkflowMetadata | undefined;
  const currentStep = metadata?.current_step || 0;
  const stepName = metadata?.step_name || '';
  const activeSubJob = metadata?.active_sub_job;

  const getStatusIcon = () => {
    switch (job.status) {
      case 'pending':
        return <ClockCircleOutlined />;
      case 'running':
      case 'cancelling':
        return <LoadingOutlined />;
      case 'completed':
        return <CheckCircleOutlined />;
      case 'failed':
      case 'cancelled':
        return <CloseCircleOutlined />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (job.status) {
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
      case 'cancelling':
        return 'orange';
      default:
        return 'default';
    }
  };

  const formatDuration = () => {
    if (!job.started_at) return null;

    const start = new Date(job.started_at).getTime();
    const end = job.completed_at
      ? new Date(job.completed_at).getTime()
      : Date.now();
    const duration = end - start;

    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    }
    if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    }
    return `${seconds}s`;
  };

  const getStepStatus = (stepIndex: number) => {
    // Step indices are 0-based, but current_step is 1-based
    const adjustedCurrent = currentStep - 1;

    if (job.status === 'failed' || job.status === 'cancelled') {
      if (stepIndex < adjustedCurrent) return 'finish';
      if (stepIndex === adjustedCurrent) return 'error';
      return 'wait';
    }

    if (stepIndex < adjustedCurrent) return 'finish';
    if (stepIndex === adjustedCurrent) return 'process';
    return 'wait';
  };

  const actions = [];

  if (job.status === 'running' && onCancel) {
    actions.push(
      <Tooltip key="cancel" title="Cancel">
        <Button
          type="text"
          danger
          icon={<CloseCircleOutlined />}
          onClick={onCancel}
        />
      </Tooltip>
    );
  }

  if (job.status === 'failed' && onRetry) {
    actions.push(
      <Tooltip key="retry" title="Retry">
        <Button type="text" icon={<RedoOutlined />} onClick={onRetry} />
      </Tooltip>
    );
  }

  if (
    (job.status === 'completed' ||
      job.status === 'failed' ||
      job.status === 'cancelled') &&
    onDelete
  ) {
    actions.push(
      <Tooltip key="delete" title="Delete">
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={onDelete}
        />
      </Tooltip>
    );
  }

  const renderSubJobInfo = () => {
    if (!activeSubJob) return null;

    return (
      <div className={styles.subJobInfo}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div className={styles.subJobHeader}>
            <Text type="secondary">Active Sub-Job</Text>
            <Badge
              status={
                activeSubJob.status === 'running'
                  ? 'processing'
                  : activeSubJob.status === 'completed'
                    ? 'success'
                    : 'error'
              }
              text={getJobTypeLabel(activeSubJob.type)}
            />
          </div>
          <Progress
            percent={activeSubJob.progress}
            size="small"
            status={activeSubJob.status === 'running' ? 'active' : undefined}
          />
        </Space>
      </div>
    );
  };

  return (
    <Card
      className={styles.workflowJobCard}
      title={
        <div className={styles.cardHeader}>
          <Space>
            {getStatusIcon()}
            <Title level={5}>{job.name || 'Process New Scenes Workflow'}</Title>
          </Space>
          <Tag color={getStatusColor()}>{job.status.toUpperCase()}</Tag>
        </div>
      }
      extra={<Space>{actions}</Space>}
    >
      <div className={styles.content}>
        <div className={styles.stepsSection}>
          <Steps
            current={currentStep - 1}
            size="small"
            className={styles.workflowSteps}
          >
            {WORKFLOW_STEPS.map((step, index) => (
              <Step
                key={index}
                title={step.title}
                description={step.description}
                status={getStepStatus(index)}
                icon={
                  getStepStatus(index) === 'process' ? (
                    <LoadingOutlined />
                  ) : undefined
                }
              />
            ))}
          </Steps>
        </div>

        <div className={styles.progressSection}>
          <div className={styles.progressInfo}>
            <Text type="secondary">Overall Progress</Text>
            <Text>
              {currentStep > 0 && currentStep <= 6
                ? `Step ${currentStep}/6: ${stepName}`
                : 'Initializing...'}
            </Text>
          </div>
          <Progress
            percent={job.progress}
            status={
              job.status === 'failed'
                ? 'exception'
                : job.status === 'running'
                  ? 'active'
                  : undefined
            }
          />
        </div>

        {activeSubJob && (
          <Collapse
            {...({
              items: [
                {
                  key: '1',
                  label: 'Sub-Job Details',
                  children: renderSubJobInfo(),
                },
              ],
              expandIcon: ({ isActive }: { isActive?: boolean }) => (
                <CaretRightOutlined rotate={isActive ? 90 : 0} />
              ),
              className: styles.subJobCollapse,
            } as unknown as Record<string, unknown>)}
          />
        )}

        <Descriptions column={2} size="small" className={styles.details}>
          <Descriptions.Item label="Type">
            <Tag color="purple">{getJobTypeLabel(job.type)}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Duration">
            {formatDuration() || 'N/A'}
          </Descriptions.Item>
          <Descriptions.Item label="Created">
            {new Date(job.created_at).toLocaleString()}
          </Descriptions.Item>
          {job.started_at && (
            <Descriptions.Item label="Started">
              {new Date(job.started_at).toLocaleString()}
            </Descriptions.Item>
          )}
          {job.completed_at && (
            <Descriptions.Item label="Completed" span={2}>
              {new Date(job.completed_at).toLocaleString()}
            </Descriptions.Item>
          )}
        </Descriptions>

        {job.error && (
          <div className={styles.error}>
            <Text type="danger" strong>
              Error:
            </Text>
            <Text type="danger">{job.error}</Text>
          </div>
        )}

        {job.result && Object.keys(job.result).length > 0 && (
          <Collapse
            {...({
              items: [
                {
                  key: '1',
                  label: 'Workflow Summary',
                  children: (
                    <Descriptions column={1} size="small">
                      {job.result.summary &&
                        Object.entries(
                          job.result.summary as Record<string, unknown>
                        ).map(([key, value]) => (
                          <Descriptions.Item
                            key={key}
                            label={key
                              .replace(/_/g, ' ')
                              .replace(/\b\w/g, (l) => l.toUpperCase())}
                          >
                            {typeof value === 'object'
                              ? JSON.stringify(value)
                              : String(value)}
                          </Descriptions.Item>
                        ))}
                    </Descriptions>
                  ),
                },
              ],
              expandIcon: ({ isActive }: { isActive?: boolean }) => (
                <CaretRightOutlined rotate={isActive ? 90 : 0} />
              ),
              className: styles.resultCollapse,
            } as unknown as Record<string, unknown>)}
          />
        )}
      </div>
    </Card>
  );
};
