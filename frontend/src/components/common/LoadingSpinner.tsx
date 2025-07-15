import React from 'react';
import { Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import styles from './LoadingSpinner.module.scss';

export interface LoadingSpinnerProps {
  size?: 'small' | 'default' | 'large';
  text?: string;
  fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'default',
  text,
  fullScreen = false,
}) => {
  const antIcon = (
    <LoadingOutlined
      style={{ fontSize: size === 'small' ? 24 : size === 'large' ? 48 : 32 }}
      spin
    />
  );

  const spinner = (
    <div className={styles.spinnerContainer}>
      <Spin indicator={antIcon} size={size} tip={text} />
    </div>
  );

  if (fullScreen) {
    return <div className={styles.fullScreenOverlay}>{spinner}</div>;
  }

  return spinner;
};
