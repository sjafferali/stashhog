import { render, screen } from '@testing-library/react';
import App from './App';

describe('App Component', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(screen.getByText('StashHog')).toBeInTheDocument();
  });

  it('renders the welcome message', () => {
    render(<App />);
    expect(screen.getByText('Welcome to StashHog')).toBeInTheDocument();
  });

  it('renders the tagline', () => {
    render(<App />);
    expect(
      screen.getByText('AI-powered content tagging and organization for Stash')
    ).toBeInTheDocument();
  });

  it('renders the footer', () => {
    render(<App />);
    const currentYear = new Date().getFullYear();
    expect(screen.getByText(`StashHog ©${currentYear}`)).toBeInTheDocument();
  });
});