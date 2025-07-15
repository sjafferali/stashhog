const { TextEncoder, TextDecoder } = require('util');

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Mock import.meta.env
global.importMetaEnv = {
  VITE_API_URL: 'http://localhost:8000',
  VITE_WS_URL: 'ws://localhost:8000',
  MODE: 'test',
  DEV: false,
  PROD: false,
  SSR: false,
};

// Replace import.meta.env references
Object.defineProperty(globalThis, 'import', {
  value: {
    meta: {
      env: global.importMetaEnv
    }
  }
});
