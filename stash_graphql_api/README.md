# Stash GraphQL API Schema

This directory contains a local copy of the Stash GraphQL schema files from the official Stash repository.

## Source

These schema files are copied from: https://github.com/stashapp/stash/tree/develop/graphql/schema

## Purpose

This local copy provides:
- Quick reference for the Stash GraphQL API structure
- Offline access to the schema definitions
- Integration with development tools that can utilize GraphQL schema files

## Structure

- `schema.graphql` - Main GraphQL schema file containing queries, mutations, and subscriptions
- `types/` - Directory containing all type definitions organized by domain:
  - Configuration types
  - Media types (scenes, images, galleries, performers, etc.)
  - Filter and query types
  - Plugin and scraper types
  - And more...

## Updates

To update these files with the latest schema changes, copy the files from the source repository linked above.