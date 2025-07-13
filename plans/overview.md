# StashHog Application Overview

## Introduction

StashHog is a web-based metadata management application designed to work with Stash, a popular open-source media organizer. It provides an intuitive interface for analyzing, managing, and enhancing metadata for media scenes stored in a Stash server.

## Purpose and Goals

### Primary Purpose
StashHog automates the tedious process of maintaining accurate metadata for large media collections. It leverages AI technology to analyze scenes and suggest appropriate metadata updates, while providing users full control over what changes are applied.

### Key Goals
1. **Automation**: Reduce manual effort in metadata management
2. **Accuracy**: Use AI to improve metadata quality
3. **Control**: Give users full visibility and control over changes
4. **Efficiency**: Handle large collections with batch processing
5. **Integration**: Seamless integration with existing Stash servers

## Target Users

- **Media Collectors**: Individuals managing personal media libraries
- **Content Creators**: Studios organizing their content
- **Archivists**: Organizations maintaining media archives
- **Stash Users**: Anyone currently using Stash who wants better metadata management

## Core Functionality

### 1. Scene Synchronization
StashHog maintains a local cache of scene data from your Stash server, including:
- Basic metadata (title, dates, paths)
- Relationships (performers, tags, studios)
- Organization status
- Custom details

### 2. Intelligent Analysis
Using OpenAI's language models, StashHog can:
- Detect studios from file paths and naming patterns
- Identify performers and normalize their names
- Suggest relevant tags based on content
- Generate detailed descriptions
- Clean up existing metadata

### 3. Change Management
Before applying any changes, StashHog:
- Shows a detailed diff of proposed changes
- Allows individual change approval/rejection
- Maintains a history of changes
- Supports bulk operations
- Enables rollback if needed

### 4. Task Automation
Schedule regular tasks such as:
- Daily synchronization with Stash
- Weekly metadata analysis
- Custom analysis rules
- Batch processing during off-hours

## Technical Architecture

### Backend (Python/FastAPI)
The backend provides a RESTful API with the following responsibilities:
- **Data Management**: Stores cached scene data and analysis results
- **Stash Integration**: Communicates with Stash via GraphQL
- **AI Processing**: Interfaces with OpenAI for metadata analysis
- **Job Management**: Handles long-running tasks asynchronously
- **WebSocket Support**: Provides real-time updates to the frontend

### Frontend (React/TypeScript)
The frontend offers a modern, responsive interface featuring:
- **Scene Browser**: Search, filter, and view scenes
- **Analysis Dashboard**: Review and apply proposed changes
- **Task Manager**: Monitor running jobs and schedules
- **Settings Panel**: Configure connections and preferences
- **Diff Viewer**: Visual comparison of metadata changes

### Database (SQLite)
A lightweight, embedded database storing:
- Cached scene metadata
- Analysis plans and results
- Job queue and history
- User settings
- Scheduled tasks

## Key Technologies

### Backend Stack
- **FastAPI**: Modern Python web framework with async support
- **SQLAlchemy**: SQL toolkit and ORM
- **Pydantic**: Data validation using Python type annotations
- **stashapi**: Python client for Stash's GraphQL API
- **OpenAI SDK**: For AI-powered analysis
- **APScheduler**: In-process task scheduling

### Frontend Stack
- **React 18**: UI library with hooks and concurrent features
- **TypeScript**: Type-safe JavaScript
- **Ant Design**: Enterprise-class UI components
- **Zustand**: Lightweight state management
- **Vite**: Next-generation frontend tooling
- **Axios**: HTTP client for API communication

### Development Tools
- **Docker**: Containerization for easy deployment
- **GitHub Actions**: CI/CD automation
- **pytest/Jest**: Testing frameworks
- **ESLint/ruff**: Code quality tools
- **mypy**: Python type checking

## Getting Started

### Prerequisites
- Python 3.9 or higher
- Node.js 18 or higher
- A running Stash instance
- OpenAI API key (for AI features)

### Basic Setup
1. Clone the repository
2. Configure connection to your Stash server
3. Set up OpenAI API credentials
4. Run database migrations
5. Start the backend and frontend servers

### First Steps
1. Perform initial sync to import your scenes
2. Configure analysis preferences
3. Run your first analysis on a small batch
4. Review and apply suggested changes
5. Set up automated schedules

## Use Cases

### Scenario 1: New Media Import
When adding new media to Stash, StashHog can:
- Automatically detect and set the correct studio
- Identify performers from filenames
- Add appropriate tags
- Generate descriptions

### Scenario 2: Metadata Cleanup
For existing collections, StashHog can:
- Standardize performer names
- Remove duplicate tags
- Fill in missing information
- Correct formatting issues

### Scenario 3: Bulk Organization
For large operations, StashHog can:
- Process thousands of scenes in batches
- Apply rule-based updates
- Generate reports on changes
- Schedule processing during off-hours

## Benefits

### Time Savings
- Reduce hours of manual tagging to minutes
- Batch process entire collections
- Automate repetitive tasks

### Improved Quality
- Consistent metadata across your collection
- AI-powered suggestions reduce errors
- Standardized naming and tagging

### Full Control
- Review all changes before applying
- Selective application of updates
- Complete audit trail
- Easy rollback options

## Future Vision

StashHog aims to become the go-to tool for Stash metadata management by:
- Adding plugin support for custom analyzers
- Implementing collaborative features
- Supporting additional AI providers
- Expanding language support
- Building a community marketplace for analysis rules

## Summary

StashHog bridges the gap between Stash's powerful media organization capabilities and the need for accurate, comprehensive metadata. By combining AI technology with user control, it makes managing large media collections both efficient and enjoyable.