import React, { useState } from 'react';
import {
  Card,
  Collapse,
  Space,
  Button,
  Tag,
  Badge,
  Tooltip,
  Image,
  Typography,
  Divider,
  Progress,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  ExpandOutlined,
  CompressOutlined,
} from '@ant-design/icons';
import { ChangePreview } from '@/components/analysis';
import type { Scene } from '@/types/models';
import type { ProposedChange } from '@/components/analysis';
import './SceneChanges.scss';

const { Panel } = Collapse;
const { Text } = Typography;

export interface SceneChangesProps {
  scene: Scene;
  changes: ProposedChange[];
  expanded?: boolean;
  onAcceptAll?: () => void;
  onRejectAll?: () => void;
  onPreview?: () => void;
  onAcceptChange?: (changeId: string) => void;
  onRejectChange?: (changeId: string) => void;
  onEditChange?: (
    changeId: string,
    value: string | number | boolean | string[] | Record<string, unknown> | null
  ) => void;
  showActions?: boolean;
}

const SceneChanges: React.FC<SceneChangesProps> = ({
  scene,
  changes,
  expanded = false,
  onAcceptAll,
  onRejectAll,
  onPreview,
  onAcceptChange,
  onRejectChange,
  onEditChange,
  showActions = true,
}) => {
  const [isExpanded, setIsExpanded] = useState(expanded);
  const [showAllChanges, setShowAllChanges] = useState(false);

  // Calculate statistics
  const acceptedCount = changes.filter((c) => c.accepted).length;
  const rejectedCount = changes.filter((c) => c.rejected).length;
  const pendingCount = changes.length - acceptedCount - rejectedCount;
  const acceptanceRate =
    changes.length > 0 ? (acceptedCount / changes.length) * 100 : 0;

  // Group changes by field
  const changesByField = changes.reduce(
    (acc, change) => {
      if (!acc[change.field]) acc[change.field] = [];
      acc[change.field].push(change);
      return acc;
    },
    {} as Record<string, ProposedChange[]>
  );

  // Determine status
  const getStatus = () => {
    if (pendingCount === 0 && acceptedCount === changes.length)
      return 'accepted';
    if (pendingCount === 0 && rejectedCount === changes.length)
      return 'rejected';
    if (pendingCount === 0) return 'reviewed';
    return 'pending';
  };

  const status = getStatus();

  const statusColors = {
    accepted: '#52c41a',
    rejected: '#f5222d',
    reviewed: '#1890ff',
    pending: '#faad14',
  };

  const statusLabels = {
    accepted: 'All Accepted',
    rejected: 'All Rejected',
    reviewed: 'Reviewed',
    pending: `${pendingCount} Pending`,
  };

  // Limit changes shown when collapsed
  const displayedChanges = showAllChanges ? changes : changes.slice(0, 3);
  const hasMoreChanges = changes.length > 3;

  return (
    <Card
      className="scene-changes-card"
      size="small"
      title={
        <div className="scene-header">
          <Space>
            {scene.path && (
              <Image
                src={scene.path}
                alt={scene.title}
                width={60}
                height={40}
                style={{ objectFit: 'cover', borderRadius: 4 }}
                preview={false}
              />
            )}
            <div>
              <Text strong>{scene.title || 'Untitled Scene'}</Text>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {scene.stash_date} • {scene.duration}
                </Text>
              </div>
            </div>
          </Space>

          <Space>
            <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
            <Badge count={pendingCount} showZero={false} />
          </Space>
        </div>
      }
      extra={
        showActions && (
          <Space>
            {onPreview && (
              <Tooltip title="Preview Scene">
                <Button
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={onPreview}
                />
              </Tooltip>
            )}
            <Button
              size="small"
              icon={isExpanded ? <CompressOutlined /> : <ExpandOutlined />}
              onClick={() => setIsExpanded(!isExpanded)}
            />
          </Space>
        )
      }
    >
      {/* Quick stats */}
      <div className="scene-stats">
        <Space>
          <Text type="secondary">
            <CheckCircleOutlined style={{ color: '#52c41a' }} /> {acceptedCount}
          </Text>
          <Divider type="vertical" />
          <Text type="secondary">
            <CloseCircleOutlined style={{ color: '#f5222d' }} /> {rejectedCount}
          </Text>
          <Divider type="vertical" />
          <Text type="secondary">
            Confidence:{' '}
            {Math.round(
              (changes.reduce((sum, c) => sum + c.confidence, 0) /
                changes.length) *
                100
            )}
            %
          </Text>
        </Space>

        {acceptanceRate > 0 && (
          <Progress
            percent={acceptanceRate}
            size="small"
            showInfo={false}
            strokeColor="#52c41a"
            style={{ width: 100 }}
          />
        )}
      </div>

      <Divider style={{ margin: '12px 0' }} />

      {/* Changes list */}
      <div className={`changes-list ${isExpanded ? 'expanded' : 'collapsed'}`}>
        {isExpanded ? (
          // Expanded view - group by field
          <Collapse defaultActiveKey={Object.keys(changesByField)}>
            {Object.entries(changesByField).map(([field, fieldChanges]) => (
              <Panel
                key={field}
                header={
                  <Space>
                    <Text strong>
                      {field.charAt(0).toUpperCase() + field.slice(1)}
                    </Text>
                    <Badge
                      count={fieldChanges.filter((c) => c.accepted).length}
                      style={{ backgroundColor: '#52c41a' }}
                    />
                    <Badge
                      count={fieldChanges.filter((c) => c.rejected).length}
                      style={{ backgroundColor: '#f5222d' }}
                    />
                  </Space>
                }
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  {fieldChanges.map((change) => (
                    <ChangePreview
                      key={change.id}
                      change={change}
                      onAccept={() => onAcceptChange?.(change.id)}
                      onReject={() => onRejectChange?.(change.id)}
                      onEdit={(value) => onEditChange?.(change.id, value)}
                      showDiff
                      editable
                    />
                  ))}
                </Space>
              </Panel>
            ))}
          </Collapse>
        ) : (
          // Collapsed view - simple list
          <Space direction="vertical" style={{ width: '100%' }}>
            {displayedChanges.map((change) => (
              <ChangePreview
                key={change.id}
                change={change}
                onAccept={() => onAcceptChange?.(change.id)}
                onReject={() => onRejectChange?.(change.id)}
                onEdit={(value) => onEditChange?.(change.id, value)}
                compact
              />
            ))}

            {hasMoreChanges && !showAllChanges && (
              <Button
                type="link"
                size="small"
                onClick={() => setShowAllChanges(true)}
              >
                Show {changes.length - 3} more changes...
              </Button>
            )}
          </Space>
        )}
      </div>

      {/* Actions */}
      {showActions && pendingCount > 0 && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <Space>
            <Button
              size="small"
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={onAcceptAll}
            >
              Accept All
            </Button>
            <Button
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={onRejectAll}
            >
              Reject All
            </Button>
          </Space>
        </>
      )}
    </Card>
  );
};

export default SceneChanges;
