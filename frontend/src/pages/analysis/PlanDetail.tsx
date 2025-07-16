import React, { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Row,
  Col,
  Card,
  Button,
  Space,
  Spin,
  Alert,
  Statistic,
  Progress,
  Badge,
  Dropdown,
  Menu,
  // Divider,
  Modal,
  InputNumber,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExportOutlined,
  ThunderboltOutlined,
  FilterOutlined,
  // SortAscendingOutlined,
  UndoOutlined,
  RedoOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { usePlanDetail } from './hooks/usePlanDetail';
import { useChangeManager } from './hooks/useChangeManager';
import { SceneChangesList, PlanSummary } from '@/components/analysis';
import ApplyPlanModal from './components/ApplyPlanModal';
import api from '@/services/api';
import { Scene } from '@/types/models';

const PlanDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const planId = parseInt(id || '0');

  const [selectedSceneId, setSelectedSceneId] = useState<string | undefined>(
    undefined
  );
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.8);

  const {
    plan,
    loading,
    error,
    refresh,
    updateChange,
    acceptChange,
    rejectChange,
    acceptAllChanges,
    rejectAllChanges,
    getStatistics,
  } = usePlanDetail(planId);

  // Flatten all changes for change manager
  const allChanges = useMemo(() => {
    if (!plan) return [];

    return plan.scenes.flatMap((scene) =>
      scene.changes.map((change) => ({
        ...change,
        sceneId: scene.scene.id,
      }))
    );
  }, [plan]);

  const changeManager = useChangeManager(
    planId,
    allChanges,
    (changeId, update) => {
      // Update change in the plan
      if (update.accepted !== undefined) {
        if (update.accepted) {
          acceptChange(changeId);
        } else {
          rejectChange(changeId);
        }
      }
      if (update.proposedValue !== undefined) {
        void updateChange(changeId, update.proposedValue);
      }
    }
  );

  const stats = getStatistics();

  // Handle scene preview
  const handlePreviewScene = (scene: Scene) => {
    window.open(`/scenes/${scene.id}`, '_blank');
  };

  // Handle accept/reject all for a scene
  const handleAcceptAllScene = (sceneId: string) => {
    acceptAllChanges(sceneId);
    void message.success('All changes accepted for scene');
  };

  const handleRejectAllScene = (sceneId: string) => {
    rejectAllChanges(sceneId);
    void message.success('All changes rejected for scene');
  };

  // Bulk actions menu
  const bulkActionsMenu = (
    <Menu>
      <Menu.Item
        key="accept-all"
        icon={<CheckCircleOutlined />}
        onClick={() => {
          acceptAllChanges();
          void message.success('All changes accepted');
        }}
      >
        Accept All Changes
      </Menu.Item>
      <Menu.Item
        key="reject-all"
        icon={<CloseCircleOutlined />}
        onClick={() => {
          rejectAllChanges();
          void message.success('All changes rejected');
        }}
      >
        Reject All Changes
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item
        key="accept-confidence"
        icon={<ThunderboltOutlined />}
        onClick={() => {
          Modal.confirm({
            title: 'Accept High Confidence Changes',
            content: (
              <div>
                <p>Set minimum confidence threshold:</p>
                <InputNumber
                  min={0}
                  max={1}
                  step={0.1}
                  value={confidenceThreshold}
                  onChange={(val: number | null) =>
                    setConfidenceThreshold(val || 0.8)
                  }
                  formatter={(value?: number) =>
                    `${((value || 0) * 100).toFixed(0)}%`
                  }
                  parser={(value?: string) =>
                    value ? parseInt(value.replace('%', '')) / 100 : 0
                  }
                  style={{ width: '100%' }}
                />
              </div>
            ),
            onOk: () =>
              void changeManager.acceptByConfidence(confidenceThreshold),
          });
        }}
      >
        Accept by Confidence
      </Menu.Item>
      <Menu.SubMenu
        key="accept-field"
        title="Accept by Field"
        icon={<FilterOutlined />}
      >
        <Menu.Item onClick={() => void changeManager.acceptByField('title')}>
          Title
        </Menu.Item>
        <Menu.Item
          onClick={() => void changeManager.acceptByField('performers')}
        >
          Performers
        </Menu.Item>
        <Menu.Item onClick={() => void changeManager.acceptByField('tags')}>
          Tags
        </Menu.Item>
        <Menu.Item onClick={() => void changeManager.acceptByField('studio')}>
          Studio
        </Menu.Item>
        <Menu.Item onClick={() => void changeManager.acceptByField('details')}>
          Details
        </Menu.Item>
      </Menu.SubMenu>
    </Menu>
  );

  // Export menu
  const exportMenu = (
    <Menu>
      <Menu.Item
        key="json"
        onClick={() => void changeManager.exportChanges('json')}
      >
        Export as JSON
      </Menu.Item>
      <Menu.Item
        key="csv"
        onClick={() => void changeManager.exportChanges('csv')}
      >
        Export as CSV
      </Menu.Item>
      <Menu.Item
        key="markdown"
        onClick={() => void changeManager.exportChanges('markdown')}
      >
        Export as Markdown
      </Menu.Item>
    </Menu>
  );

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error || !plan) {
    return (
      <Alert
        message="Error"
        description="Failed to load plan details"
        type="error"
        showIcon
        action={
          <Button
            size="small"
            onClick={() => {
              void navigate('/analysis/plans');
            }}
          >
            Back to Plans
          </Button>
        }
      />
    );
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 8 }}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => {
              void navigate('/analysis/plans');
            }}
          >
            Back
          </Button>
          <h1 style={{ margin: 0 }}>{plan.name}</h1>
          <Badge
            status={plan.status === 'APPLIED' ? 'success' : 'processing'}
            text={plan.status}
          />
        </Space>

        <Space style={{ float: 'right' }}>
          <Button
            icon={<UndoOutlined />}
            disabled={!changeManager.canUndo}
            onClick={() => void changeManager.undo()}
          >
            Undo
          </Button>
          <Button
            icon={<RedoOutlined />}
            disabled={!changeManager.canRedo}
            onClick={() => void changeManager.redo()}
          >
            Redo
          </Button>
          <Dropdown overlay={exportMenu}>
            <Button icon={<ExportOutlined />}>Export</Button>
          </Dropdown>
          <Dropdown overlay={bulkActionsMenu}>
            <Button type="primary">Bulk Actions</Button>
          </Dropdown>
        </Space>
      </div>

      {/* Statistics Row */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Total Changes"
              value={stats.totalChanges}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Accepted"
              value={stats.acceptedChanges}
              valueStyle={{ color: '#52c41a' }}
              suffix={`(${stats.acceptanceRate.toFixed(0)}%)`}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Rejected"
              value={stats.rejectedChanges}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Pending"
              value={stats.pendingChanges}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Avg Confidence"
              value={stats.averageConfidence * 100}
              precision={0}
              suffix="%"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic title="Scenes" value={plan.total_scenes} />
          </Card>
        </Col>
      </Row>

      {/* Progress Bar */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span>Review Progress:</span>
          <Progress
            percent={
              ((stats.acceptedChanges + stats.rejectedChanges) /
                stats.totalChanges) *
              100
            }
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            disabled={stats.acceptedChanges === 0}
            onClick={() => setShowApplyModal(true)}
          >
            Apply Changes ({stats.acceptedChanges})
          </Button>
        </div>
      </Card>

      {/* Main Content */}
      <Row gutter={16}>
        <Col span={16}>
          <Card title="Scene Changes" size="small">
            <SceneChangesList
              sceneChanges={plan.scenes}
              onSelectScene={setSelectedSceneId}
              selectedSceneId={selectedSceneId}
              onAcceptAll={handleAcceptAllScene}
              onRejectAll={handleRejectAllScene}
              onPreviewScene={handlePreviewScene}
              onAcceptChange={acceptChange}
              onRejectChange={rejectChange}
              onEditChange={updateChange}
            />
          </Card>
        </Col>

        <Col span={8}>
          <Card title="Plan Summary" size="small">
            <PlanSummary
              plan={{
                id: plan.id,
                name: plan.name,
                description: plan.description,
                status: plan.status,
                total_scenes: plan.total_scenes,
                total_changes: plan.total_changes,
                model: plan.metadata.model || 'gpt-4',
                temperature: plan.metadata.temperature || 0.7,
                active: plan.status !== 'CANCELLED',
                created_at: plan.created_at,
                updated_at: plan.updated_at,
                extract_performers:
                  plan.metadata.options?.detect_performers || false,
                extract_tags: plan.metadata.options?.detect_tags || false,
                extract_studio: plan.metadata.options?.detect_studios || false,
                extract_title: true,
                extract_date: true,
                extract_details: plan.metadata.options?.detect_details || false,
                prompt_template: '',
                metadata: plan.metadata,
              }}
              statistics={{
                totalScenes: plan.total_scenes,
                analyzedScenes: plan.total_scenes,
                pendingScenes: 0,
                totalChanges: stats.totalChanges,
                acceptedChanges: stats.acceptedChanges,
                rejectedChanges: stats.rejectedChanges,
                avgConfidence: stats.averageConfidence,
                // acceptanceRate: stats.acceptanceRate / 100,
                avgProcessingTime: 0,
                fieldBreakdown: {
                  title: allChanges.filter((c) => c.field === 'title').length,
                  performers: allChanges.filter((c) => c.field === 'performers')
                    .length,
                  tags: allChanges.filter((c) => c.field === 'tags').length,
                  studio: allChanges.filter((c) => c.field === 'studio').length,
                  details: allChanges.filter((c) => c.field === 'details')
                    .length,
                  date: allChanges.filter((c) => c.field === 'date').length,
                  custom: allChanges.filter((c) => c.field === 'custom').length,
                },
              }}
              onApply={() => setShowApplyModal(true)}
              onDelete={() => {
                Modal.confirm({
                  title: 'Delete Plan',
                  content:
                    'Are you sure you want to delete this plan? This action cannot be undone.',
                  onOk: async () => {
                    // TODO: Implement delete
                    void message.info(
                      'Delete functionality not implemented yet'
                    );
                  },
                });
              }}
              loading={false}
            />
          </Card>
        </Col>
      </Row>

      {/* Apply Changes Modal */}
      <ApplyPlanModal
        visible={showApplyModal}
        planId={planId}
        planName={plan.name}
        acceptedChanges={stats.acceptedChanges}
        totalScenes={plan.total_scenes}
        onCancel={() => setShowApplyModal(false)}
        onApply={async () => {
          // Get accepted change IDs
          const acceptedChangeIds = allChanges
            .filter((c) => c.accepted)
            .map((c) => c.id);

          // Call API to apply changes
          const response = await api.post(`/analysis/plans/${planId}/apply`, {
            change_ids: acceptedChangeIds,
            background: true,
          });

          return response.data;
        }}
        onComplete={() => {
          // Refresh the plan data
          void refresh();
          void message.success('All changes applied successfully');
        }}
      />
    </div>
  );
};

export default PlanDetail;
