import React, { useEffect } from 'react';
import { Modal, Descriptions, Tag, Button, Space, Typography } from 'antd';
import {
  UserOutlined,
  VideoCameraOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { Performer } from '@/types/models';
import useAppStore from '@/store';

const { Title, Text, Link } = Typography;

interface PerformerDetailModalProps {
  performer: Performer;
  visible: boolean;
  onClose: () => void;
  onViewScenes: (performerId: string) => void;
}

export const PerformerDetailModal: React.FC<PerformerDetailModalProps> = ({
  performer,
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

  if (!performer) return null;

  const formatDate = (date: string | null) => {
    if (!date) return '-';
    return dayjs(date).format('YYYY-MM-DD HH:mm:ss');
  };

  const handleOpenInStash = () => {
    const stashUrl = settings?.stash_url || '';
    if (stashUrl && performer.id) {
      // Remove trailing slash from stash_url if present
      const baseUrl = stashUrl.replace(/\/$/, '');
      const fullUrl = `${baseUrl}/performers/${performer.id}`;
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
          <UserOutlined />
          <span>{performer.name}</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
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
          onClick={() => onViewScenes(performer.id)}
        >
          View Scenes ({performer.scene_count || 0})
        </Button>,
      ]}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Basic Information */}
        <div>
          <Title level={5}>Basic Information</Title>
          <Descriptions bordered column={2}>
            <Descriptions.Item label="Name">{performer.name}</Descriptions.Item>
            <Descriptions.Item label="Gender">
              {performer.gender || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Birthdate">
              {formatDate(performer.birthdate ?? null)}
            </Descriptions.Item>
            <Descriptions.Item label="Country">
              {performer.country || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Ethnicity">
              {performer.ethnicity || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Hair Color">
              {performer.hair_color || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Eye Color">
              {performer.eye_color || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Height">
              {performer.height ? `${performer.height} cm` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Weight">
              {performer.weight ? `${performer.weight} kg` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Measurements">
              {performer.measurements || '-'}
            </Descriptions.Item>
          </Descriptions>
        </div>

        {/* Additional Details */}
        <div>
          <Title level={5}>Additional Details</Title>
          <Descriptions bordered column={2}>
            <Descriptions.Item label="Tattoos">
              {performer.tattoos || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Piercings">
              {performer.piercings || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Fake Tits">
              {performer.fake_tits || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Aliases" span={2}>
              {performer.aliases || '-'}
            </Descriptions.Item>
          </Descriptions>
        </div>

        {/* Links */}
        {(performer.url || performer.twitter || performer.instagram) && (
          <div>
            <Title level={5}>Links</Title>
            <Space direction="vertical">
              {performer.url && (
                <Link href={performer.url} target="_blank">
                  <LinkOutlined /> Website
                </Link>
              )}
              {performer.twitter && (
                <Link
                  href={`https://twitter.com/${performer.twitter}`}
                  target="_blank"
                >
                  <LinkOutlined /> Twitter: @{performer.twitter}
                </Link>
              )}
              {performer.instagram && (
                <Link
                  href={`https://instagram.com/${performer.instagram}`}
                  target="_blank"
                >
                  <LinkOutlined /> Instagram: @{performer.instagram}
                </Link>
              )}
            </Space>
          </div>
        )}

        {/* Details/Bio */}
        {performer.details && (
          <div>
            <Title level={5}>Biography</Title>
            <Text style={{ whiteSpace: 'pre-wrap' }}>{performer.details}</Text>
          </div>
        )}

        {/* Metadata */}
        <div>
          <Title level={5}>Metadata</Title>
          <Descriptions bordered column={2}>
            <Descriptions.Item label="Total Scenes">
              <Tag color="blue">{performer.scene_count || 0}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Favorite">
              {performer.favorite ? '⭐ Yes' : 'No'}
            </Descriptions.Item>
            <Descriptions.Item label="Rating">
              {performer.rating100 ? `${performer.rating100}/100` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="ID">
              <Text code>{performer.id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Created">
              {formatDate(performer.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Updated">
              {formatDate(performer.updated_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Last Synced">
              {performer.last_synced
                ? dayjs(performer.last_synced).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
          </Descriptions>
        </div>
      </Space>
    </Modal>
  );
};
