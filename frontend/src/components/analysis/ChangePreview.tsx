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
  Modal
} from 'antd';
import { 
  CheckOutlined, 
  CloseOutlined, 
  EditOutlined,
  InfoCircleOutlined,
  DiffOutlined
} from '@ant-design/icons';
import { DiffViewer } from './DiffViewer';
import styles from './ChangePreview.module.scss';
import dayjs from 'dayjs';

const { Text, Paragraph } = Typography;

export interface ProposedChange {
  id: string;
  field: string;
  fieldLabel: string;
  currentValue: any;
  proposedValue: any;
  confidence: number;
  type: 'text' | 'array' | 'object' | 'date' | 'number';
  accepted?: boolean;
  rejected?: boolean;
  editedValue?: any;
}

export interface ChangePreviewProps {
  change: ProposedChange;
  onAccept?: () => void;
  onReject?: () => void;
  onEdit?: (value: any) => void;
  showDiff?: boolean;
  editable?: boolean;
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

  const renderValue = (value: any, type: string) => {
    if (value === null || value === undefined) {
      return <Text type="secondary">None</Text>;
    }

    switch (type) {
      case 'array':
        return (
          <Space size={4} wrap>
            {value.map((item: any, index: number) => (
              <Tag key={index}>{item}</Tag>
            ))}
          </Space>
        );
      
      case 'date':
        return dayjs(value).format('YYYY-MM-DD');
      
      case 'object':
        return <code>{JSON.stringify(value, null, 2)}</code>;
      
      default:
        return value.toString();
    }
  };

  const renderEditInput = () => {
    switch (change.type) {
      case 'text':
        return (
          <Input.TextArea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            autoSize={{ minRows: 1, maxRows: 4 }}
          />
        );
      
      case 'array':
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
            value={editValue ? dayjs(editValue) : null}
            onChange={(date) => setEditValue(date?.toISOString())}
            style={{ width: '100%' }}
          />
        );
      
      case 'number':
        return (
          <Input
            type="number"
            value={editValue}
            onChange={(e) => setEditValue(Number(e.target.value))}
          />
        );
      
      default:
        return (
          <Input.TextArea
            value={JSON.stringify(editValue, null, 2)}
            onChange={(e) => {
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
            <Tooltip title={`Confidence: ${(change.confidence * 100).toFixed(0)}%`}>
              <Tag color={getConfidenceColor(change.confidence)}>
                {getConfidenceLabel(change.confidence)} Confidence
              </Tag>
            </Tooltip>
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
                    change.editedValue !== undefined ? change.editedValue : change.proposedValue, 
                    change.type
                  )}
                  {change.editedValue !== undefined && (
                    <Tag color="blue" size="small">Edited</Tag>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className={styles.editSection}>
              <Text type="secondary">Edit value:</Text>
              {renderEditInput()}
              <Space className={styles.editActions}>
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
                onClick={onReject}
                danger
              >
                Reject
              </Button>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={onAccept}
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
          proposed={change.editedValue !== undefined ? change.editedValue : change.proposedValue}
          type={change.type}
        />
      </Modal>
    </>
  );
};