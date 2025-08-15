import React from 'react';

interface ActiveJobsSectionProps {
  onCancel: (jobId: string) => Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
  onRefresh: () => void;
  className?: string;
}

const ActiveJobsSection: React.FC<ActiveJobsSectionProps> = ({ className }) => {
  // MINIMAL VERSION FOR DEBUGGING NAVIGATION ISSUE
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
      <h3>Active Jobs Section (Minimal Debug Version)</h3>
      <p>This is a minimal version to test navigation.</p>
      <p>
        If navigation works with this version, the issue is in the removed code.
      </p>
    </div>
  );
};

export default ActiveJobsSection;
