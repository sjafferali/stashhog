import React from 'react';
import { Empty } from 'antd';
import { Scene } from '@/types/models';
import { ViewMode } from '@/store/slices/scenes';
import { GridView } from './GridView';
import { ListView } from './ListView';

interface SceneListContainerProps {
  scenes: Scene[];
  viewMode: ViewMode;
  onSceneSelect: (scene: Scene) => void;
}

export const SceneListContainer: React.FC<SceneListContainerProps> = ({
  scenes,
  viewMode,
  onSceneSelect,
}) => {
  if (scenes.length === 0) {
    return (
      <Empty
        description="No scenes found"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        style={{ padding: '48px 0' }}
      />
    );
  }

  return viewMode === 'grid' ? (
    <GridView scenes={scenes} onSceneSelect={onSceneSelect} />
  ) : (
    <ListView scenes={scenes} onSceneSelect={onSceneSelect} />
  );
};
