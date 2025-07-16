import React, { useMemo } from 'react';
import { Row, Col, Empty, Segmented } from 'antd';
import { AppstoreOutlined, BarsOutlined } from '@ant-design/icons';
import VirtualList from 'rc-virtual-list';
import { Scene } from '@/types/models';
import { SceneCard, SceneAction } from './SceneCard';
import { SceneListItem } from './SceneListItem';
import { LoadingSpinner } from '../common';
import styles from './SceneGrid.module.scss';

export interface SceneGridProps {
  scenes: Scene[];
  loading?: boolean;
  onSceneClick?: (scene: Scene) => void;
  layout?: 'grid' | 'list';
  onLayoutChange?: (layout: 'grid' | 'list') => void;
  sceneActions?: SceneAction[];
  virtualScroll?: boolean;
  selectable?: boolean;
  selectedIds?: string[];
  onSelectionChange?: (ids: string[]) => void;
}

export const SceneGrid: React.FC<SceneGridProps> = ({
  scenes,
  loading = false,
  onSceneClick,
  layout = 'grid',
  onLayoutChange,
  sceneActions = [],
  virtualScroll = true,
  selectable = false,
  selectedIds = [],
  onSelectionChange,
}) => {
  const containerHeight = 600; // Adjust based on your layout

  const layoutOptions = [
    { label: <AppstoreOutlined />, value: 'grid' },
    { label: <BarsOutlined />, value: 'list' },
  ];

  const gridColumns = useMemo(() => {
    return {
      xs: 24,
      sm: 12,
      md: 8,
      lg: 6,
      xl: 4,
      xxl: 4,
    };
  }, []);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (scenes.length === 0) {
    return <Empty description="No scenes found" />;
  }

  const renderScene = (scene: Scene) => {
    if (layout === 'list') {
      return (
        <SceneListItem
          key={scene.id}
          scene={scene}
          onClick={onSceneClick}
          actions={sceneActions}
          selectable={selectable}
          selected={selectedIds.includes(scene.id)}
          onSelect={(selected) => {
            if (onSelectionChange) {
              const newIds = selected
                ? [...selectedIds, scene.id]
                : selectedIds.filter((id) => id !== scene.id);
              onSelectionChange(newIds);
            }
          }}
        />
      );
    }

    return (
      <Col key={scene.id} {...gridColumns}>
        <SceneCard
          scene={scene}
          onClick={onSceneClick}
          actions={sceneActions}
        />
      </Col>
    );
  };

  const content =
    layout === 'grid' ? (
      <Row gutter={[16, 16]}>{scenes.map(renderScene)}</Row>
    ) : virtualScroll && scenes.length > 20 ? (
      <VirtualList
        data={scenes}
        height={containerHeight}
        itemHeight={120}
        itemKey="id"
      >
        {(scene) => renderScene(scene)}
      </VirtualList>
    ) : (
      <div className={styles.listContainer}>{scenes.map(renderScene)}</div>
    );

  return (
    <div className={styles.sceneGrid}>
      {onLayoutChange && (
        <div className={styles.toolbar}>
          <Segmented
            options={layoutOptions}
            value={layout}
            onChange={onLayoutChange}
          />
        </div>
      )}
      {content}
    </div>
  );
};
