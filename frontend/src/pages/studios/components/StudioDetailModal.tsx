import React, { useEffect } from 'react';
import { Modal, Descriptions, Tag, Button, Space, Typography } from 'antd';
import {
  HomeOutlined,
  VideoCameraOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { Studio } from '@/types/models';
import useAppStore from '@/store';

const { Title, Text, Link } = Typography;

interface StudioDetailModalProps {
  studio: Studio;
  visible: boolean;
  onClose: () => void;
  onViewScenes: (studioId: string) => void;
}

export const StudioDetailModal: React.FC<StudioDetailModalProps> = ({
  studio,
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

  if (!studio) return null;

  const formatDate = (date: string | null) => {
    if (!date) return '-';
    return dayjs(date).format('YYYY-MM-DD HH:mm:ss');
  };

  const handleOpenInStash = () => {
    const stashUrl = settings?.stash_url || '';
    if (stashUrl && studio.id) {
      // Remove trailing slash from stash_url if present
      const baseUrl = stashUrl.replace(/\/$/, '');
      const fullUrl = `${baseUrl}/studios/${studio.id}`;
      window.open(fullUrl, '_blank');
    }
  };

  // Check if we have a valid stash URL
  const hasStashUrl = Boolean(
    settings?.stash_url && settings.stash_url.trim() !== ''
  );

  return (
    <Modal
      title={
        <Space>
          <HomeOutlined />
          <span>{studio.name}</span>
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
          onClick={() => onViewScenes(studio.id)}
        >
          View Scenes ({studio.scene_count || 0})
        </Button>,
      ]}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Basic Information */}
        <div>
          <Title level={5}>Basic Information</Title>
          <Descriptions bordered column={1}>
            <Descriptions.Item label="Name">{studio.name}</Descriptions.Item>
            <Descriptions.Item label="Total Scenes">
              <Tag color="blue">{studio.scene_count || 0}</Tag>
            </Descriptions.Item>
            {studio.url && (
              <Descriptions.Item label="Website">
                <Link href={studio.url} target="_blank">
                  <LinkOutlined /> {studio.url}
                </Link>
              </Descriptions.Item>
            )}
            {studio.rating100 && (
              <Descriptions.Item label="Rating">
                {studio.rating100}/100
              </Descriptions.Item>
            )}
            <Descriptions.Item label="ID">
              <Text code>{studio.id}</Text>
            </Descriptions.Item>
          </Descriptions>
        </div>

        {/* Parent Studio */}
        {studio.parent_studio && (
          <div>
            <Title level={5}>Parent Studio</Title>
            <Tag color="purple" style={{ fontSize: 14 }}>
              {studio.parent_studio.name}
            </Tag>
          </div>
        )}

        {/* Details */}
        {studio.details && (
          <div>
            <Title level={5}>Details</Title>
            <Text style={{ whiteSpace: 'pre-wrap' }}>{studio.details}</Text>
          </div>
        )}

        {/* Metadata */}
        <div>
          <Title level={5}>Metadata</Title>
          <Descriptions bordered column={1}>
            <Descriptions.Item label="Created">
              {formatDate(studio.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Updated">
              {formatDate(studio.updated_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Last Synced">
              {studio.last_synced
                ? dayjs(studio.last_synced).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
          </Descriptions>
        </div>
      </Space>
    </Modal>
  );
};
