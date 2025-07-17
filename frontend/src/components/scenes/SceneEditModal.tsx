import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  DatePicker,
  Select,
  Rate,
  Button,
  message,
} from 'antd';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import dayjs from 'dayjs';
import apiClient from '@/services/apiClient';
import { Scene, Performer, Tag, Studio } from '@/types/models';

const { TextArea } = Input;

interface SceneEditModalProps {
  visible: boolean;
  scene: Scene;
  onClose: () => void;
  onSuccess?: () => void;
}

export const SceneEditModal: React.FC<SceneEditModalProps> = ({
  visible,
  scene,
  onClose,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const [loading, setLoading] = useState(false);

  // Fetch all performers, tags, and studios for selection
  const { data: performers } = useQuery('all-performers', () =>
    apiClient.getPerformers({ per_page: 1000 })
  );
  const { data: tags } = useQuery('all-tags', () =>
    apiClient.getTags({ per_page: 1000 })
  );
  const { data: studios } = useQuery('all-studios', () =>
    apiClient.getStudios({ per_page: 1000 })
  );

  // Update scene mutation
  const updateMutation = useMutation(
    async (updates: Partial<Scene>) => {
      return apiClient.updateScene(Number(scene.id), updates);
    },
    {
      onSuccess: () => {
        void message.success('Scene updated successfully');
        void queryClient.invalidateQueries(['scene', scene.id]);
        onSuccess?.();
        onClose();
      },
      onError: (error: unknown) => {
        const err = error as { response?: { data?: { detail?: string } } };
        void message.error(
          err.response?.data?.detail || 'Failed to update scene'
        );
      },
    }
  );

  // Set initial form values when scene changes
  useEffect(() => {
    if (scene && visible) {
      form.setFieldsValue({
        title: scene.title || '',
        details: scene.details || '',
        date: scene.stash_date ? dayjs(scene.stash_date) : undefined,
        rating: scene.rating ? scene.rating / 20 : 0, // Convert from 0-100 to 0-5
        organized: scene.organized,
        studio_id: scene.studio?.id,
        performer_ids: scene.performers?.map((p) => p.id) || [],
        tag_ids: scene.tags?.map((t) => t.id) || [],
      });
    }
  }, [scene, visible, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // Prepare updates
      interface UpdateValues {
        title: string;
        details?: string;
        organized?: boolean;
        rating?: number;
        studio_id?: string | null;
        performer_ids?: string[];
        tag_ids?: string[];
        date?: string;
      }

      const updates: UpdateValues = {
        title: values.title,
        details: values.details,
        organized: values.organized,
        rating: values.rating ? values.rating * 20 : 0, // Convert from 0-5 to 0-100
        studio_id: values.studio_id || null,
        performer_ids: values.performer_ids || [],
        tag_ids: values.tag_ids || [],
      };

      // Handle date
      if (values.date) {
        updates.date = values.date.format('YYYY-MM-DD');
      }

      await updateMutation.mutateAsync(updates);
    } catch (error) {
      console.error('Failed to update scene:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Edit Scene"
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="cancel" onClick={onClose}>
          Cancel
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={loading || updateMutation.isLoading}
          onClick={() => void handleSubmit()}
        >
          Save Changes
        </Button>,
      ]}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="title"
          label="Title"
          rules={[{ required: true, message: 'Please enter a title' }]}
        >
          <Input />
        </Form.Item>

        <Form.Item name="details" label="Details/Description">
          <TextArea rows={4} />
        </Form.Item>

        <Form.Item name="date" label="Date">
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item name="rating" label="Rating">
          <Rate />
        </Form.Item>

        <Form.Item name="studio_id" label="Studio">
          <Select
            showSearch
            allowClear
            placeholder="Select a studio"
            optionFilterProp="label"
            loading={!studios}
            options={studios?.items?.map((studio: Studio) => ({
              value: studio.id,
              label: studio.name,
            }))}
          />
        </Form.Item>

        <Form.Item name="performer_ids" label="Performers">
          <Select
            mode="multiple"
            showSearch
            placeholder="Select performers"
            optionFilterProp="label"
            loading={!performers}
            options={performers?.items?.map((performer: Performer) => ({
              value: performer.id,
              label: performer.name,
            }))}
          />
        </Form.Item>

        <Form.Item name="tag_ids" label="Tags">
          <Select
            mode="multiple"
            showSearch
            placeholder="Select tags"
            optionFilterProp="label"
            loading={!tags}
            options={tags?.items?.map((tag: Tag) => ({
              value: tag.id,
              label: tag.name,
            }))}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};
