import { Dayjs } from 'dayjs';

interface DayjsMock {
  (date?: string | number | Date | Dayjs | null | undefined): {
    format: jest.Mock<string>;
    fromNow: jest.Mock<string>;
    isValid: jest.Mock<boolean>;
    toISOString: jest.Mock<string>;
    valueOf: jest.Mock<number>;
  };
  extend: jest.Mock<void>;
}

const dayjs = jest.fn(
  (_date?: string | number | Date | Dayjs | null | undefined) => ({
    format: jest.fn(() => '2023-01-01'),
    fromNow: jest.fn(() => 'a few seconds ago'),
    isValid: jest.fn(() => true),
    toISOString: jest.fn(() => '2023-01-01T00:00:00.000Z'),
    valueOf: jest.fn(() => 1672531200000),
  })
) as unknown as DayjsMock;

// Add extend method to the mock
dayjs.extend = jest.fn();

export default dayjs;
