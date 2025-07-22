import React, { useState } from 'react';
import {
  Card,
  Tag,
  Button,
  Space,
  Tooltip,
  Progress,
  Typography,
  Input,
  Select,
  DatePicker,
  Modal,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  EditOutlined,
  DiffOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useQuery } from 'react-query';
import apiClient from '@/services/apiClient';
import { Tag as TagType, Performer, Studio } from '@/types/models';
import { DiffViewer } from './DiffViewer';
import styles from './ChangePreview.module.scss';
import dayjs from 'dayjs';

const { Text, Link } = Typography;

export interface ProposedChange {
  id: string;
  sceneId?: string | number;
  field: string;
  fieldLabel: string;
  action?: 'set' | 'add' | 'update';
  currentValue:
    | string
    | number
    | boolean
    | string[]
    | Record<string, unknown>
    | null;
  proposedValue:
    | string
    | number
    | boolean
    | string[]
    | Record<string, unknown>
    | null;
  confidence: number;
  type: 'text' | 'array' | 'object' | 'date' | 'number';
  accepted?: boolean;
  rejected?: boolean;
  applied?: boolean;
  editedValue?:
    | string
    | number
    | boolean
    | string[]
    | Record<string, unknown>
    | null;
}

export interface ChangePreviewProps {
  change: ProposedChange;
  onAccept?: () => void | Promise<void>;
  onReject?: () => void | Promise<void>;
  onEdit?: (
    value: string | number | boolean | string[] | Record<string, unknown> | null
  ) => void;
  showDiff?: boolean;
  editable?: boolean;
  compact?: boolean;
}

