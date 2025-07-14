import React, { Component, ReactNode } from 'react';
import { Result, Button } from 'antd';
import { HomeOutlined, ReloadOutlined } from '@ant-design/icons';

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    
    // Log to external service if needed
    if (process.env.NODE_ENV === 'production') {
      // logErrorToService(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const { error } = this.state;
      const { fallback } = this.props;

      if (fallback) {
        return fallback(error!, this.handleReset);
      }

      return (
        <Result
          status="error"
          title="Something went wrong"
          subTitle={error?.message || 'An unexpected error occurred'}
          extra={[
            <Button 
              key="reset"
              type="primary" 
              icon={<ReloadOutlined />}
              onClick={this.handleReset}
            >
              Try Again
            </Button>,
            <Button 
              key="home"
              icon={<HomeOutlined />}
              onClick={this.handleGoHome}
            >
              Back to Home
            </Button>
          ]}
        />
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;