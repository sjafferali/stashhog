export type JobType =
  | 'sync'
  | 'sync_all'
  | 'sync_scenes'
  | 'analysis'
  | 'apply_plan'
  | 'generate_details'
  | 'export'
  | 'import'
  | 'cleanup'
  | 'settings_test'
  | 'scene_sync'
  | 'scene_analysis'
  | 'stash_scan'
  | 'stash_generate'
  | 'check_stash_generate'
  | 'process_downloads'
  | 'process_new_scenes'
  | 'test';

export const JOB_TYPE_LABELS: Record<string, string> = {
  sync: 'Sync',
  sync_all: 'Full Sync',
  sync_scenes: 'Sync Scenes',
  analysis: 'Scene Analysis',
  scene_analysis: 'Scene Analysis', // Handle legacy type
  scene_sync: 'Scene Sync', // Handle legacy type
  apply_plan: 'Apply Plan',
  generate_details: 'Generate Details',
  export: 'Export',
  import: 'Import',
  cleanup: 'Cleanup',
  settings_test: 'Settings Test',
  stash_scan: 'Stash Metadata Scan',
  stash_generate: 'Stash Generate Metadata',
  check_stash_generate: 'Check Resource Generation',
  process_downloads: 'Process Downloads',
  process_new_scenes: 'Process New Scenes',
  test: 'Test Job',
};

export const JOB_TYPE_COLORS: Record<string, string> = {
  sync: 'blue',
  sync_all: 'blue',
  sync_scenes: 'blue',
  scene_sync: 'blue',
  analysis: 'green',
  scene_analysis: 'green',
  apply_plan: 'purple',
  generate_details: 'orange',
  export: 'cyan',
  import: 'cyan',
  cleanup: 'magenta',
  settings_test: 'purple',
  stash_scan: 'volcano',
  stash_generate: 'geekblue',
  check_stash_generate: 'orange',
  process_downloads: 'geekblue',
  process_new_scenes: 'purple',
  test: 'cyan',
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
  if (
    total !== undefined &&
    total !== null &&
    processed !== undefined &&
    processed !== null
  ) {
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
    } else if (type === 'stash_scan') {
      unit = ' files';
    } else if (type === 'stash_generate') {
      unit = ' items';
    } else if (type === 'check_stash_generate') {
      unit = ' resources';
    } else if (type === 'process_downloads') {
      unit = ' downloads';
    } else if (type === 'process_new_scenes') {
      unit = ' steps';
    }

    return `${processed} / ${total}${unit}`;
  }

  return `${Math.round(progress || 0)}%`;
};

export const JOB_TYPE_DESCRIPTIONS: Record<string, string> = {
  sync: 'Synchronize all data with Stash',
  sync_all: 'Full synchronization of all entities with Stash',
  sync_scenes: 'Synchronize specific scenes with Stash',
  analysis: 'Analyze scenes with AI',
  scene_analysis: 'Analyze scenes with AI',
  scene_sync: 'Synchronize scenes with Stash',
  apply_plan: 'Apply analysis plan changes',
  generate_details: 'Generate scene details with AI',
  export: 'Export data',
  import: 'Import data',
  cleanup: 'Clean up old jobs, stuck plans, and download logs',
  settings_test: 'Test system settings',
  stash_scan: 'Scan and update metadata in Stash library',
  stash_generate:
    'Generate preview images, sprites, and metadata for media files',
  check_stash_generate: 'Check for resources requiring generation in Stash',
  process_downloads: 'Process downloaded content',
  process_new_scenes:
    'Complete workflow to process newly downloaded scenes through scanning, analysis, and metadata generation',
  test: 'Test job demonstrating daemon job orchestration',
};

export const getJobTypeDescription = (type: string): string => {
  return JOB_TYPE_DESCRIPTIONS[type] || 'Unknown job type';
};
