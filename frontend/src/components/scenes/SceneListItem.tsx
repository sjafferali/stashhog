import React from 'react';
import { List, Tag, Space, Checkbox, Button, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import {
  CalendarOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  EyeOutlined,
  EditOutlined,
  ExperimentOutlined,
  MoreOutlined,
  StarFilled,
} from '@ant-design/icons';
import { Scene } from '@/types/models';
import { SceneAction } from './SceneCard';
import styles from './SceneListItem.module.scss';

export interface SceneListItemProps {
  scene: Scene;
  onClick?: (scene: Scene) => void;
  actions?: SceneAction[];
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (selected: boolean) => void;
}

export const SceneListItem: React.FC<SceneListItemProps> = ({
  scene,
  onClick,
  actions = [],
  selectable = false,
  selected = false,
  onSelect,
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

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    const size = bytes;
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let unitIndex = 0;
    let value = size;

    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex++;
    }

    return `${value.toFixed(1)} ${units[unitIndex]}`;
  };

  const menuItems: MenuProps['items'] = actions.map((action) => ({
    key: action.key,
    label: action.label,
    icon: action.icon,
    danger: action.danger,
    onClick: () => action.onClick(scene),
  }));

  const listActions = [
    <Button
      key="view"
      type="text"
      size="small"
      icon={<EyeOutlined />}
      onClick={() => onClick?.(scene)}
    >
      View
    </Button>,
    <Button
      key="edit"
      type="text"
      size="small"
      icon={<EditOutlined />}
      onClick={() => actions.find((a) => a.key === 'edit')?.onClick(scene)}
    >
      Edit
    </Button>,
    <Button
      key="analyze"
      type="text"
      size="small"
      icon={<ExperimentOutlined />}
      onClick={() => actions.find((a) => a.key === 'analyze')?.onClick(scene)}
    >
      Analyze
    </Button>,
  ];

  if (menuItems.length > 0) {
    listActions.push(
      <Dropdown key="more" menu={{ items: menuItems }} trigger={['click']}>
        <Button type="text" size="small" icon={<MoreOutlined />} />
      </Dropdown>
    );
  }

  return (
    <List.Item
      className={styles.sceneListItem}
      actions={listActions}
      extra={
        <img
          width={200}
          alt={scene.title}
          src={`/api/scenes/${scene.id}/thumbnail`}
          onError={(e) => {
            (e.target as HTMLImageElement).src = '/placeholder-scene.png';
          }}
        />
      }
    >
      <List.Item.Meta
        avatar={
          selectable && (
            <Checkbox
              checked={selected}
              onChange={(e) => onSelect?.(e.target.checked)}
            />
          )
        }
        title={
          <div className={styles.title}>
            <span onClick={() => onClick?.(scene)}>{scene.title}</span>
            {scene.rating && (
              <span className={styles.rating}>
                <StarFilled /> {scene.rating}
              </span>
            )}
            {scene.analyzed && <Tag color="green">Analyzed</Tag>}
          </div>
        }
        description={
          <div className={styles.metadata}>
            <Space size="middle" wrap>
              {scene.stash_date && (
                <span>
                  <CalendarOutlined />{' '}
                  {new Date(scene.stash_date).toLocaleDateString()}
                </span>
              )}
              <span>
                <ClockCircleOutlined /> {formatDuration(scene.duration)}
              </span>
              <span>
                <DatabaseOutlined /> {formatFileSize(scene.size)}
              </span>
              <span>
                {scene.width}x{scene.height}
              </span>
            </Space>

            <div className={styles.tags}>
              {scene.studio && <Tag color="blue">{scene.studio.name}</Tag>}

              {scene.performers && scene.performers.length > 0 && (
                <Space size={4}>
                  {scene.performers.slice(0, 3).map((performer) => (
                    <Tag key={performer.id} color="purple">
                      {performer.name}
                    </Tag>
                  ))}
                  {scene.performers.length > 3 && (
                    <Tag>+{scene.performers.length - 3} more</Tag>
                  )}
                </Space>
              )}

              {scene.tags && scene.tags.length > 0 && (
                <Space size={4}>
                  {scene.tags.slice(0, 5).map((tag) => (
                    <Tag key={tag.id}>{tag.name}</Tag>
                  ))}
                  {scene.tags.length > 5 && (
                    <Tag>+{scene.tags.length - 5} more</Tag>
                  )}
                </Space>
              )}
            </div>
          </div>
        }
      />
    </List.Item>
  );
};
