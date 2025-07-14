import React, { useState } from 'react';
import { Modal, Steps, Form, Input, Select, Button, Space, Typography, Alert } from 'antd';
import { CalendarOutlined, SettingOutlined, CheckCircleOutlined } from '@ant-design/icons';
import ScheduleBuilder from './ScheduleBuilder';
import TaskConfigurator from './TaskConfigurator';
import { useSchedules } from '../hooks/useSchedules';
import { CreateScheduleData } from '../types';

const { Step } = Steps;
const { TextArea } = Input;
const { Title, Text } = Typography;

interface CreateScheduleModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const CreateScheduleModal: React.FC<CreateScheduleModalProps> = ({ visible, onClose, onSuccess }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const { createSchedule } = useSchedules();

  const handleClose = () => {
    form.resetFields();
    setCurrentStep(0);
    onClose();
  };

  const handleNext = async () => {
    try {
      await form.validateFields();
      setCurrentStep(currentStep + 1);
    } catch (error) {
      // Validation failed
    }
  };

  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();
      
      const scheduleData: CreateScheduleData = {
        name: values.name,
        description: values.description,
        task_type: values.task_type,
        schedule: values.schedule,
        config: values.config || {},
        enabled: true,
      };

      await createSchedule(scheduleData);
      handleClose();
      onSuccess();
    } catch (error) {
      console.error('Failed to create schedule:', error);
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    {
      title: 'Task Type',
      icon: <SettingOutlined />,
      content: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={4}>Select Task Type</Title>
            <Text type="secondary">Choose what type of task you want to schedule</Text>
          </div>
          
          <Form.Item
            name="task_type"
            rules={[{ required: true, message: 'Please select a task type' }]}
          >
            <Select
              size="large"
              placeholder="Select task type"
              options={[
                { 
                  value: 'sync', 
                  label: 'Sync Task',
                  description: 'Synchronize data from Stash'
                },
                { 
                  value: 'analysis', 
                  label: 'Analysis Task',
                  description: 'Analyze scenes and generate tagging plans'
                },
                { 
                  value: 'cleanup', 
                  label: 'Cleanup Task',
                  description: 'Clean up old data and logs'
                },
              ]}
              optionRender={(option) => (
                <Space direction="vertical" size={0}>
                  <Text strong>{option.label}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {option.data.description}
                  </Text>
                </Space>
              )}
            />
          </Form.Item>

          <Form.Item
            name="name"
            rules={[{ required: true, message: 'Please enter a schedule name' }]}
          >
            <Input
              size="large"
              placeholder="Schedule name"
              prefix={<CalendarOutlined />}
            />
          </Form.Item>

          <Form.Item name="description">
            <TextArea
              placeholder="Description (optional)"
              rows={3}
            />
          </Form.Item>
        </Space>
      ),
    },
    {
      title: 'Configuration',
      icon: <SettingOutlined />,
      content: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={4}>Configure Task</Title>
            <Text type="secondary">Set up task-specific options</Text>
          </div>
          
          <Form.Item shouldUpdate>
            {() => {
              const taskType = form.getFieldValue('task_type');
              return taskType ? (
                <TaskConfigurator
                  taskType={taskType}
                  onChange={(config) => form.setFieldValue('config', config)}
                />
              ) : (
                <Alert
                  message="Please select a task type first"
                  type="info"
                />
              );
            }}
          </Form.Item>
        </Space>
      ),
    },
    {
      title: 'Schedule',
      icon: <CalendarOutlined />,
      content: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={4}>Set Schedule</Title>
            <Text type="secondary">Define when the task should run</Text>
          </div>
          
          <Form.Item
            name="schedule"
            rules={[{ required: true, message: 'Please set a schedule' }]}
          >
            <ScheduleBuilder />
          </Form.Item>
        </Space>
      ),
    },
    {
      title: 'Review',
      icon: <CheckCircleOutlined />,
      content: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={4}>Review Schedule</Title>
            <Text type="secondary">Confirm your schedule settings</Text>
          </div>
          
          <Form.Item shouldUpdate>
            {() => {
              const values = form.getFieldsValue();
              return (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Alert
                    message="Schedule Summary"
                    description={
                      <Space direction="vertical">
                        <div><strong>Name:</strong> {values.name || 'Not set'}</div>
                        <div><strong>Type:</strong> {values.task_type || 'Not set'}</div>
                        <div><strong>Schedule:</strong> {values.schedule || 'Not set'}</div>
                        {values.description && (
                          <div><strong>Description:</strong> {values.description}</div>
                        )}
                      </Space>
                    }
                    type="info"
                  />
                </Space>
              );
            }}
          </Form.Item>
        </Space>
      ),
    },
  ];

  return (
    <Modal
      title="Create Schedule"
      open={visible}
      onCancel={handleClose}
      width={800}
      footer={null}
    >
      <Form
        form={form}
        layout="vertical"
        size="large"
      >
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          {steps.map((step) => (
            <Step key={step.title} title={step.title} icon={step.icon} />
          ))}
        </Steps>

        <div style={{ minHeight: 300 }}>
          {steps[currentStep].content}
        </div>

        <div style={{ marginTop: 24, textAlign: 'right' }}>
          <Space>
            {currentStep > 0 && (
              <Button onClick={handlePrev}>
                Previous
              </Button>
            )}
            {currentStep < steps.length - 1 && (
              <Button type="primary" onClick={handleNext}>
                Next
              </Button>
            )}
            {currentStep === steps.length - 1 && (
              <Button type="primary" onClick={handleSubmit} loading={loading}>
                Create Schedule
              </Button>
            )}
          </Space>
        </div>
      </Form>
    </Modal>
  );
};

export default CreateScheduleModal;