import React, { useMemo, useCallback } from 'react';
import {
  Card,
  Col,
  Row,
  Image,
  Tag,
  Space,
  Checkbox,
  Typography,
  Tooltip,
} from 'antd';
import {
  // ClockCircleOutlined,
  FolderOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { Scene } from '@/types/models';
import { useScenesStore, GridSize } from '@/store/slices/scenes';
import styles from './GridView.module.scss';

const { Text } = Typography;

interface GridViewProps {
  scenes: Scene[];
  onSceneSelect: (scene: Scene) => void;
}

const GRID_COLS: Record<GridSize, number> = {
  small: 6,
  medium: 4,
  large: 3,
};

const formatDuration = (seconds?: number): string => {
  if (!seconds) return 'N/A';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
};

const formatFileSize = (bytes?: string): string => {
  if (!bytes) return 'N/A';
  const size = parseInt(bytes, 10);
  if (isNaN(size)) return 'N/A';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let unitIndex = 0;
  let formattedSize = size;

  while (formattedSize >= 1024 && unitIndex < units.length - 1) {
    formattedSize /= 1024;
    unitIndex++;
  }

  return `${formattedSize.toFixed(1)} ${units[unitIndex]}`;
};

export const GridView: React.FC<GridViewProps> = ({
  scenes,
  onSceneSelect,
}) => {
  const { gridSize, selectedScenes, toggleSceneSelection } = useScenesStore();
  const colSpan = GRID_COLS[gridSize];

  const handleCardClick = useCallback(
    (scene: Scene, e: React.MouseEvent) => {
      // Don't open modal if clicking on checkbox
      if ((e.target as HTMLElement).closest('.ant-checkbox-wrapper')) {
        return;
      }
      onSceneSelect(scene);
    },
    [onSceneSelect]
  );

  const handleCheckboxClick = useCallback(
    (sceneId: string, e: React.MouseEvent) => {
      e.stopPropagation();
      toggleSceneSelection(sceneId);
    },
    [toggleSceneSelection]
  );

  const sceneCards = useMemo(
    () =>
      scenes.map((scene) => {
        const isSelected = selectedScenes.has(scene.id.toString());
        const thumbnailUrl = `/api/scenes/${scene.id}/thumbnail`; // Adjust based on your API

        return (
          <Col key={scene.id} span={colSpan}>
            <Card
              hoverable
              className={`${styles.sceneCard} ${isSelected ? styles.selected : ''}`}
              onClick={(e: React.MouseEvent) => handleCardClick(scene, e)}
              cover={
                <div className={styles.coverWrapper}>
                  <Image
                    alt={scene.title || 'Scene thumbnail'}
                    src={thumbnailUrl}
                    fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
                    preview={false}
                    className={styles.thumbnail}
                  />
                  {scene.duration && (
                    <div className={styles.duration}>
                      {formatDuration(scene.duration)}
                    </div>
                  )}
                  <Checkbox
                    checked={isSelected}
                    onClick={(e) => handleCheckboxClick(scene.id.toString(), e)}
                    className={styles.checkbox}
                  />
                </div>
              }
            >
              <Card.Meta
                title={
                  <Tooltip title={scene.title || scene.path}>
                    <Text ellipsis>{scene.title || 'Untitled'}</Text>
                  </Tooltip>
                }
                description={
                  <Space
                    direction="vertical"
                    size="small"
                    style={{ width: '100%' }}
                  >
                    {scene.studio && (
                      <Tag color="blue">{scene.studio.name}</Tag>
                    )}

                    <Space size="small" wrap>
                      {scene.performers && scene.performers.length > 0 && (
                        <Tooltip
                          title={scene.performers.map((p) => p.name).join(', ')}
                        >
                          <Tag color="pink">
                            {scene.performers.length} performer
                            {scene.performers.length > 1 ? 's' : ''}
                          </Tag>
                        </Tooltip>
                      )}

                      {scene.tags && scene.tags.length > 0 && (
                        <Tooltip
                          title={scene.tags.map((t) => t.name).join(', ')}
                        >
                          <Tag color="green">
                            {scene.tags.length} tag
                            {scene.tags.length > 1 ? 's' : ''}
                          </Tag>
                        </Tooltip>
                      )}
                    </Space>

                    <Space size="small" className={styles.metadata}>
                      {scene.organized && (
                        <Tooltip title="Organized">
                          <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        </Tooltip>
                      )}

                      {scene.date && (
                        <Tooltip title={`Scene date: ${scene.date}`}>
                          <CalendarOutlined />
                        </Tooltip>
                      )}

                      {scene.size && (
                        <Tooltip
                          title={`File size: ${formatFileSize(scene.size)}`}
                        >
                          <FolderOutlined />
                        </Tooltip>
                      )}

                      {scene.details && (
                        <Tooltip title="Has details">
                          <InfoCircleOutlined style={{ color: '#1890ff' }} />
                        </Tooltip>
                      )}
                    </Space>
                  </Space>
                }
              />
            </Card>
          </Col>
        );
      }),
    [scenes, colSpan, selectedScenes, handleCardClick, handleCheckboxClick]
  );

  return <Row gutter={[16, 16]}>{sceneCards}</Row>;
};
