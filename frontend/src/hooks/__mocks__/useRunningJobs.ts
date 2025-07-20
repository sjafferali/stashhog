export const useRunningJobs = () => ({
  runningJobs: [],
  runningCount: 0,
  isLoading: false,
  error: null,
  refetch: jest.fn(),
});
