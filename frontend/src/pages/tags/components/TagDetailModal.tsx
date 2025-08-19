import React, { useEffect } from 'react';
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
  LinkOutlined,
  ApiOutlined,
  BugOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { Tag as TagModel } from '@/types/models';
import useAppStore from '@/store';

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
  const { settings, loadSettings, isLoaded } = useAppStore();

  // Load settings if not already loaded
  useEffect(() => {
    if (!isLoaded) {
      void loadSettings();
    }
  }, [isLoaded, loadSettings]);

  if (!tag) return null;

  const formatDate = (date: string | null) => {
    if (!date) return '-';
    return dayjs(date).format('YYYY-MM-DD HH:mm:ss');
  };

  const handleOpenInStash = () => {
    const stashUrl = settings?.stash_url || '';
    if (stashUrl && tag.id) {
      // Remove trailing slash from stash_url if present
      const baseUrl = stashUrl.replace(/\/$/, '');
      const fullUrl = `${baseUrl}/tags/${tag.id}`;
      window.open(fullUrl, '_blank');
    }
  };

  const handleOpenInAPI = () => {
    // Get current origin for the API base URL
    const apiUrl = `${window.location.origin}/api/entities/tags/${tag.id}`;
    window.open(apiUrl, '_blank');
  };

  const handleDebugStashAPI = () => {
    // Open the debug endpoint for Stash GraphQL data
    const debugUrl = `${window.location.origin}/api/debug/stashtag/${tag.id}`;
    window.open(debugUrl, '_blank');
  };

  // Check if we have a valid stash URL
  const hasStashUrl = Boolean(
    settings?.stash_url && settings.stash_url.trim() !== ''
  );

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
        <Button key="open-api" icon={<ApiOutlined />} onClick={handleOpenInAPI}>
          Open in API
        </Button>,
        <Button
          key="debug-api"
          icon={<BugOutlined />}
          onClick={handleDebugStashAPI}
        >
          Debug Stash API
        </Button>,
        <Button
          key="open-stash"
          icon={<LinkOutlined />}
          onClick={handleOpenInStash}
          disabled={!hasStashUrl}
        >
          Open in Stash
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
            <Descriptions.Item label="Last Synced">
              {tag.last_synced
                ? dayjs(tag.last_synced).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
          </Descriptions>
        </div>
      </Space>
    </Modal>
  );
};
