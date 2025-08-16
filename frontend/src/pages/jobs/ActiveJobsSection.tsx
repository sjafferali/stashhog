import React, { useState, useEffect } from 'react';

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
  // TEST 3: Adding useEffect to test if lifecycle hooks break navigation
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [mountTime, setMountTime] = useState<string>('');

  // Test useEffect on mount
  useEffect(() => {
    console.log('ActiveJobsSection mounted');
    setMountTime(new Date().toLocaleTimeString());

    // Cleanup function
    return () => {
      console.log('ActiveJobsSection unmounting');
    };
  }, []);

  // Test useEffect that depends on state
  useEffect(() => {
    console.log('Active jobs changed:', activeJobs.length);
  }, [activeJobs]);

  // Test useEffect that runs on every render
  useEffect(() => {
    console.log('Component rendered');
  });

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
      <h3>Test 3: With useState + useEffect</h3>
      <p>Mounted at: {mountTime}</p>
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
