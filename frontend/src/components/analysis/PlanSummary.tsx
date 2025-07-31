import React, { useState } from 'react';
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
  Collapse,
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
  PushpinOutlined,
} from '@ant-design/icons';
import { AnalysisPlan } from '@/types/models';
import styles from './PlanSummary.module.scss';

const { Text } = Typography;
const { Panel } = Collapse;

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
    markers: number;
    custom: number;
  };
}

export interface PlanSummaryProps {
  plan: AnalysisPlan;
  statistics: PlanStatistics;
  onApply?: () => void;
  onDelete?: () => void;
  loading?: boolean;
  jobProgress?: number;
}

export const PlanSummary: React.FC<PlanSummaryProps> = ({
  plan,
  statistics,
  onApply,
  onDelete,
  loading = false,
  jobProgress,
}) => {
  const [windowWidth, setWindowWidth] = useState(
    typeof window !== 'undefined' ? window.innerWidth : 1024
  );

  React.useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isMobile = windowWidth < 768;

  const acceptanceRate =
    statistics.totalChanges > 0
      ? (statistics.acceptedChanges / statistics.totalChanges) * 100
      : 0;

  const completionRate =
    jobProgress !== undefined && plan.status.toLowerCase() === 'pending'
      ? jobProgress
      : statistics.totalScenes > 0
        ? (statistics.analyzedScenes / statistics.totalScenes) * 100
        : 0;

  const fieldIcons = {
    title: <FileTextOutlined />,
    date: <ClockCircleOutlined />,
    details: <FileTextOutlined />,
    performers: <UserOutlined />,
    tags: <TagsOutlined />,
    studio: <HomeOutlined />,
    markers: <PushpinOutlined />,
    custom: <BarChartOutlined />,
  };

  return (
    <Card className={styles.planSummary}>
      <div className={styles.header}>
        <div>
          <div style={{ marginBottom: 8 }}>
            <Text strong style={{ marginRight: 8 }}>
              Plan Status:
            </Text>
            <Tag
              color={
                plan.status.toLowerCase() === 'pending'
                  ? 'purple'
                  : plan.status.toLowerCase() === 'draft'
                    ? 'blue'
                    : plan.status.toLowerCase() === 'reviewing'
                      ? 'orange'
                      : plan.status.toLowerCase() === 'applied'
                        ? 'green'
                        : plan.status.toLowerCase() === 'cancelled'
                          ? 'red'
                          : 'default'
              }
              style={{ fontWeight: 500, fontSize: '14px' }}
            >
              {plan.status.toUpperCase()}
            </Tag>
          </div>
          {plan.description && <Text type="secondary">{plan.description}</Text>}
        </div>
        <Space>
          {onApply && (
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={onApply}
              loading={loading}
              disabled={
                statistics.pendingScenes === 0 ||
                plan.status === 'pending' ||
                plan.status === 'applied' ||
                plan.status === 'cancelled'
              }
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
        <Col xs={12} sm={12} md={6}>
          <div className={styles.statisticWrapper}>
            <Statistic
              title="Scenes"
              value={statistics.totalScenes}
              prefix={<BarChartOutlined />}
            />
          </div>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <div className={styles.statisticWrapper}>
            <Statistic
              title="Analyzed"
              value={statistics.analyzedScenes}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </div>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <div className={styles.statisticWrapper}>
            <Statistic
              title="Pending"
              value={statistics.pendingScenes}
              valueStyle={{ color: '#faad14' }}
              prefix={<SyncOutlined />}
            />
          </div>
        </Col>
        {statistics.avgProcessingTime > 0 && (
          <Col xs={12} sm={12} md={6}>
            <div className={styles.statisticWrapper}>
              <Statistic
                title="Avg Time"
                value={statistics.avgProcessingTime}
                suffix="ms"
                precision={0}
                prefix={<ClockCircleOutlined />}
              />
            </div>
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

      {isMobile ? (
        <div className={styles.mobileCollapse}>
          <Collapse defaultActiveKey={['1']}>
            <Panel header="Change Statistics" key="1">
              <div className={styles.mobileStatContent}>
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
                <div className={styles.statRowProgress}>
                  <Text>Acceptance Rate</Text>
                  <Progress
                    percent={acceptanceRate}
                    size="small"
                    className={styles.progressBar}
                    status={
                      acceptanceRate >= 80
                        ? 'success'
                        : acceptanceRate >= 50
                          ? 'normal'
                          : 'exception'
                    }
                  />
                </div>
                <div className={styles.statRowProgress}>
                  <Text>Avg Confidence</Text>
                  <Progress
                    percent={statistics.avgConfidence * 100}
                    size="small"
                    className={styles.progressBar}
                    format={(percent?: number) => `${percent?.toFixed(0)}%`}
                  />
                </div>
              </div>
            </Panel>
            <Panel header="Field Breakdown" key="2">
              <div className={styles.mobileStatContent}>
                {Object.entries(statistics.fieldBreakdown).map(
                  ([field, count]) => (
                    <div key={field} className={styles.fieldRow}>
                      <Space className={styles.fieldLabel}>
                        {fieldIcons[field as keyof typeof fieldIcons]}
                        <Text className={styles.fieldName}>
                          {field.charAt(0).toUpperCase() + field.slice(1)}
                        </Text>
                      </Space>
                      <Tag className={styles.fieldCount}>{count}</Tag>
                    </div>
                  )
                )}
              </div>
            </Panel>
          </Collapse>
        </div>
      ) : (
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={24} md={24} lg={12}>
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

          <Col xs={24} sm={24} md={24} lg={12}>
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
      )}

      <Divider />

      <Descriptions column={{ xs: 1, sm: 1, md: 2 }} size="small">
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
