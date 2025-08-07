/**
 * AppInitializer component that loads essential metadata on app startup.
 * This ensures job metadata is available throughout the application.
 */

import React, { useEffect } from 'react';
import { useJobMetadata } from '../hooks/useJobMetadata';

interface AppInitializerProps {
  children: React.ReactNode;
}

export const AppInitializer: React.FC<AppInitializerProps> = ({ children }) => {
  const { error } = useJobMetadata();

  useEffect(() => {
    if (error) {
      console.warn(
        'Job metadata failed to load, using static fallbacks:',
        error
      );
      // The app can continue with static fallbacks
    }
  }, [error]);

  // We don't block the app from loading even if metadata fails
  // The static fallbacks in jobUtils will be used
  return <>{children}</>;
};
