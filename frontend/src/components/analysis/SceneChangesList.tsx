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
  DownOutlined,
  UpOutlined,
} from '@ant-design/icons';
import { useQuery } from 'react-query';
import apiClient from '@/services/apiClient';
import { ProposedChange } from './ChangePreview';
import { Scene, Tag as TagType, Performer, Studio } from '@/types/models';
import styles from './SceneChangesList.module.scss';

const { Panel } = Collapse;
const { Text, Title } = Typography;

export interface SceneChanges {
  scene?: Scene;
  scene_id?: string;
  scene_title?: string;
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
  onPreviewScene?: (scene: Scene | { id: string; title: string }) => void;
  expandedByDefault?: boolean;
  selectable?: boolean;
  selectedSceneIds?: string[];
  onSelectionChange?: (sceneIds: string[]) => void;
  onAcceptChange?: (changeId: string) => void;
  onRejectChange?: (changeId: string) => void;
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
  onAcceptChange,
  onRejectChange,
  onEditChange: _onEditChange,
}) => {
  const [expandedKeys, setExpandedKeys] = useState<string[]>(
    expandedByDefault
      ? sceneChanges.map((sc) => sc.scene?.id || sc.scene_id || '')
      : []
  );
  const [expandedArrays, setExpandedArrays] = useState<Set<string>>(new Set());
  const [expandAll, setExpandAll] = useState(expandedByDefault);

  // Fetch all tags to map IDs to names
  const { data: tagsData } = useQuery('all-tags', () =>
    apiClient.getTags({ per_page: 1000 })
  );

  // Fetch all performers to map IDs to names
  const { data: performersData } = useQuery('all-performers', () =>
    apiClient.getPerformers({ per_page: 1000 })
  );

  // Fetch all studios to map IDs to names
  const { data: studiosData } = useQuery('all-studios', () =>
    apiClient.getStudios({ per_page: 1000 })
  );

  // Create a map of tag IDs to names
  const tagIdToName = React.useMemo(() => {
    const map = new Map<string, string>();
    if (tagsData?.items) {
      tagsData.items.forEach((tag: TagType) => {
        map.set(tag.id.toString(), tag.name);
      });
    }
    return map;
  }, [tagsData]);

  // Create a map of performer IDs to names
  const performerIdToName = React.useMemo(() => {
    const map = new Map<string, string>();
    if (performersData?.items) {
      performersData.items.forEach((performer: Performer) => {
        map.set(performer.id.toString(), performer.name);
      });
    }
    return map;
  }, [performersData]);

  // Create a map of studio IDs to names
  const studioIdToName = React.useMemo(() => {
    const map = new Map<string, string>();
    if (studiosData?.items) {
      studiosData.items.forEach((studio: Studio) => {
        map.set(studio.id.toString(), studio.name);
      });
    }
    return map;
  }, [studiosData]);

  const handleExpandAll = () => {
    if (expandAll) {
      setExpandedKeys([]);
    } else {
      setExpandedKeys(
        sceneChanges.map((sc) => sc.scene?.id || sc.scene_id || '')
      );
    }
    setExpandAll(!expandAll);
  };

  const handleSelectAll = (checked: boolean) => {
    if (onSelectionChange) {
      if (checked) {
        onSelectionChange(
          sceneChanges.map((sc) => sc.scene?.id || sc.scene_id || '')
        );
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
    const sceneId = scene?.id || sceneChange.scene_id || '';
    const sceneTitle = scene?.title || sceneChange.scene_title || 'Untitled';
    const stats = getChangeStats(sceneChange.changes);
    const status = getSceneStatus(sceneChange);
    const isSelected = selectedSceneId === sceneId;
    const isChecked = selectedSceneIds.includes(sceneId);

    return (
      <div
        className={`${styles.sceneHeader} ${isSelected ? styles.selected : ''}`}
      >
        {selectable && (
          <Checkbox
            checked={isChecked}
            onChange={(e) => handleSelectScene(sceneId, e.target.checked)}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          />
        )}

        <Avatar size="large" shape="square" className={styles.thumbnail}>
          {sceneTitle.charAt(0)}
        </Avatar>

        <div className={styles.sceneInfo}>
          <Title level={5} className={styles.sceneTitle}>
            {sceneTitle}
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
                  onPreviewScene(scene || { id: sceneId, title: sceneTitle });
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
                  onAcceptAll(sceneId);
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
                  onRejectAll(sceneId);
                }}
              />
            </Tooltip>
          )}
        </Space>
      </div>
    );
  };

  const renderValue = (
    value:
      | string
      | number
      | boolean
      | string[]
      | Record<string, unknown>
      | null
      | undefined,
    type: string,
    fieldKey: string,
    fieldName?: string
  ) => {
    if (value === null || value === undefined) {
      return 'None';
    }

    if (type === 'array' && Array.isArray(value)) {
      if (value.length === 0) return 'None';

      const isExpanded = expandedArrays.has(fieldKey);
      const displayItems = isExpanded ? value : value.slice(0, 3);

      // Map IDs to names based on field type
      let mappedItems = displayItems;
      if (fieldName === 'tags' && tagIdToName.size > 0) {
        mappedItems = displayItems.map((item) => {
          const name = tagIdToName.get(item.toString());
          return name || item; // Fall back to ID if name not found
        });
      } else if (fieldName === 'performers' && performerIdToName.size > 0) {
        mappedItems = displayItems.map((item) => {
          const name = performerIdToName.get(item.toString());
          return name || item; // Fall back to ID if name not found
        });
      }

      return (
        <div>
          <span>{mappedItems.join(', ')}</span>
          {value.length > 3 && (
            <Button
              type="link"
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                setExpandedArrays((prev) => {
                  const newSet = new Set(prev);
                  if (isExpanded) {
                    newSet.delete(fieldKey);
                  } else {
                    newSet.add(fieldKey);
                  }
                  return newSet;
                });
              }}
              style={{ padding: '0 4px', height: 'auto' }}
              icon={isExpanded ? <UpOutlined /> : <DownOutlined />}
            >
              {isExpanded ? 'Show less' : `Show ${value.length - 3} more`}
            </Button>
          )}
        </div>
      );
    }

    if (type === 'object' && typeof value === 'object') {
      const jsonStr = JSON.stringify(value);
      return (
        <Tooltip title={jsonStr} placement="top">
          <span>{jsonStr}</span>
        </Tooltip>
      );
    }

    // Handle studio field
    if (fieldName === 'studio' && studioIdToName.size > 0) {
      const studioName = studioIdToName.get(value.toString());
      if (studioName) {
        return studioName;
      }
    }

    const stringValue = String(value);
    // Add tooltip for long strings
    if (stringValue.length > 100) {
      return (
        <Tooltip title={stringValue} placement="top">
          <span>{stringValue}</span>
        </Tooltip>
      );
    }

    return stringValue;
  };

  const renderChangesList = (changes: ProposedChange[], sceneId: string) => {
    if (!changes || changes.length === 0) {
      return (
        <Empty
          description="No changes available"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      );
    }

    return (
      <List
        dataSource={changes}
        renderItem={(change: ProposedChange) => (
          <List.Item className={styles.changeItem}>
            <div className={styles.changeContent}>
              <div className={styles.changeHeader}>
                <Space align="center">
                  <Text strong>{change.fieldLabel || change.field}</Text>
                  <Tag
                    color={
                      change.confidence >= 0.8
                        ? 'green'
                        : change.confidence >= 0.6
                          ? 'orange'
                          : 'red'
                    }
                  >
                    {Math.round(change.confidence * 100)}% confidence
                  </Tag>
                  {change.accepted && <Tag color="green">Accepted</Tag>}
                  {change.rejected && <Tag color="red">Rejected</Tag>}
                  {!change.accepted && !change.rejected && (
                    <Tag color="blue">Pending</Tag>
                  )}
                  <a
                    href={`/scenes/${sceneId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    style={{ fontSize: 12 }}
                  >
                    View Scene →
                  </a>
                </Space>
              </div>
              <div className={styles.changeValues}>
                {change.action === 'add' &&
                (change.field === 'tags' || change.field === 'performers') ? (
                  <>
                    <div className={styles.valueRow}>
                      <Text type="secondary" className={styles.valueLabel}>
                        Current:
                      </Text>
                      <div className={styles.value}>
                        {renderValue(
                          change.currentValue,
                          change.type,
                          `${change.id}-current`,
                          change.field
                        )}
                      </div>
                    </div>
                    <div className={styles.arrow}>+</div>
                    <div className={styles.valueRow}>
                      <Text type="secondary" className={styles.valueLabel}>
                        Adding:
                      </Text>
                      <div
                        className={styles.value}
                        style={{ color: '#52c41a' }}
                      >
                        {renderValue(
                          change.proposedValue,
                          change.type,
                          `${change.id}-proposed`,
                          change.field
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className={styles.valueRow}>
                      <Text type="secondary" className={styles.valueLabel}>
                        Current:
                      </Text>
                      <div className={styles.value}>
                        {renderValue(
                          change.currentValue,
                          change.type,
                          `${change.id}-current`,
                          change.field
                        )}
                      </div>
                    </div>
                    <div className={styles.arrow}>→</div>
                    <div className={styles.valueRow}>
                      <Text type="secondary" className={styles.valueLabel}>
                        Proposed:
                      </Text>
                      <div className={styles.value}>
                        {renderValue(
                          change.proposedValue,
                          change.type,
                          `${change.id}-proposed`,
                          change.field
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
              {onAcceptChange &&
                onRejectChange &&
                !change.accepted &&
                !change.rejected && (
                  <Space className={styles.changeActions}>
                    <Button
                      size="small"
                      type="primary"
                      icon={<CheckCircleOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        onAcceptChange(change.id);
                      }}
                    >
                      Accept
                    </Button>
                    <Button
                      size="small"
                      danger
                      icon={<CloseCircleOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        onRejectChange(change.id);
                      }}
                    >
                      Reject
                    </Button>
                  </Space>
                )}
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
            key={sceneChange.scene?.id || sceneChange.scene_id || ''}
            header={renderSceneHeader(sceneChange)}
          >
            <Card
              size="small"
              onClick={() =>
                onSelectScene?.(
                  sceneChange.scene?.id || sceneChange.scene_id || ''
                )
              }
              className={
                selectedSceneId ===
                (sceneChange.scene?.id || sceneChange.scene_id)
                  ? styles.selectedCard
                  : ''
              }
            >
              {renderChangesList(
                sceneChange.changes,
                sceneChange.scene?.id || sceneChange.scene_id || ''
              )}
            </Card>
          </Panel>
        ))}
      </Collapse>
    </div>
  );
};
