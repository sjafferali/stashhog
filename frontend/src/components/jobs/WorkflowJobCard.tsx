import React, { useState, useEffect } from 'react';
import {
  Card,
  Progress,
  Tag,
  Space,
  Button,
  Typography,
  Tooltip,
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
import { getJobTypeLabel, getJobTypeColor } from '@/utils/jobUtils';
import { WorkflowJobModal } from './WorkflowJobModal';
import styles from './WorkflowJobCard.module.scss';

const { Text, Title } = Typography;

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
  { title: 'Final Sync', description: 'Sync any pending updates' },
  { title: 'Complete', description: 'Workflow finished' },
];

export const WorkflowJobCard: React.FC<WorkflowJobCardProps> = ({
  job,
  onCancel,
  onRetry,
  onDelete,
}) => {
  const [modalVisible, setModalVisible] = useState(false);
  const [localJob, setLocalJob] = useState(job);
  const metadata = localJob.metadata as WorkflowMetadata | undefined;
  const currentStep = metadata?.current_step || 0;
  const stepName = metadata?.step_name || '';
  const activeSubJob = metadata?.active_sub_job;

  // Update local job when props change
  useEffect(() => {
    setLocalJob(job);
  }, [job]);

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
            key={`${activeSubJob.id}-${activeSubJob.progress}`}
            percent={activeSubJob.progress}
            size="small"
            status={activeSubJob.status === 'running' ? 'active' : undefined}
          />
        </Space>
      </div>
    );
  };

  return (
    <>
      <Card
        className={styles.workflowJobCard}
        data-status={job.status}
        title={
          <div className={styles.cardHeader}>
            <Space>
              {getStatusIcon()}
              <Title level={5} style={{ margin: 0 }}>
                {job.name || 'Process New Scenes Workflow'}
              </Title>
            </Space>
            <Tag color={getStatusColor()}>{job.status.toUpperCase()}</Tag>
          </div>
        }
        extra={<Space>{actions}</Space>}
        onClick={() => setModalVisible(true)}
        style={{ cursor: 'pointer' }}
      >
        <div className={styles.content}>
          <div className={styles.jobIdSection}>
            <Text type="secondary">Job ID: </Text>
            <Text
              copyable
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            >
              {job.id}
            </Text>
          </div>

          <div className={styles.stepsPreview}>
            <Text type="secondary">Current Step:</Text>
            <Text strong>
              {currentStep > 0 && currentStep <= 7
                ? `${currentStep}/7 - ${WORKFLOW_STEPS[currentStep - 1]?.title}`
                : 'Initializing...'}
            </Text>
          </div>

          <div className={styles.quickInfo}>
            <Space size="middle" wrap>
              <Tooltip title="Job Type">
                <Tag color={getJobTypeColor(job.type)}>
                  {getJobTypeLabel(job.type)}
                </Tag>
              </Tooltip>
              <Tooltip title="Created">
                <Text type="secondary">
                  <ClockCircleOutlined />{' '}
                  {new Date(job.created_at).toLocaleTimeString()}
                </Text>
              </Tooltip>
            </Space>
          </div>

          <div className={styles.progressSection}>
            <div className={styles.progressInfo}>
              <Text type="secondary">Overall Progress</Text>
              <Text>
                {currentStep > 0 && currentStep <= 7
                  ? `Step ${currentStep}/7: ${stepName}`
                  : 'Initializing...'}
              </Text>
            </div>
            <Progress
              percent={job.progress}
              status={
                job.status === 'failed'
                  ? 'exception'
                  : job.status === 'cancelled' || job.status === 'cancelling'
                    ? 'exception'
                    : job.status === 'running'
                      ? 'active'
                      : undefined
              }
              strokeColor={job.status === 'cancelled' ? '#ff4d4f' : undefined}
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
                // Force re-render when activeSubJob changes
                key: `collapse-${activeSubJob.id}-${activeSubJob.progress}`,
              } as unknown as Record<string, unknown>)}
            />
          )}

          <div className={styles.clickHint}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              Click card to view full details
            </Text>
          </div>
        </div>
      </Card>

      <WorkflowJobModal
        job={localJob}
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        onCancel={onCancel}
        onRetry={onRetry}
        onDelete={onDelete}
      />
    </>
  );
};
