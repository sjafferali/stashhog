import React from 'react';
import {
  Modal,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  List,
} from 'antd';
import {
  TagOutlined,
  VideoCameraOutlined,
  BranchesOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { Tag as TagModel } from '@/types/models';

const { Title, Text } = Typography;

interface TagDetailModalProps {
  tag: TagModel;
  visible: boolean;
  onClose: () => void;
  onViewScenes: (tagId: string) => void;
}

export const TagDetailModal: React.FC<TagDetailModalProps> = ({
  tag,
  visible,
  onClose,
  onViewScenes,
}) => {
  if (!tag) return null;

  const formatDate = (date: string | null) => {
    if (!date) return '-';
    return dayjs(date).format('YYYY-MM-DD HH:mm');
  };

  return (
    <Modal
      title={
        <Space>
          <TagOutlined />
          <span>{tag.name}</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={700}
      footer={[
        <Button key="close" onClick={onClose}>
          Close
        </Button>,
        <Button
          key="scenes"
          type="primary"
          icon={<VideoCameraOutlined />}
          onClick={() => onViewScenes(tag.id)}
        >
          View Scenes ({tag.scene_count || 0})
        </Button>,
      ]}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Basic Information */}
        <div>
          <Title level={5}>Basic Information</Title>
          <Descriptions bordered column={1}>
            <Descriptions.Item label="Name">
              <Tag color="green" style={{ fontSize: 14 }}>
                {tag.name}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Total Scenes">
              <Tag color="blue">{tag.scene_count || 0}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Total Markers">
              <Tag color="purple">{tag.marker_count || 0}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="ID">
              <Text code>{tag.id}</Text>
            </Descriptions.Item>
          </Descriptions>
        </div>

        {/* Aliases */}
        {tag.aliases && tag.aliases.length > 0 && (
          <div>
            <Title level={5}>Aliases</Title>
            <Space wrap>
              {tag.aliases.map((alias: string, index: number) => (
                <Tag key={index} color="orange">
                  {alias}
                </Tag>
              ))}
            </Space>
          </div>
        )}

        {/* Parent Tags */}
        {tag.parent_tags && tag.parent_tags.length > 0 && (
          <div>
            <Title level={5}>
              <BranchesOutlined /> Parent Tags
            </Title>
            <List
              size="small"
              dataSource={tag.parent_tags}
              renderItem={(parentTag: TagModel) => (
                <List.Item>
                  <Tag color="purple">{parentTag.name}</Tag>
                </List.Item>
              )}
            />
          </div>
        )}

        {/* Child Tags */}
        {tag.child_tags && tag.child_tags.length > 0 && (
          <div>
            <Title level={5}>
              <BranchesOutlined /> Child Tags
            </Title>
            <List
              size="small"
              dataSource={tag.child_tags}
              renderItem={(childTag: TagModel) => (
                <List.Item>
                  <Tag color="cyan">{childTag.name}</Tag>
                </List.Item>
              )}
            />
          </div>
        )}

        {/* Metadata */}
        <div>
          <Title level={5}>Metadata</Title>
          <Descriptions bordered column={1}>
            <Descriptions.Item label="Created">
              {formatDate(tag.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Updated">
              {formatDate(tag.updated_at)}
            </Descriptions.Item>
          </Descriptions>
        </div>
      </Space>
    </Modal>
  );
};
