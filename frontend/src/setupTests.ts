/* eslint-disable no-undef */
import '@testing-library/jest-dom';

// Mock dayjs
jest.mock('dayjs');

// Mock apiClient
jest.mock('@/services/apiClient');

// Mock job metadata service
jest.mock('@/services/jobMetadataService', () => ({
  jobMetadataService: {
    fetchMetadata: jest.fn().mockResolvedValue({
      job_types: [],
      categories: [],
    }),
    getJobLabel: jest.fn().mockImplementation((type: string) => {
      return type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
    }),
    getJobColor: jest.fn().mockReturnValue('blue'),
    getJobDescription: jest.fn().mockReturnValue('Mock description'),
    getJobMetadata: jest.fn().mockReturnValue(null),
    formatJobProgress: jest
      .fn()
      .mockImplementation((_type, processed, total, progress) => {
        if (processed !== undefined && total !== undefined) {
          return `${processed} / ${total}`;
        }
        return `${Math.round(progress || 0)}%`;
      }),
  },
}));

// Mock hooks
jest.mock('@/hooks/useRunningJobs');
jest.mock('@/hooks/useWebSocket');

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as unknown as typeof IntersectionObserver;

// Suppress console errors and warnings in tests
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: ReactDOM.render') ||
        args[0].includes('inside a test was not wrapped in act'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };

  console.warn = (...args) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('React Router Future Flag Warning')
    ) {
      return;
    }
    originalWarn.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});
