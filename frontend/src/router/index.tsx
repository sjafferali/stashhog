import { RouteObject } from 'react-router-dom';
import MainLayout from '@/layouts/MainLayout';
import Dashboard from '@/pages/Dashboard';
import SceneBrowser from '@/pages/scenes/SceneBrowser';
import SceneDetail from '@/pages/scenes/SceneDetail';
import Analysis from '@/pages/analysis/Analysis';
import PlanList from '@/pages/analysis/PlanList';
import PlanDetail from '@/pages/analysis/PlanDetail';
import JobMonitor from '@/pages/jobs/JobMonitor';
import RunJob from '@/pages/jobs/RunJob';
import Jobsv2 from '@/pages/jobs/Jobsv2';
import Settings from '@/pages/settings/Settings';
import SyncManagement from '@/pages/sync/SyncManagement';
import Scheduler from '@/pages/Scheduler';
import NotFound from '@/pages/NotFound';

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: 'scenes',
        children: [
          {
            index: true,
            element: <SceneBrowser />,
          },
          {
            path: ':id',
            element: <SceneDetail />,
          },
        ],
      },
      {
        path: 'analysis',
        children: [
          {
            index: true,
            element: <Analysis />,
          },
          {
            path: 'plans',
            children: [
              {
                index: true,
                element: <PlanList />,
              },
              {
                path: ':id',
                element: <PlanDetail />,
              },
            ],
          },
        ],
      },
      {
        path: 'jobs',
        children: [
          {
            index: true,
            element: <JobMonitor />,
          },
          {
            path: 'run',
            element: <RunJob />,
          },
          {
            path: 'v2',
            element: <Jobsv2 />,
          },
        ],
      },
      {
        path: 'settings',
        element: <Settings />,
      },
      {
        path: 'sync',
        element: <SyncManagement />,
      },
      {
        path: 'scheduler',
        element: <Scheduler />,
      },
    ],
  },
  {
    path: '*',
    element: <NotFound />,
  },
];
