import React from 'react';
import {
  Card,
  Statistic,
  Row,
  Col,
  Progress,
  Tag,
  Button,
  Space,
  Divider,
  Typography,
  Tooltip,
  Descriptions,
  Badge,
} from 'antd';
import {
  CheckCircleOutlined,
  SyncOutlined,
  DeleteOutlined,
  BarChartOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  UserOutlined,
  TagsOutlined,
  HomeOutlined,
} from '@ant-design/icons';
import { AnalysisPlan } from '@/types/models';
import styles from './PlanSummary.module.scss';

const { Title, Text } = Typography;

export interface PlanStatistics {
  totalScenes: number;
  analyzedScenes: number;
  pendingScenes: number;
  totalChanges: number;
  acceptedChanges: number;
  rejectedChanges: number;
  avgConfidence: number;
  avgProcessingTime: number;
  fieldBreakdown: {
    title: number;
    date: number;
    details: number;
    performers: number;
    tags: number;
    studio: number;
    custom: number;
  };
}

export interface PlanSummaryProps {
  plan: AnalysisPlan;
  statistics: PlanStatistics;
  onApply?: () => void;
  onDelete?: () => void;
  loading?: boolean;
}

export const PlanSummary: React.FC<PlanSummaryProps> = ({
  plan,
  statistics,
  onApply,
  onDelete,
  loading = false,
}) => {
  const acceptanceRate =
    statistics.totalChanges > 0
      ? (statistics.acceptedChanges / statistics.totalChanges) * 100
      : 0;

  const completionRate =
    statistics.totalScenes > 0
      ? (statistics.analyzedScenes / statistics.totalScenes) * 100
      : 0;

  const getStatusColor = () => {
    if (!plan.active) return 'default';
    if (completionRate === 100) return 'success';
    if (completionRate > 0) return 'processing';
    return 'warning';
  };

  const getStatusText = () => {
    if (!plan.active) return 'Inactive';
    if (completionRate === 100) return 'Complete';
    if (completionRate > 0) return 'In Progress';
    return 'Not Started';
  };

  const fieldIcons = {
    title: <FileTextOutlined />,
    date: <ClockCircleOutlined />,
    details: <FileTextOutlined />,
    performers: <UserOutlined />,
    tags: <TagsOutlined />,
    studio: <HomeOutlined />,
    custom: <BarChartOutlined />,
  };

  return (
    <Card className={styles.planSummary}>
      <div className={styles.header}>
        <div>
          <Title level={4}>
            <span>{plan.name}</span>
            <Badge
              status={
                getStatusColor() as
                  | 'success'
                  | 'processing'
                  | 'default'
                  | 'error'
                  | 'warning'
              }
              text={getStatusText()}
              className={styles.status}
            />
          </Title>
          {plan.description && <Text type="secondary">{plan.description}</Text>}
        </div>
        <Space>
          {onApply && (
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={onApply}
              loading={loading}
              disabled={statistics.pendingScenes === 0}
            >
              Apply Changes
            </Button>
          )}
          {onDelete && (
            <Tooltip title="Delete Plan">
              <Button danger icon={<DeleteOutlined />} onClick={onDelete} />
            </Tooltip>
          )}
        </Space>
      </div>

      <Divider />

      <Row gutter={[16, 16]}>
        <Col xs={12} sm={6}>
          <Statistic
            title="Total Scenes"
            value={statistics.totalScenes}
            prefix={<BarChartOutlined />}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="Analyzed"
            value={statistics.analyzedScenes}
            valueStyle={{ color: '#52c41a' }}
            prefix={<CheckCircleOutlined />}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="Pending"
            value={statistics.pendingScenes}
            valueStyle={{ color: '#faad14' }}
            prefix={<SyncOutlined />}
          />
        </Col>
        {statistics.avgProcessingTime > 0 && (
          <Col xs={12} sm={6}>
            <Statistic
              title="Avg Processing"
              value={statistics.avgProcessingTime}
              suffix="ms"
              precision={0}
              prefix={<ClockCircleOutlined />}
            />
          </Col>
        )}
      </Row>

      <div className={styles.progressSection}>
        <div className={styles.progressHeader}>
          <Text>Analysis Progress</Text>
          <Text>{completionRate.toFixed(0)}%</Text>
        </div>
        <Progress
          percent={completionRate}
          showInfo={false}
          status={completionRate === 100 ? 'success' : 'active'}
        />
      </div>

      <Divider />

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title="Change Statistics">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div className={styles.statRow}>
                <Text>Total Changes</Text>
                <Tag>{statistics.totalChanges}</Tag>
              </div>
              <div className={styles.statRow}>
                <Text>Accepted</Text>
                <Tag color="green">{statistics.acceptedChanges}</Tag>
              </div>
              <div className={styles.statRow}>
                <Text>Rejected</Text>
                <Tag color="red">{statistics.rejectedChanges}</Tag>
              </div>
              <div className={styles.statRow}>
                <Text>Acceptance Rate</Text>
                <Progress
                  percent={acceptanceRate}
                  size="small"
                  status={
                    acceptanceRate >= 80
                      ? 'success'
                      : acceptanceRate >= 50
                        ? 'normal'
                        : 'exception'
                  }
                />
              </div>
              <div className={styles.statRow}>
                <Text>Avg Confidence</Text>
                <Progress
                  percent={statistics.avgConfidence * 100}
                  size="small"
                  format={(percent?: number) => `${percent?.toFixed(0)}%`}
                />
              </div>
            </Space>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card size="small" title="Field Breakdown">
            <Space direction="vertical" style={{ width: '100%' }}>
              {Object.entries(statistics.fieldBreakdown).map(
                ([field, count]) => (
                  <div key={field} className={styles.fieldRow}>
                    <Space>
                      {fieldIcons[field as keyof typeof fieldIcons]}
                      <Text className={styles.fieldName}>
                        {field.charAt(0).toUpperCase() + field.slice(1)}
                      </Text>
                    </Space>
                    <Tag>{count}</Tag>
                  </div>
                )
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      <Divider />

      <Descriptions column={2} size="small">
        <Descriptions.Item label="Model">
          <Tag color="blue">{plan.model}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Temperature">
          {plan.temperature}
        </Descriptions.Item>
        <Descriptions.Item label="Max Tokens">
          {plan.max_tokens || 'Default'}
        </Descriptions.Item>
        <Descriptions.Item label="Created">
          {new Date(plan.created_at).toLocaleDateString()}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};
