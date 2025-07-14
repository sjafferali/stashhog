import React from 'react';
import { Card, Tag, Space, Tooltip, Badge, Dropdown, Button } from 'antd';
import type { MenuProps } from 'antd';
import { 
  PlayCircleOutlined, 
  CalendarOutlined, 
  ClockCircleOutlined,
  EyeOutlined,
  EditOutlined,
  AnalysisOutlined,
  MoreOutlined,
  StarFilled
} from '@ant-design/icons';
import { Scene } from '@/types/models';
import styles from './SceneCard.module.scss';

export interface SceneAction {
  key: string;
  label: string;
  icon?: React.ReactNode;
  onClick: (scene: Scene) => void;
  danger?: boolean;
}

export interface SceneCardProps {
  scene: Scene;
  onClick?: (scene: Scene) => void;
  actions?: SceneAction[];
  showDetails?: boolean;
}

export const SceneCard: React.FC<SceneCardProps> = ({
  scene,
  onClick,
  actions = [],
  showDetails = true,
}) => {
  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes?: string) => {
    if (!bytes) return 'N/A';
    const size = parseInt(bytes, 10);
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let unitIndex = 0;
    let value = size;
    
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex++;
    }
    
    return `${value.toFixed(1)} ${units[unitIndex]}`;
  };

  const menuItems: MenuProps['items'] = actions.map(action => ({
    key: action.key,
    label: action.label,
    icon: action.icon,
    danger: action.danger,
    onClick: () => action.onClick(scene),
  }));

  const cardActions = [
    <Tooltip key="view" title="View Details">
      <Button
        type="text"
        icon={<EyeOutlined />}
        onClick={() => onClick?.(scene)}
      />
    </Tooltip>,
    <Tooltip key="edit" title="Edit">
      <Button
        type="text"
        icon={<EditOutlined />}
        onClick={() => actions.find(a => a.key === 'edit')?.onClick(scene)}
      />
    </Tooltip>,
    <Tooltip key="analyze" title="Analyze">
      <Button
        type="text"
        icon={<AnalysisOutlined />}
        onClick={() => actions.find(a => a.key === 'analyze')?.onClick(scene)}
      />
    </Tooltip>,
  ];

  if (menuItems.length > 0) {
    cardActions.push(
      <Dropdown key="more" menu={{ items: menuItems }} trigger={['click']}>
        <Button type="text" icon={<MoreOutlined />} />
      </Dropdown>
    );
  }

  return (
    <Badge.Ribbon 
      text={scene.analyzed_at ? 'Analyzed' : 'Not Analyzed'}
      color={scene.analyzed_at ? 'green' : 'gray'}
    >
      <Card
        className={styles.sceneCard}
        hoverable
        onClick={() => onClick?.(scene)}
        cover={
          <div className={styles.thumbnail}>
            <img 
              alt={scene.title} 
              src={`/api/scenes/${scene.id}/thumbnail`}
              onError={(e) => {
                (e.target as HTMLImageElement).src = '/placeholder-scene.png';
              }}
            />
            <div className={styles.duration}>
              <ClockCircleOutlined /> {formatDuration(scene.duration)}
            </div>
            {scene.rating && (
              <div className={styles.rating}>
                <StarFilled /> {scene.rating}
              </div>
            )}
          </div>
        }
        actions={showDetails ? cardActions : undefined}
      >
        <Card.Meta
          title={
            <Tooltip title={scene.title}>
              <div className={styles.title}>{scene.title}</div>
            </Tooltip>
          }
          description={
            <div className={styles.metadata}>
              {scene.date && (
                <div className={styles.date}>
                  <CalendarOutlined /> {new Date(scene.date).toLocaleDateString()}
                </div>
              )}
              
              {scene.studio && (
                <Tag color="blue">{scene.studio.name}</Tag>
              )}
              
              <div className={styles.fileInfo}>
                <span>{scene.width}x{scene.height}</span>
                <span>{formatFileSize(scene.size)}</span>
              </div>

              {showDetails && (
                <>
                  {scene.performers && scene.performers.length > 0 && (
                    <div className={styles.performers}>
                      <Space size={4} wrap>
                        {scene.performers.slice(0, 3).map(performer => (
                          <Tag key={performer.id} color="purple">
                            {performer.name}
                          </Tag>
                        ))}
                        {scene.performers.length > 3 && (
                          <Tag>+{scene.performers.length - 3} more</Tag>
                        )}
                      </Space>
                    </div>
                  )}
                  
                  {scene.tags && scene.tags.length > 0 && (
                    <div className={styles.tags}>
                      <Space size={4} wrap>
                        {scene.tags.slice(0, 5).map(tag => (
                          <Tag key={tag.id}>{tag.name}</Tag>
                        ))}
                        {scene.tags.length > 5 && (
                          <Tag>+{scene.tags.length - 5} more</Tag>
                        )}
                      </Space>
                    </div>
                  )}
                </>
              )}
            </div>
          }
        />
      </Card>
    </Badge.Ribbon>
  );
};