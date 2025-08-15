import React, { useState } from 'react';

interface Job {
  id: string;
  type: string;
  status: string;
  progress?: number;
}

interface ActiveJobsSectionProps {
  onCancel: (jobId: string) => Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
  onRefresh: () => void;
  className?: string;
}

const ActiveJobsSection: React.FC<ActiveJobsSectionProps> = ({ className }) => {
  // TEST 2: Adding useState to test if state management breaks navigation
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      className={className}
      style={{
        padding: 16,
        marginBottom: 16,
        border: '1px solid #d9d9d9',
        borderRadius: 4,
        backgroundColor: '#fff',
      }}
    >
      <h3>Test 2: With useState</h3>
      <p>Active Jobs: {activeJobs.length}</p>
      <p>Loading: {loading ? 'Yes' : 'No'}</p>
      <p>Collapsed: {collapsed ? 'Yes' : 'No'}</p>
      <button onClick={() => setCollapsed(!collapsed)}>Toggle Collapsed</button>
      <button
        onClick={() =>
          setActiveJobs([
            { id: '1', type: 'test', status: 'running', progress: 50 },
          ])
        }
      >
        Add Test Job
      </button>
      <button onClick={() => setLoading(!loading)}>Toggle Loading</button>
    </div>
  );
};

export default ActiveJobsSection;