export const ChangePreview: React.FC<ChangePreviewProps> = ({
  change,
  onAccept,
  onReject,
  onEdit,
  showDiff = true,
  editable = true,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(change.proposedValue);
  const [showDiffModal, setShowDiffModal] = useState(false);

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

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'green';
    if (confidence >= 0.6) return 'orange';
    return 'red';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
  };

  const handleSaveEdit = () => {
    onEdit?.(editValue);
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditValue(change.proposedValue);
    setIsEditing(false);
  };

  const renderValue = (
    value:
      | string
      | number
      | boolean
      | string[]
      | Record<string, unknown>
      | null,
    type: string
  ) => {
    if (value === null || value === undefined) {
      return <Text type="secondary">None</Text>;
    }

    switch (type) {
      case 'array':
        return (
          <Space size={4} wrap>
            {(value as string[]).map((item: string, index: number) => {
              // Map IDs to names based on field type
              let displayValue = item;
              if (change.field === 'tags' && tagIdToName.size > 0) {
                displayValue = tagIdToName.get(item.toString()) || item;
              } else if (
                change.field === 'performers' &&
                performerIdToName.size > 0
              ) {
                displayValue = performerIdToName.get(item.toString()) || item;
              }
              return <Tag key={index}>{displayValue}</Tag>;
            })}
          </Space>
        );

      case 'date':
        return dayjs(value as string | number).format('YYYY-MM-DD');

      case 'object':
        return <code>{JSON.stringify(value, null, 2)}</code>;

      default:
        // Handle studio field
        if (change.field === 'studio' && studioIdToName.size > 0 && value) {
          const studioName = studioIdToName.get(value.toString());
          if (studioName) {
            return studioName;
          }
        }
        return value.toString();
    }
  };

  const renderEditInput = () => {
    switch (change.type) {
      case 'text':
        // Handle studio field with select dropdown
        if (change.field === 'studio' && studioIdToName.size > 0) {
          const studioOptions = Array.from(studioIdToName.entries()).map(
            ([id, name]) => ({
              value: id,
              label: name,
            })
          );
          return (
            <Select
              value={editValue}
              onChange={setEditValue}
              style={{ width: '100%' }}
              options={studioOptions}
              showSearch
              filterOption={(input, option) =>
                String(option?.label ?? '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            />
          );
        }
        return (
          <Input.TextArea
            value={editValue as string | number | readonly string[] | undefined}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
              setEditValue(e.target.value)
            }
            autoSize={{ minRows: 1, maxRows: 4 }}
          />
        );

      case 'array':
        // Create options based on field type
        if (change.field === 'tags' && tagIdToName.size > 0) {
          const tagOptions = Array.from(tagIdToName.entries()).map(
            ([id, name]) => ({
              value: id,
              label: name,
            })
          );
          return (
            <Select
              mode="multiple"
              value={editValue}
              onChange={setEditValue}
              style={{ width: '100%' }}
              options={tagOptions}
              showSearch
              filterOption={(input, option) =>
                String(option?.label ?? '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            />
          );
        } else if (
          change.field === 'performers' &&
          performerIdToName.size > 0
        ) {
          const performerOptions = Array.from(performerIdToName.entries()).map(
            ([id, name]) => ({
              value: id,
              label: name,
            })
          );
          return (
            <Select
              mode="multiple"
              value={editValue}
              onChange={setEditValue}
              style={{ width: '100%' }}
              options={performerOptions}
              showSearch
              filterOption={(input, option) =>
                String(option?.label ?? '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            />
          );
        }
        // For other array fields, use the default tags mode
        return (
          <Select
            mode="tags"
            value={editValue}
            onChange={setEditValue}
            style={{ width: '100%' }}
          />
        );

      case 'date':
        return (
          <DatePicker
            value={editValue ? dayjs(editValue as string | number) : null}
            onChange={(date: any) => setEditValue(date?.toISOString())} // eslint-disable-line @typescript-eslint/no-explicit-any
            style={{ width: '100%' }}
          />
        );

      case 'number':
        return (
          <Input
            type="number"
            value={editValue as string | undefined}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setEditValue(Number(e.target.value))
            }
          />
        );

      default:
        return (
          <Input.TextArea
            value={JSON.stringify(editValue, null, 2)}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => {
              try {
                setEditValue(JSON.parse(e.target.value));
              } catch {
                // Keep the string value if JSON parse fails
              }
            }}
            autoSize={{ minRows: 2, maxRows: 6 }}
          />
        );
    }
  };

  const statusTag = change.accepted ? (
    <Tag color="green">Accepted</Tag>
  ) : change.rejected ? (
    <Tag color="red">Rejected</Tag>
  ) : null;

  return (
    <>
      <Card className={styles.changePreview}>
        <div className={styles.header}>
          <div className={styles.fieldInfo}>
            <Text strong>{change.fieldLabel}</Text>
            {statusTag}
            <Tooltip
              title={`Confidence: ${(change.confidence * 100).toFixed(0)}%`}
            >
              <Tag color={getConfidenceColor(change.confidence)}>
                {getConfidenceLabel(change.confidence)} Confidence
              </Tag>
            </Tooltip>
            {change.sceneId && (
              <Link
                href={`/scenes/${change.sceneId}`}
                target="_blank"
                style={{ marginLeft: 8 }}
              >
                <LinkOutlined /> View Scene
              </Link>
            )}
          </div>

          <Space>
            {showDiff && (
              <Tooltip title="View Diff">
                <Button
                  type="text"
                  icon={<DiffOutlined />}
                  onClick={() => setShowDiffModal(true)}
                />
              </Tooltip>
            )}
            {editable && !change.accepted && !change.rejected && (
              <Tooltip title="Edit">
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  onClick={() => setIsEditing(!isEditing)}
                />
              </Tooltip>
            )}
          </Space>
        </div>

        <div className={styles.content}>
          {!isEditing ? (
            <div className={styles.values}>
              <div className={styles.valueSection}>
                <Text type="secondary">Current:</Text>
                <div className={styles.value}>
                  {renderValue(change.currentValue, change.type)}
                </div>
              </div>

              <div className={styles.arrow}>→</div>

              <div className={styles.valueSection}>
                <Text type="secondary">Proposed:</Text>
                <div className={styles.value}>
                  {renderValue(
                    change.editedValue !== undefined
                      ? change.editedValue
                      : change.proposedValue,
                    change.type
                  )}
                  {change.editedValue !== undefined && (
                    <Tag color="blue">Edited</Tag>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className={styles.editSection}>
              <Text type="secondary">Edit value:</Text>
              {renderEditInput()}
              <Space>
                <Button size="small" onClick={handleCancelEdit}>
                  Cancel
                </Button>
                <Button size="small" type="primary" onClick={handleSaveEdit}>
                  Save
                </Button>
              </Space>
            </div>
          )}
        </div>

        {!change.accepted && !change.rejected && (
          <div className={styles.actions}>
            <Progress
              percent={change.confidence * 100}
              showInfo={false}
              strokeColor={getConfidenceColor(change.confidence)}
              className={styles.confidenceBar}
            />
            <Space>
              <Button
                icon={<CloseOutlined />}
                onClick={() => void onReject?.()}
                danger
              >
                Reject
              </Button>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={() => void onAccept?.()}
              >
                Accept
              </Button>
            </Space>
          </div>
        )}
      </Card>

      <Modal
        title={`Diff: ${change.fieldLabel}`}
        open={showDiffModal}
        onCancel={() => setShowDiffModal(false)}
        footer={null}
        width={800}
      >
        <DiffViewer
          current={change.currentValue}
          proposed={
            change.editedValue !== undefined
              ? change.editedValue
              : change.proposedValue
          }
          type={
            change.type === 'number' || change.type === 'date'
              ? 'text'
              : change.type
          }
        />
      </Modal>
    </>
  );
};
