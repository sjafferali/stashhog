export type JobType =
  | 'sync'
  | 'sync_all'
  | 'sync_scenes'
  | 'sync_performers'
  | 'sync_tags'
  | 'sync_studios'
  | 'analysis'
  | 'apply_plan'
  | 'generate_details'
  | 'export'
  | 'import'
  | 'cleanup'
  | 'settings_test'
  | 'scene_sync'
  | 'scene_analysis';

export const JOB_TYPE_LABELS: Record<string, string> = {
  sync: 'Sync',
  sync_all: 'Full Sync',
  sync_scenes: 'Sync Scenes',
  sync_performers: 'Sync Performers',
  sync_tags: 'Sync Tags',
  sync_studios: 'Sync Studios',
  analysis: 'Scene Analysis',
  scene_analysis: 'Scene Analysis', // Handle legacy type
  scene_sync: 'Scene Sync', // Handle legacy type
  apply_plan: 'Apply Plan',
  generate_details: 'Generate Details',
  export: 'Export',
  import: 'Import',
  cleanup: 'Cleanup',
  settings_test: 'Settings Test',
};

export const JOB_TYPE_COLORS: Record<string, string> = {
  sync: 'blue',
  sync_all: 'blue',
  sync_scenes: 'blue',
  sync_performers: 'blue',
  sync_tags: 'blue',
  sync_studios: 'blue',
  scene_sync: 'blue',
  analysis: 'green',
  scene_analysis: 'green',
  apply_plan: 'purple',
  generate_details: 'orange',
  export: 'cyan',
  import: 'cyan',
  cleanup: 'magenta',
  settings_test: 'purple',
};

export const getJobTypeLabel = (type: string): string => {
  return (
    JOB_TYPE_LABELS[type] ||
    type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
  );
};

export const getJobTypeColor = (type: string): string => {
  // Check exact match first
  if (JOB_TYPE_COLORS[type]) {
    return JOB_TYPE_COLORS[type];
  }

  // Check by prefix for backward compatibility
  if (type.includes('sync')) return 'blue';
  if (type.includes('analysis')) return 'green';
  if (type.includes('test')) return 'purple';

  return 'default';
};

export const formatJobProgress = (
  type: string,
  processed: number | undefined,
  total: number | undefined,
  progress: number
): string => {
  if (total !== undefined && processed !== undefined) {
    // Determine the unit based on job type
    let unit = '';
    if (
      type === 'sync' ||
      type === 'sync_all' ||
      type === 'sync_scenes' ||
      type === 'scene_sync' ||
      type === 'analysis' ||
      type === 'scene_analysis'
    ) {
      unit = ' scenes';
    } else if (type === 'apply_plan') {
      unit = ' changes';
    } else if (type === 'sync_performers') {
      unit = ' performers';
    } else if (type === 'sync_tags') {
      unit = ' tags';
    } else if (type === 'sync_studios') {
      unit = ' studios';
    }

    return `${processed} / ${total}${unit}`;
  }

  return `${Math.round(progress)}%`;
};
