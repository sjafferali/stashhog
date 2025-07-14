import React, { useState } from 'react';
import { Modal } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';

export interface ConfirmModalProps {
  title: string;
  content: string | React.ReactNode;
  onConfirm: () => Promise<void>;
  danger?: boolean;
  open: boolean;
  onCancel: () => void;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  title,
  content,
  onConfirm,
  danger = false,
  open,
  onCancel,
}) => {
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
      onCancel(); // Close modal on success
    } catch (error) {
      console.error('Confirm action failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={
        <span>
          {danger && <ExclamationCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />}
          {title}
        </span>
      }
      open={open}
      onOk={handleConfirm}
      onCancel={onCancel}
      okText="Confirm"
      cancelText="Cancel"
      okButtonProps={{
        danger,
        loading,
      }}
      confirmLoading={loading}
    >
      {content}
    </Modal>
  );
};

export const confirmModal = (props: Omit<ConfirmModalProps, 'open' | 'onCancel'>) => {
  return new Promise<void>((resolve, reject) => {
    Modal.confirm({
      title: props.title,
      content: props.content,
      icon: props.danger ? <ExclamationCircleOutlined /> : null,
      okText: 'Confirm',
      okType: props.danger ? 'danger' : 'primary',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          await props.onConfirm();
          resolve();
        } catch (error) {
          reject(error);
        }
      },
      onCancel: () => {
        reject(new Error('User cancelled'));
      },
    });
  });
};