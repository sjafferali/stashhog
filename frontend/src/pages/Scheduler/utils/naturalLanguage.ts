interface TimePattern {
  pattern: RegExp;
  handler: (match: RegExpMatchArray) => string;
}

const TIME_PATTERNS: TimePattern[] = [
  // Every X minutes
  {
    pattern: /every (\d+) minutes?/i,
    handler: (match) => `*/${match[1]} * * * *`,
  },
  // Every X hours
  {
    pattern: /every (\d+) hours?/i,
    handler: (match) => `0 */${match[1]} * * *`,
  },
  // Every hour
  {
    pattern: /every hour/i,
    handler: () => '0 * * * *',
  },
  // Every day at specific time
  {
    pattern: /every day at (\d{1,2}):?(\d{2})?\s*(am|pm)?/i,
    handler: (match) => {
      let hour = parseInt(match[1]);
      const minute = match[2] ? parseInt(match[2]) : 0;
      const meridiem = match[3]?.toLowerCase();

      if (meridiem === 'pm' && hour < 12) hour += 12;
      if (meridiem === 'am' && hour === 12) hour = 0;

      return `${minute} ${hour} * * *`;
    },
  },
  // Daily at midnight
  {
    pattern: /daily at midnight|every day at midnight/i,
    handler: () => '0 0 * * *',
  },
  // Daily at noon
  {
    pattern: /daily at noon|every day at noon/i,
    handler: () => '0 12 * * *',
  },
  // Every weekday
  {
    pattern: /every weekday|weekdays only/i,
    handler: () => '0 9 * * 1-5',
  },
  // Every weekend
  {
    pattern: /every weekend|weekends only/i,
    handler: () => '0 9 * * 0,6',
  },
  // Every specific day of week
  {
    pattern:
      /every (monday|tuesday|wednesday|thursday|friday|saturday|sunday)/i,
    handler: (match) => {
      const days: Record<string, number> = {
        sunday: 0,
        monday: 1,
        tuesday: 2,
        wednesday: 3,
        thursday: 4,
        friday: 5,
        saturday: 6,
      };
      const day = days[match[1].toLowerCase()];
      return `0 0 * * ${day}`;
    },
  },
  // Specific day at time
  {
    pattern:
      /(monday|tuesday|wednesday|thursday|friday|saturday|sunday)s? at (\d{1,2}):?(\d{2})?\s*(am|pm)?/i,
    handler: (match) => {
      const days: Record<string, number> = {
        sunday: 0,
        monday: 1,
        tuesday: 2,
        wednesday: 3,
        thursday: 4,
        friday: 5,
        saturday: 6,
      };
      const day = days[match[1].toLowerCase()];
      let hour = parseInt(match[2]);
      const minute = match[3] ? parseInt(match[3]) : 0;
      const meridiem = match[4]?.toLowerCase();

      if (meridiem === 'pm' && hour < 12) hour += 12;
      if (meridiem === 'am' && hour === 12) hour = 0;

      return `${minute} ${hour} * * ${day}`;
    },
  },
  // Monthly on specific day
  {
    pattern: /monthly on the (\d{1,2})(st|nd|rd|th)?/i,
    handler: (match) => {
      const day = parseInt(match[1]);
      return `0 0 ${day} * *`;
    },
  },
  // Every month on the first
  {
    pattern: /every month on the first|monthly on the first/i,
    handler: () => '0 0 1 * *',
  },
  // Every month on the last day
  {
    pattern: /every month on the last day|last day of every month/i,
    handler: () => '0 0 L * *',
  },
  // Twice a day
  {
    pattern: /twice a day|twice daily/i,
    handler: () => '0 0,12 * * *',
  },
  // Three times a day
  {
    pattern: /three times a day|thrice daily/i,
    handler: () => '0 0,8,16 * * *',
  },
  // Every X days
  {
    pattern: /every (\d+) days?/i,
    handler: (match) => `0 0 */${match[1]} * *`,
  },
  // At specific times
  {
    pattern: /at (\d{1,2}):?(\d{2})?\s*(am|pm)?/i,
    handler: (match) => {
      let hour = parseInt(match[1]);
      const minute = match[2] ? parseInt(match[2]) : 0;
      const meridiem = match[3]?.toLowerCase();

      if (meridiem === 'pm' && hour < 12) hour += 12;
      if (meridiem === 'am' && hour === 12) hour = 0;

      return `${minute} ${hour} * * *`;
    },
  },
  // Every morning
  {
    pattern: /every morning/i,
    handler: () => '0 6 * * *',
  },
  // Every evening
  {
    pattern: /every evening/i,
    handler: () => '0 18 * * *',
  },
  // Every night
  {
    pattern: /every night/i,
    handler: () => '0 22 * * *',
  },
  // Business hours
  {
    pattern: /business hours|during business hours/i,
    handler: () => '0 9-17 * * 1-5',
  },
  // After hours
  {
    pattern: /after hours|outside business hours/i,
    handler: () => '0 18-8 * * *',
  },
];

export function parseNaturalLanguage(input: string): string | null {
  const normalizedInput = input.trim().toLowerCase();

  for (const { pattern, handler } of TIME_PATTERNS) {
    const match = normalizedInput.match(pattern);
    if (match) {
      try {
        return handler(match);
      } catch (error) {
        console.error('Error parsing natural language:', error);
      }
    }
  }

  return null;
}

export function suggestNaturalLanguageExamples(input: string): string[] {
  const suggestions = [
    'every hour',
    'every day at 3am',
    'every Monday at 9am',
    'twice a day',
    'every weekday',
    'monthly on the 1st',
    'every 30 minutes',
  ];

  if (!input) return suggestions.slice(0, 5);

  const normalizedInput = input.toLowerCase();
  return suggestions
    .filter((s) => s.toLowerCase().includes(normalizedInput))
    .slice(0, 5);
}
