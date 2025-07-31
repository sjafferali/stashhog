import React, { useState } from 'react';
import { message } from 'antd';
import RunJobForm from '../Scheduler/components/RunJobForm';

const RunJob: React.FC = () => {
  const [lastJobId, setLastJobId] = useState<string | null>(null);

  const handleRunJobSuccess = (jobId: string) => {
    setLastJobId(jobId);
    message.success(`Job ${jobId} started successfully!`);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <RunJobForm onSuccess={handleRunJobSuccess} />
      {lastJobId && (
        <div style={{ marginTop: '16px', color: '#888' }}>
          Last job started: {lastJobId}
        </div>
      )}
    </div>
  );
};

export default RunJob;
