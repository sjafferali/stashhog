import { useEffect } from 'react';
import { useRoutes } from 'react-router-dom';
import { message } from 'antd';
import { routes } from './router';
import useAppStore from './store';

function App() {
  const routing = useRoutes(routes);
  const { notification, setNotification, loadSettings, isLoaded } =
    useAppStore();

  // Load settings on app initialization
  useEffect(() => {
    if (!isLoaded) {
      void loadSettings();
    }
  }, [isLoaded, loadSettings]);

  useEffect(() => {
    if (notification) {
      const { type, content } = notification;
      void message[type](content);
      setNotification(null);
    }
  }, [notification, setNotification]);

  return <>{routing}</>;
}

export default App;
