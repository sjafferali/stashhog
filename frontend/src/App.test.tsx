import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act } from 'react';
import { routes } from './router';

describe('App Component', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  const renderApp = async () => {
    const router = createMemoryRouter(routes);

    let result;
    await act(async () => {
      result = render(
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      );
    });
    return result!;
  };

  it('renders without crashing', async () => {
    const { container } = await renderApp();
    expect(container).toBeInTheDocument();
  });

  it('renders the sidebar with logo', async () => {
    await renderApp();
    await waitFor(() => {
      expect(screen.getByText('StashHog')).toBeInTheDocument();
    });
  });

  it('renders the navigation menu', async () => {
    await renderApp();
    await waitFor(() => {
      expect(screen.getAllByText('Dashboard')[0]).toBeInTheDocument();
      // Library menu now contains Scenes, Performers, Tags, and Studios
      expect(screen.getByText('Library')).toBeInTheDocument();
    });

    // Click on Library menu to expand it
    const user = userEvent.setup();
    const libraryMenu = screen.getByText('Library');
    await user.click(libraryMenu);

    // Now check for the submenu items - use getAllByText since these might appear in multiple places
    await waitFor(() => {
      expect(screen.getByText('Scenes')).toBeInTheDocument();
      // Use getAllByText for items that might appear in multiple places (menu and dashboard)
      expect(screen.getAllByText('Performers')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Tags')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Studios')[0]).toBeInTheDocument();
    });
  });

  it('renders the footer', async () => {
    await renderApp();
    const currentYear = new Date().getFullYear();
    await waitFor(() => {
      expect(
        screen.getByText(new RegExp(`StashHog ©${currentYear}`))
      ).toBeInTheDocument();
    });
  });
});
