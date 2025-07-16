import React, { useState } from 'react';
import {
  List,
  Card,
  Badge,
  Tag,
  Space,
  Button,
  Collapse,
  Typography,
  Checkbox,
  Empty,
  Tooltip,
  Avatar,
} from 'antd';
import {
  ExpandOutlined,
  CompressOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { ProposedChange } from './ChangePreview';
import { Scene } from '@/types/models';
import styles from './SceneChangesList.module.scss';

const { Panel } = Collapse;
const { Text, Title } = Typography;

export interface SceneChanges {
  scene: Scene;
  changes: ProposedChange[];
  allAccepted?: boolean;
  allRejected?: boolean;
}

export interface SceneChangesListProps {
  sceneChanges: SceneChanges[];
  onSelectScene?: (sceneId: string) => void;
  selectedSceneId?: string;
  onAcceptAll?: (sceneId: string) => void;
  onRejectAll?: (sceneId: string) => void;
  onPreviewScene?: (scene: Scene) => void;
  expandedByDefault?: boolean;
  selectable?: boolean;
  selectedSceneIds?: string[];
  onSelectionChange?: (sceneIds: string[]) => void;
  onAcceptChange?: (sceneId: string, changeId: string) => void;
  onRejectChange?: (sceneId: string, changeId: string) => void;
  onEditChange?: (
    changeId: string,
    proposedValue:
      | string
      | number
      | boolean
      | string[]
      | Record<string, unknown>
      | null
  ) => Promise<void>;
}

export const SceneChangesList: React.FC<SceneChangesListProps> = ({
  sceneChanges,
  onSelectScene,
  selectedSceneId,
  onAcceptAll,
  onRejectAll,
  onPreviewScene,
  expandedByDefault = false,
  selectable = false,
  selectedSceneIds = [],
  onSelectionChange,
}) => {
  const [expandedKeys, setExpandedKeys] = useState<string[]>(
    expandedByDefault ? sceneChanges.map((sc) => sc.scene.id) : []
  );
  const [expandAll, setExpandAll] = useState(expandedByDefault);

  const handleExpandAll = () => {
    if (expandAll) {
      setExpandedKeys([]);
    } else {
      setExpandedKeys(sceneChanges.map((sc) => sc.scene.id));
    }
    setExpandAll(!expandAll);
  };

  const handleSelectAll = (checked: boolean) => {
    if (onSelectionChange) {
      if (checked) {
        onSelectionChange(sceneChanges.map((sc) => sc.scene.id));
      } else {
        onSelectionChange([]);
      }
    }
  };

  const handleSelectScene = (sceneId: string, checked: boolean) => {
    if (onSelectionChange) {
      if (checked) {
        onSelectionChange([...selectedSceneIds, sceneId]);
      } else {
        onSelectionChange(selectedSceneIds.filter((id) => id !== sceneId));
      }
    }
  };

  const getChangeStats = (changes: ProposedChange[]) => {
    const accepted = changes.filter((c) => c.accepted).length;
    const rejected = changes.filter((c) => c.rejected).length;
    const pending = changes.filter((c) => !c.accepted && !c.rejected).length;

    return { accepted, rejected, pending, total: changes.length };
  };

  const getSceneStatus = (sceneChanges: SceneChanges) => {
    const stats = getChangeStats(sceneChanges.changes);

    if (sceneChanges.allAccepted || stats.accepted === stats.total) {
      return { color: 'green', text: 'All Accepted' };
    }
    if (sceneChanges.allRejected || stats.rejected === stats.total) {
      return { color: 'red', text: 'All Rejected' };
    }
    if (stats.pending === 0) {
      return { color: 'blue', text: 'Reviewed' };
    }
    if (stats.pending === stats.total) {
      return { color: 'orange', text: 'Pending Review' };
    }
    return { color: 'purple', text: 'Partially Reviewed' };
  };

  if (sceneChanges.length === 0) {
    return (
      <Empty
        description="No scene changes to review"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  const renderSceneHeader = (sceneChange: SceneChanges) => {
    const { scene } = sceneChange;
    const stats = getChangeStats(sceneChange.changes);
    const status = getSceneStatus(sceneChange);
    const isSelected = selectedSceneId === scene.id;
    const isChecked = selectedSceneIds.includes(scene.id);

    return (
      <div
        className={`${styles.sceneHeader} ${isSelected ? styles.selected : ''}`}
      >
        {selectable && (
          <Checkbox
            checked={isChecked}
            onChange={(e) => handleSelectScene(scene.id, e.target.checked)}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          />
        )}

        <Avatar
          src={`/api/scenes/${scene.id}/thumbnail`}
          size="large"
          shape="square"
          className={styles.thumbnail}
        >
          {scene.title.charAt(0)}
        </Avatar>

        <div className={styles.sceneInfo}>
          <Title level={5} className={styles.sceneTitle}>
            {scene.title}
          </Title>
          <Space size="small">
            <Tag color={status.color}>{status.text}</Tag>
            <Text type="secondary">
              {stats.total} change{stats.total !== 1 ? 's' : ''}
            </Text>
            {stats.pending > 0 && (
              <Badge
                count={stats.pending}
                style={{ backgroundColor: '#faad14' }}
              />
            )}
          </Space>
        </div>

        <Space>
          {onPreviewScene && (
            <Tooltip title="Preview Scene">
              <Button
                type="text"
                icon={<PlayCircleOutlined />}
                onClick={(e: React.MouseEvent) => {
                  e.stopPropagation();
                  onPreviewScene(scene);
                }}
              />
            </Tooltip>
          )}
          {stats.pending > 0 && onAcceptAll && (
            <Tooltip title="Accept All">
              <Button
                type="text"
                icon={<CheckCircleOutlined />}
                onClick={(e: React.MouseEvent) => {
                  e.stopPropagation();
                  onAcceptAll(scene.id);
                }}
              />
            </Tooltip>
          )}
          {stats.pending > 0 && onRejectAll && (
            <Tooltip title="Reject All">
              <Button
                type="text"
                danger
                icon={<CloseCircleOutlined />}
                onClick={(e: React.MouseEvent) => {
                  e.stopPropagation();
                  onRejectAll(scene.id);
                }}
              />
            </Tooltip>
          )}
        </Space>
      </div>
    );
  };

  const renderChangesList = (changes: ProposedChange[]) => {
    return (
      <List
        dataSource={changes}
        renderItem={(change: ProposedChange) => (
          <List.Item className={styles.changeItem}>
            <div className={styles.changeContent}>
              <Space>
                <Text strong>{change.fieldLabel}</Text>
                {change.accepted && <Tag color="green">Accepted</Tag>}
                {change.rejected && <Tag color="red">Rejected</Tag>}
                {!change.accepted && !change.rejected && (
                  <Tag color="orange">Pending</Tag>
                )}
              </Space>
              <div className={styles.changeValues}>
                <Text type="secondary">
                  {JSON.stringify(change.currentValue)} →{' '}
                  {JSON.stringify(change.proposedValue)}
                </Text>
              </div>
            </div>
          </List.Item>
        )}
      />
    );
  };

  return (
    <div className={styles.sceneChangesList}>
      <div className={styles.toolbar}>
        {selectable && (
          <Checkbox
            onChange={(e) => handleSelectAll(e.target.checked)}
            checked={
              selectedSceneIds.length === sceneChanges.length &&
              sceneChanges.length > 0
            }
            indeterminate={
              selectedSceneIds.length > 0 &&
              selectedSceneIds.length < sceneChanges.length
            }
          >
            Select All
          </Checkbox>
        )}
        <Button
          type="text"
          icon={expandAll ? <CompressOutlined /> : <ExpandOutlined />}
          onClick={handleExpandAll}
        >
          {expandAll ? 'Collapse All' : 'Expand All'}
        </Button>
      </div>

      <Collapse
        activeKey={expandedKeys}
        onChange={(keys: string | string[]) =>
          setExpandedKeys(Array.isArray(keys) ? keys : [keys])
        }
      >
        {sceneChanges.map((sceneChange) => (
          <Panel
            key={sceneChange.scene.id}
            header={renderSceneHeader(sceneChange)}
          >
            <Card
              size="small"
              onClick={() => onSelectScene?.(sceneChange.scene.id)}
              className={
                selectedSceneId === sceneChange.scene.id
                  ? styles.selectedCard
                  : ''
              }
            >
              {renderChangesList(sceneChange.changes)}
            </Card>
          </Panel>
        ))}
      </Collapse>
    </div>
  );
};
