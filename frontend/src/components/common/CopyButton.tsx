import React, { useState } from 'react';
import { Button, Tooltip, message } from 'antd';
import { CopyOutlined, CheckOutlined } from '@ant-design/icons';
import styles from './CopyButton.module.scss';

export interface CopyButtonProps {
  text: string;
  size?: 'small' | 'middle' | 'large';
  type?: 'default' | 'primary' | 'dashed' | 'link' | 'text';
  showText?: boolean;
  buttonText?: string;
  onCopy?: () => void;
}

export const CopyButton: React.FC<CopyButtonProps> = ({
  text,
  size = 'small',
  type = 'text',
  showText = false,
  buttonText = 'Copy',
  onCopy,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      void message.success('Copied to clipboard');
      onCopy?.();

      // Reset icon after 2 seconds
      setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
      void message.error('Failed to copy to clipboard');
    }
  };

  return (
    <Tooltip title={copied ? 'Copied!' : 'Copy to clipboard'}>
      <Button
        type={type}
        size={size}
        icon={copied ? <CheckOutlined /> : <CopyOutlined />}
        onClick={() => void handleCopy()}
        className={`${styles.copyButton} ${copied ? styles.copied : ''}`}
      >
        {showText && (copied ? 'Copied!' : buttonText)}
      </Button>
    </Tooltip>
  );
};
