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
  Dropdown,
  Menu,
  // Divider,
  Modal,
  message,
  Tag,
} from 'antd';
import {
  ArrowLeftOutlined,
  CloseCircleOutlined,
  ExportOutlined,
  // SortAscendingOutlined,
  UndoOutlined,
  RedoOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { usePlanDetail } from './hooks/usePlanDetail';
import { useChangeManager } from './hooks/useChangeManager';
import { useJob } from './hooks/useJob';
import { SceneChangesList, PlanSummary } from '@/components/analysis';
import ApplyPlanModal from './components/ApplyPlanModal';
import BulkActions from './components/BulkActions';
import { JobProgress } from '@/components/jobs/JobProgress';
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

  const {
    plan,
    loading,
    error,
    costs,
    costsLoading,
    refresh,
    updateChange,
    acceptChange,
    rejectChange,
    acceptAllChanges,
    rejectAllChanges,
    acceptByConfidence,
    acceptByField,
    rejectByField,
    cancelPlan,
    getStatistics,
    getFieldCounts,
  } = usePlanDetail(planId);

  // Fetch job details if plan has a job_id
  const { job } = useJob(plan?.job_id);

  // Flatten all changes for change manager
  const allChanges = useMemo(() => {
    if (!plan) return [];

    return plan.scenes.flatMap((scene) =>
      scene.changes.map((change) => ({
        ...change,
        sceneId: scene.scene_id,
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
          void acceptChange(changeId);
        } else {
          void rejectChange(changeId);
        }
      }
      if (update.proposedValue !== undefined) {
        void updateChange(changeId, update.proposedValue);
      }
    }
  );

  const stats = getStatistics();

  // Handle scene preview
  const handlePreviewScene = (scene: Scene | { id: string; title: string }) => {
    window.open(`/scenes/${scene.id}`, '_blank');
  };

  // Handle accept/reject all for a scene
  const handleAcceptAllScene = (sceneId: string) => {
    void acceptAllChanges(sceneId);
  };

  const handleRejectAllScene = (sceneId: string) => {
    void rejectAllChanges(sceneId);
  };

  // Handle cancel plan
  const handleCancelPlan = () => {
    Modal.confirm({
      title: 'Cancel Plan',
      content:
        'Are you sure you want to cancel this plan? This action cannot be undone.',
      onOk: () => void cancelPlan(),
    });
  };

  const fieldCounts = getFieldCounts();

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
          <Tag
            color={
              plan.status === 'pending'
                ? 'purple'
                : plan.status === 'draft'
                  ? 'blue'
                  : plan.status === 'reviewing'
                    ? 'orange'
                    : plan.status === 'applied'
                      ? 'green'
                      : plan.status === 'cancelled'
                        ? 'red'
                        : 'default'
            }
            style={{ fontWeight: 500, fontSize: '14px' }}
          >
            {plan.status.toUpperCase()}
          </Tag>
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
          {plan.status !== 'applied' &&
            plan.status !== 'cancelled' &&
            plan.status !== 'pending' && (
              <BulkActions
                totalChanges={stats.totalChanges}
                acceptedChanges={stats.acceptedChanges}
                rejectedChanges={stats.rejectedChanges}
                pendingChanges={stats.pendingChanges}
                onAcceptAll={() => acceptAllChanges()}
                onRejectAll={() => rejectAllChanges()}
                onAcceptByConfidence={(threshold) =>
                  void acceptByConfidence(threshold)
                }
                onAcceptByField={(field) => void acceptByField(field)}
                onRejectByField={(field) => void rejectByField(field)}
                fieldCounts={fieldCounts}
              />
            )}
        </Space>
      </div>

      {/* Job Progress for PENDING plans */}
      {plan.status === 'pending' && plan.job_id && (
        <div style={{ marginBottom: 16 }}>
          <Alert
            message="Analysis in Progress"
            description="This plan is being created as scenes are analyzed. Changes will appear as scenes complete processing."
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <JobProgress
            jobId={plan.job_id}
            showDetails={true}
            onComplete={() => {
              // Refresh the plan when the job completes
              void refresh();
            }}
          />
        </div>
      )}

      {/* Statistics Row */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}>
          <Card
            size="small"
            style={{ height: '100%', display: 'flex', alignItems: 'center' }}
            bodyStyle={{ width: '100%' }}
          >
            <Statistic
              title="Total Changes"
              value={stats.totalChanges}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card
            size="small"
            style={{ height: '100%', display: 'flex', alignItems: 'center' }}
            bodyStyle={{ width: '100%' }}
          >
            <Statistic
              title="Accepted"
              value={stats.acceptedChanges}
              valueStyle={{ color: '#52c41a' }}
              suffix={
                <span style={{ fontSize: '14px', fontWeight: 'normal' }}>
                  ({stats.acceptanceRate.toFixed(0)}%)
                </span>
              }
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card
            size="small"
            style={{ height: '100%', display: 'flex', alignItems: 'center' }}
            bodyStyle={{ width: '100%' }}
          >
            <Statistic
              title="Rejected"
              value={stats.rejectedChanges}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card
            size="small"
            style={{ height: '100%', display: 'flex', alignItems: 'center' }}
            bodyStyle={{ width: '100%' }}
          >
            <Statistic
              title="Pending"
              value={stats.pendingChanges}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card
            size="small"
            style={{ height: '100%', display: 'flex', alignItems: 'center' }}
            bodyStyle={{ width: '100%' }}
          >
            <Statistic
              title="Avg Confidence"
              value={stats.averageConfidence * 100}
              precision={0}
              suffix="%"
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card
            size="small"
            style={{ height: '100%', display: 'flex', alignItems: 'center' }}
            bodyStyle={{ width: '100%' }}
          >
            <Statistic title="Scenes" value={plan.total_scenes} />
          </Card>
        </Col>
      </Row>

      {/* Cost Row (if AI was used) */}
      {(costsLoading || (costs && costs.total_cost > 0)) && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          {costsLoading ? (
            <Col span={24}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <Spin size="small" /> Loading cost information...
              </Card>
            </Col>
          ) : costs && costs.total_cost > 0 ? (
            <>
              <Col span={6}>
                <Card size="small" style={{ height: '100%' }}>
                  <Statistic
                    title="Total API Cost"
                    value={costs.total_cost}
                    precision={4}
                    prefix="$"
                    valueStyle={{ color: '#722ed1' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small" style={{ height: '100%' }}>
                  <Statistic
                    title="Cost per Scene"
                    value={
                      costs.average_cost_per_scene ||
                      costs.total_cost / plan.total_scenes
                    }
                    precision={4}
                    prefix="$"
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small" style={{ height: '100%' }}>
                  <Statistic
                    title="Total Tokens"
                    value={costs.total_tokens}
                    suffix={costs.model ? ` (${costs.model})` : ''}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small" style={{ height: '100%' }}>
                  <Statistic
                    title="Token Breakdown"
                    value={`${costs.prompt_tokens || 0} / ${costs.completion_tokens || 0}`}
                    suffix="prompt / completion"
                    valueStyle={{ fontSize: '18px' }}
                  />
                </Card>
              </Col>
            </>
          ) : null}
        </Row>
      )}

      {/* Progress Bar */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span>Review Progress:</span>
          <Progress
            percent={Math.round(
              ((stats.acceptedChanges + stats.rejectedChanges) /
                stats.totalChanges) *
                100
            )}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            disabled={
              stats.unappliedAcceptedChanges === 0 ||
              plan.status === 'applied' ||
              plan.status === 'cancelled' ||
              plan.status === 'pending'
            }
            onClick={() => setShowApplyModal(true)}
          >
            Apply Changes ({stats.unappliedAcceptedChanges})
          </Button>
          <Button
            danger
            icon={<CloseCircleOutlined />}
            onClick={handleCancelPlan}
            disabled={
              plan.status === 'applied' ||
              plan.status === 'cancelled' ||
              plan.status === 'pending'
            }
          >
            Cancel Plan
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
              onAcceptAll={
                plan.status === 'applied' ||
                plan.status === 'cancelled' ||
                plan.status === 'pending'
                  ? undefined
                  : handleAcceptAllScene
              }
              onRejectAll={
                plan.status === 'applied' ||
                plan.status === 'cancelled' ||
                plan.status === 'pending'
                  ? undefined
                  : handleRejectAllScene
              }
              onPreviewScene={handlePreviewScene}
              onAcceptChange={
                plan.status === 'applied' ||
                plan.status === 'cancelled' ||
                plan.status === 'pending'
                  ? undefined
                  : (id) => void acceptChange(id)
              }
              onRejectChange={
                plan.status === 'applied' ||
                plan.status === 'cancelled' ||
                plan.status === 'pending'
                  ? undefined
                  : (id) => void rejectChange(id)
              }
              onEditChange={
                plan.status === 'applied' ||
                plan.status === 'cancelled' ||
                plan.status === 'pending'
                  ? undefined
                  : (id, value) => updateChange(id, value)
              }
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
                active: plan.status !== 'cancelled',
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
              statistics={(() => {
                const analyzedScenes = (() => {
                  // For pending plans with running jobs, use job progress
                  if (plan.status === 'pending' && job) {
                    if (job.status === 'running' || job.status === 'pending') {
                      return job.processed_items || 0;
                    }
                    // If job is completed, use total scenes
                    if (job.status === 'completed') {
                      return plan.total_scenes;
                    }
                  }
                  // For other statuses, use metadata or actual analyzed count
                  return (
                    plan.metadata?.scenes_analyzed || plan.scenes.length || 0
                  );
                })();

                const pendingScenes = (() => {
                  // For pending plans with running jobs
                  if (
                    plan.status === 'pending' &&
                    job &&
                    job.status === 'running'
                  ) {
                    return Math.max(
                      0,
                      plan.total_scenes - (job.processed_items || 0)
                    );
                  }
                  // For reviewing/draft plans, count scenes without changes as pending
                  if (plan.status === 'reviewing' || plan.status === 'draft') {
                    const scenesWithChanges = plan.scenes.length;
                    return Math.max(0, plan.total_scenes - scenesWithChanges);
                  }
                  return 0;
                })();

                const planStats = {
                  totalScenes: plan.total_scenes,
                  analyzedScenes,
                  pendingScenes,
                  totalChanges: stats.totalChanges,
                  acceptedChanges: stats.acceptedChanges,
                  rejectedChanges: stats.rejectedChanges,
                  avgConfidence: stats.averageConfidence,
                  // acceptanceRate: stats.acceptanceRate / 100,
                  avgProcessingTime: plan.metadata.processing_time || 0,
                  fieldBreakdown: {
                    title: allChanges.filter((c) => c.field === 'title').length,
                    performers: allChanges.filter(
                      (c) => c.field === 'performers'
                    ).length,
                    tags: allChanges.filter((c) => c.field === 'tags').length,
                    studio: allChanges.filter((c) => c.field === 'studio')
                      .length,
                    details: allChanges.filter((c) => c.field === 'details')
                      .length,
                    date: allChanges.filter((c) => c.field === 'date').length,
                    markers: allChanges.filter((c) => c.field === 'markers')
                      .length,
                    custom: allChanges.filter((c) => c.field === 'custom')
                      .length,
                  },
                };
                console.log('PlanDetail sending to PlanSummary:', {
                  planStatus: plan.status,
                  job,
                  stats: planStats,
                  totalScenes: plan.total_scenes,
                  scenesLength: plan.scenes.length,
                  metadata: plan.metadata,
                });
                return planStats;
              })()}
              onApply={() => setShowApplyModal(true)}
              loading={false}
              jobProgress={job?.progress}
            />
          </Card>
        </Col>
      </Row>

      {/* Apply Changes Modal */}
      <ApplyPlanModal
        visible={showApplyModal}
        planId={planId}
        planName={plan.name}
        acceptedChanges={stats.unappliedAcceptedChanges}
        totalScenes={plan.total_scenes}
        onCancel={() => setShowApplyModal(false)}
        onApply={async () => {
          // Get accepted but unapplied change IDs
          const acceptedChangeIds = allChanges
            .filter((c) => c.accepted && !c.applied)
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
