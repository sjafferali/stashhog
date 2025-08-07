/**
 * Service for fetching and managing job metadata from the backend.
 * This provides a single source of truth for job type configuration.
 */

import api from './api';

export interface JobMetadata {
  value: string;
  label: string;
  description: string;
  color: string;
  icon?: string;
  category?: string;
  unit?: string;
  unit_singular?: string;
  schema_value: string;
  allow_concurrent: boolean;
  is_workflow: boolean;
}

export interface JobMetadataResponse {
  job_types: JobMetadata[];
  categories: string[];
}

class JobMetadataService {
  private metadata: JobMetadataResponse | null = null;
  private metadataPromise: Promise<JobMetadataResponse> | null = null;
  private jobTypeMap: Map<string, JobMetadata> = new Map();

  /**
   * Fetch job metadata from the backend.
   * Uses caching to avoid multiple API calls.
   */
  async fetchMetadata(forceRefresh = false): Promise<JobMetadataResponse> {
    // Return cached metadata if available and not forcing refresh
    if (this.metadata && !forceRefresh) {
      return this.metadata;
    }

    // If already fetching, return the existing promise
    if (this.metadataPromise && !forceRefresh) {
      return this.metadataPromise as Promise<JobMetadataResponse>;
    }

    // Fetch metadata from backend
    this.metadataPromise = api
      .get<JobMetadataResponse>('/jobs/metadata')
      .then((response) => {
        this.metadata = response.data;
        // Build lookup map for quick access
        this.jobTypeMap.clear();
        response.data.job_types.forEach((job: JobMetadata) => {
          this.jobTypeMap.set(job.value, job);
          // Also map schema value if different
          if (job.schema_value !== job.value) {
            this.jobTypeMap.set(job.schema_value, job);
          }
        });
        return response.data;
      })
      .finally(() => {
        this.metadataPromise = null;
      });

    return this.metadataPromise as Promise<JobMetadataResponse>;
  }

  /**
   * Get metadata for a specific job type.
   */
  getJobMetadata(jobType: string): JobMetadata | undefined {
    return this.jobTypeMap.get(jobType);
  }

  /**
   * Get the label for a job type.
   * Falls back to formatting the job type if metadata not found.
   */
  getJobLabel(jobType: string): string {
    const metadata = this.getJobMetadata(jobType);
    if (metadata) {
      return metadata.label;
    }
    // Fallback: format the job type
    return jobType.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  }

  /**
   * Get the color for a job type.
   */
  getJobColor(jobType: string): string {
    const metadata = this.getJobMetadata(jobType);
    if (metadata) {
      return metadata.color;
    }
    // Fallback logic
    if (jobType.includes('sync')) return 'blue';
    if (jobType.includes('analysis')) return 'green';
    if (jobType.includes('test')) return 'purple';
    return 'default';
  }

  /**
   * Get the description for a job type.
   */
  getJobDescription(jobType: string): string {
    const metadata = this.getJobMetadata(jobType);
    return metadata?.description || 'Unknown job type';
  }

  /**
   * Get the unit for a job type's progress display.
   */
  getJobUnit(jobType: string): string {
    const metadata = this.getJobMetadata(jobType);
    return metadata?.unit || '';
  }

  /**
   * Format job progress with appropriate units.
   */
  formatJobProgress(
    jobType: string,
    processed: number | undefined,
    total: number | undefined,
    progress: number
  ): string {
    if (
      total !== undefined &&
      total !== null &&
      processed !== undefined &&
      processed !== null
    ) {
      const unit = this.getJobUnit(jobType);
      const unitStr = unit ? ` ${unit}` : '';
      return `${processed} / ${total}${unitStr}`;
    }
    return `${Math.round(progress || 0)}%`;
  }

  /**
   * Get all job types grouped by category.
   */
  getJobsByCategory(): Map<string, JobMetadata[]> {
    const categories = new Map<string, JobMetadata[]>();

    if (!this.metadata) {
      return categories;
    }

    this.metadata.job_types.forEach((job) => {
      const category = job.category || 'Other';
      if (!categories.has(category)) {
        categories.set(category, []);
      }
      categories.get(category)!.push(job);
    });

    return categories;
  }

  /**
   * Check if a job type allows concurrent execution.
   */
  allowsConcurrent(jobType: string): boolean {
    const metadata = this.getJobMetadata(jobType);
    return metadata?.allow_concurrent || false;
  }

  /**
   * Check if a job type is a workflow job.
   */
  isWorkflow(jobType: string): boolean {
    const metadata = this.getJobMetadata(jobType);
    return metadata?.is_workflow || false;
  }
}

// Export singleton instance
export const jobMetadataService = new JobMetadataService();

// Export convenience functions that use the service
export const getJobTypeLabel = (type: string): string => {
  return jobMetadataService.getJobLabel(type);
};

export const getJobTypeColor = (type: string): string => {
  return jobMetadataService.getJobColor(type);
};

export const getJobTypeDescription = (type: string): string => {
  return jobMetadataService.getJobDescription(type);
};

export const formatJobProgress = (
  type: string,
  processed: number | undefined,
  total: number | undefined,
  progress: number
): string => {
  return jobMetadataService.formatJobProgress(type, processed, total, progress);
};
