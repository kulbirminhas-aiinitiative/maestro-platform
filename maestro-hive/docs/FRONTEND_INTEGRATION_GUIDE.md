# Frontend Integration Guide: Tri-Modal Mission Control

**Version**: 2.0.0
**Date**: 2025-10-13
**GraphQL API**: http://localhost:8000/graphql
**WebSocket**: ws://localhost:8000/graphql

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Apollo Client Setup](#apollo-client-setup)
4. [GraphQL Queries](#graphql-queries)
5. [React Hooks](#react-hooks)
6. [TypeScript Types](#typescript-types)
7. [Component Examples](#component-examples)
8. [Real-Time Subscriptions](#real-time-subscriptions)
9. [Error Handling](#error-handling)
10. [Performance Optimization](#performance-optimization)
11. [Testing](#testing)

---

## Overview

The Tri-Modal Mission Control frontend provides 4 key lenses into the system:

1. **Events Lens**: DDE/BDV/ACC event streams
2. **Correlations Lens**: Cross-stream correlation network
3. **Graph Lens**: Neo4j graph visualization with time-travel
4. **Deployment Lens**: Contract stars (deployment readiness)

**Deployment Rule**: Deploy ONLY when DDE ✅ AND BDV ✅ AND ACC ✅

---

## Prerequisites

### Required Packages

```bash
# Core dependencies
npm install @apollo/client graphql

# WebSocket for subscriptions
npm install graphql-ws

# Graph visualization
npm install cytoscape cytoscape-dom-node react-cytoscapejs

# UI components (if using)
npm install @tanstack/react-query lucide-react

# Dev dependencies
npm install --save-dev @graphql-codegen/cli @graphql-codegen/typescript @graphql-codegen/typescript-operations @graphql-codegen/typescript-react-apollo
```

### GraphQL CodeGen Configuration

Create `codegen.yml`:

```yaml
overwrite: true
schema: "http://localhost:8000/graphql"
documents: "src/**/*.graphql"
generates:
  src/generated/graphql.ts:
    plugins:
      - "typescript"
      - "typescript-operations"
      - "typescript-react-apollo"
    config:
      withHooks: true
      withComponent: false
      withHOC: false
```

Add to `package.json`:

```json
{
  "scripts": {
    "codegen": "graphql-codegen --config codegen.yml"
  }
}
```

---

## Apollo Client Setup

### 1. Create Apollo Client Instance

**File**: `src/lib/apolloClient.ts`

```typescript
import {
  ApolloClient,
  InMemoryCache,
  HttpLink,
  split,
  from,
} from '@apollo/client';
import { GraphQLWsLink } from '@apollo/client/link/subscriptions';
import { getMainDefinition } from '@apollo/client/utilities';
import { createClient } from 'graphql-ws';
import { onError } from '@apollo/client/link/error';

// HTTP connection for queries and mutations
const httpLink = new HttpLink({
  uri: import.meta.env.VITE_GRAPHQL_HTTP_URL || 'http://localhost:8000/graphql',
});

// WebSocket connection for subscriptions
const wsLink = new GraphQLWsLink(
  createClient({
    url: import.meta.env.VITE_GRAPHQL_WS_URL || 'ws://localhost:8000/graphql',
    connectionParams: {
      // Add auth token if needed
      // authToken: localStorage.getItem('token'),
    },
  })
);

// Error handling link
const errorLink = onError(({ graphQLErrors, networkError }) => {
  if (graphQLErrors) {
    graphQLErrors.forEach(({ message, locations, path }) =>
      console.error(
        `[GraphQL error]: Message: ${message}, Location: ${locations}, Path: ${path}`
      )
    );
  }

  if (networkError) {
    console.error(`[Network error]: ${networkError}`);
  }
});

// Split traffic based on operation type
const splitLink = split(
  ({ query }) => {
    const definition = getMainDefinition(query);
    return (
      definition.kind === 'OperationDefinition' &&
      definition.operation === 'subscription'
    );
  },
  wsLink,  // Use WebSocket for subscriptions
  httpLink // Use HTTP for queries and mutations
);

// Create Apollo Client
export const apolloClient = new ApolloClient({
  link: from([errorLink, splitLink]),
  cache: new InMemoryCache({
    typePolicies: {
      Query: {
        fields: {
          ddeEvents: {
            // Relay-style pagination
            keyArgs: ['filter'],
            merge(existing, incoming) {
              if (!existing) return incoming;
              return {
                ...incoming,
                edges: [...existing.edges, ...incoming.edges],
              };
            },
          },
          bdvEvents: {
            keyArgs: ['filter'],
            merge(existing, incoming) {
              if (!existing) return incoming;
              return {
                ...incoming,
                edges: [...existing.edges, ...incoming.edges],
              };
            },
          },
          accEvents: {
            keyArgs: ['filter'],
            merge(existing, incoming) {
              if (!existing) return incoming;
              return {
                ...incoming,
                edges: [...existing.edges, ...incoming.edges],
              };
            },
          },
        },
      },
    },
  }),
  defaultOptions: {
    watchQuery: {
      fetchPolicy: 'cache-and-network',
      errorPolicy: 'all',
    },
    query: {
      fetchPolicy: 'network-only',
      errorPolicy: 'all',
    },
  },
});
```

### 2. Wrap App with ApolloProvider

**File**: `src/main.tsx`

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ApolloProvider } from '@apollo/client';
import { apolloClient } from './lib/apolloClient';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ApolloProvider client={apolloClient}>
      <App />
    </ApolloProvider>
  </React.StrictMode>
);
```

---

## GraphQL Queries

### Events Lens Queries

**File**: `src/graphql/events.graphql`

```graphql
# Query recent DDE events
query GetRecentDDEEvents(
  $iterationId: ID
  $eventType: DDEEventType
  $contractId: String
  $first: Int
  $after: String
) {
  ddeEvents(
    filter: {
      iterationId: $iterationId
      eventType: $eventType
      contractId: $contractId
    }
    pagination: { first: $first, after: $after }
  ) {
    edges {
      node {
        eventId
        iterationId
        timestamp
        workflowId
        eventType
        nodeId
        nodeType
        nodeStatus
        contractId
        qualityGatePassed
        traceId
        correlations {
          linkId
          targetStream
          confidence {
            value
            provenance
            reasoning
          }
        }
      }
      cursor
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
    totalCount
  }
}

# Query BDV events
query GetRecentBDVEvents(
  $iterationId: ID
  $scenarioStatus: BDVScenarioStatus
  $contractTags: [String!]
  $first: Int
  $after: String
) {
  bdvEvents(
    filter: {
      iterationId: $iterationId
      scenarioStatus: $scenarioStatus
      contractTags: $contractTags
    }
    pagination: { first: $first, after: $after }
  ) {
    edges {
      node {
        eventId
        iterationId
        timestamp
        eventType
        scenarioId
        scenarioName
        scenarioStatus
        contractTags
        durationMs
        traceId
        correlations {
          linkId
          targetStream
          confidence {
            value
          }
        }
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
    totalCount
  }
}

# Query ACC events
query GetRecentACCEvents(
  $iterationId: ID
  $violationType: ACCViolationType
  $violationSeverity: ACCViolationSeverity
  $first: Int
  $after: String
) {
  accEvents(
    filter: {
      iterationId: $iterationId
      violationType: $violationType
      violationSeverity: $violationSeverity
    }
    pagination: { first: $first, after: $after }
  ) {
    edges {
      node {
        eventId
        iterationId
        timestamp
        eventType
        modulePath
        violationType
        violationSeverity
        violationMessage
        totalViolations
        blockingViolations
        traceId
        correlations {
          linkId
          targetStream
        }
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
    totalCount
  }
}
```

### Correlations Lens Queries

```graphql
# Query correlation links
query GetCorrelations(
  $iterationId: ID
  $sourceStream: String
  $targetStream: String
  $minConfidence: Float
  $first: Int
  $after: String
) {
  correlations(
    filter: {
      iterationId: $iterationId
      sourceStream: $sourceStream
      targetStream: $targetStream
      minConfidence: $minConfidence
    }
    pagination: { first: $first, after: $after }
  ) {
    edges {
      node {
        linkId
        sourceStream
        sourceEventId
        sourceEntityId
        targetStream
        targetEventId
        targetEntityId
        confidence {
          value
          provenance
          reasoning
          createdAt
        }
        linkType
        iterationId
        createdAt
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
    totalCount
  }
}
```

### Deployment Lens Queries

```graphql
# Query contract stars (deployment readiness)
query GetContractStars(
  $iterationId: ID
  $isValid: Boolean
  $first: Int
  $after: String
) {
  contractStars(
    filter: {
      iterationId: $iterationId
      isValid: $isValid
    }
    pagination: { first: $first, after: $after }
  ) {
    edges {
      node {
        contractId
        iterationId

        # DDE side
        ddeInterfaceNodeId
        ddeContractLocked
        ddeContractValidated

        # BDV side
        bdvContractTag
        bdvScenarios
        bdvAllPassed

        # ACC side
        accComponentBoundary
        accViolations
        accClean

        # Deployment readiness
        isComplete
        isValid

        createdAt
        updatedAt
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
    totalCount
  }
}

# Query single contract star
query GetContractStar($contractId: String!, $iterationId: ID!) {
  contractStar(contractId: $contractId, iterationId: $iterationId) {
    contractId
    iterationId
    ddeInterfaceNodeId
    ddeContractLocked
    ddeContractValidated
    bdvContractTag
    bdvScenarios
    bdvAllPassed
    accComponentBoundary
    accViolations
    accClean
    isComplete
    isValid
    createdAt
    updatedAt
  }
}
```

### Graph Lens Queries

```graphql
# Time-travel query
query GetGraphAtTime(
  $iterationId: ID!
  $asOfTime: DateTime!
  $systemKnewBy: DateTime
) {
  graphAtTime(
    iterationId: $iterationId
    asOfTime: $asOfTime
    systemKnewBy: $systemKnewBy
  ) {
    iterationId
    snapshotTime
    nodes {
      nodeId
      iterationId
      nodeType
      validFrom
      validTo
      observedAt
      properties
    }
    edges {
      edgeId
      iterationId
      sourceNodeId
      targetNodeId
      edgeType
      validFrom
      validTo
      observedAt
      properties
    }
    nodeCount
    edgeCount
  }
}

# Query graph nodes
query GetGraphNodes(
  $iterationId: ID
  $nodeType: NodeTypeEnum
  $first: Int
  $after: String
) {
  graphNodes(
    filter: {
      iterationId: $iterationId
      nodeType: $nodeType
    }
    pagination: { first: $first, after: $after }
  ) {
    edges {
      node {
        nodeId
        iterationId
        nodeType
        validFrom
        validTo
        observedAt
        properties
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
    totalCount
  }
}
```

### Statistics Queries

```graphql
# System statistics
query GetSystemStats {
  systemStats {
    totalEvents
    totalCorrelations
    totalContractStars
    eventsByStream
    correlationRate
    throughput {
      eventsPerSecond
      correlationsPerSecond
    }
    latency {
      p50Ms
      p95Ms
      p99Ms
    }
  }
}

# Iteration statistics
query GetIterationStats($iterationId: ID!) {
  iterationStats(iterationId: $iterationId) {
    iterationId
    totalEvents
    ddeEvents
    bdvEvents
    accEvents
    correlations
    contractStars
    contractStarsValid
    startedAt
    completedAt
    durationSeconds
  }
}

# Health check
query GetHealth {
  health {
    status
    timestamp
    services {
      name
      status
      latencyMs
      error
    }
  }
}
```

---

## React Hooks

### Custom Hook: useEvents

**File**: `src/hooks/useEvents.ts`

```typescript
import { useQuery } from '@apollo/client';
import { GET_RECENT_DDE_EVENTS } from '../graphql/events.graphql';

export function useDDEEvents(
  iterationId?: string,
  eventType?: string,
  contractId?: string,
  first: number = 50
) {
  const { data, loading, error, fetchMore, refetch } = useQuery(
    GET_RECENT_DDE_EVENTS,
    {
      variables: {
        iterationId,
        eventType,
        contractId,
        first,
      },
      pollInterval: 5000, // Poll every 5 seconds for updates
    }
  );

  const loadMore = () => {
    if (!data?.ddeEvents.pageInfo.hasNextPage) return;

    fetchMore({
      variables: {
        after: data.ddeEvents.pageInfo.endCursor,
      },
    });
  };

  return {
    events: data?.ddeEvents.edges.map(edge => edge.node) || [],
    totalCount: data?.ddeEvents.totalCount || 0,
    hasMore: data?.ddeEvents.pageInfo.hasNextPage || false,
    loading,
    error,
    loadMore,
    refetch,
  };
}
```

### Custom Hook: useContractStars

**File**: `src/hooks/useContractStars.ts`

```typescript
import { useQuery } from '@apollo/client';
import { GET_CONTRACT_STARS } from '../graphql/deployment.graphql';

export function useContractStars(
  iterationId?: string,
  isValid?: boolean,
  first: number = 50
) {
  const { data, loading, error, refetch } = useQuery(GET_CONTRACT_STARS, {
    variables: {
      iterationId,
      isValid,
      first,
    },
    pollInterval: 10000, // Poll every 10 seconds
  });

  const stars = data?.contractStars.edges.map(edge => edge.node) || [];

  // Calculate deployment readiness stats
  const readyToDeploy = stars.filter(star => star.isValid).length;
  const notReady = stars.filter(star => !star.isValid).length;

  return {
    stars,
    totalCount: data?.contractStars.totalCount || 0,
    readyToDeploy,
    notReady,
    loading,
    error,
    refetch,
  };
}
```

### Custom Hook: useGraphSnapshot

**File**: `src/hooks/useGraphSnapshot.ts`

```typescript
import { useQuery } from '@apollo/client';
import { GET_GRAPH_AT_TIME } from '../graphql/graph.graphql';

export function useGraphSnapshot(
  iterationId: string,
  asOfTime: Date,
  systemKnewBy?: Date
) {
  const { data, loading, error, refetch } = useQuery(GET_GRAPH_AT_TIME, {
    variables: {
      iterationId,
      asOfTime: asOfTime.toISOString(),
      systemKnewBy: systemKnewBy?.toISOString(),
    },
    skip: !iterationId || !asOfTime,
  });

  return {
    snapshot: data?.graphAtTime,
    nodes: data?.graphAtTime?.nodes || [],
    edges: data?.graphAtTime?.edges || [],
    nodeCount: data?.graphAtTime?.nodeCount || 0,
    edgeCount: data?.graphAtTime?.edgeCount || 0,
    loading,
    error,
    refetch,
  };
}
```

---

## Real-Time Subscriptions

### Subscription Queries

**File**: `src/graphql/subscriptions.graphql`

```graphql
# Subscribe to DDE events
subscription OnDDEEventCreated($iterationId: ID) {
  ddeEventCreated(iterationId: $iterationId) {
    eventId
    iterationId
    timestamp
    eventType
    contractId
    nodeStatus
    traceId
  }
}

# Subscribe to contract star creation
subscription OnContractStarCreated($iterationId: ID) {
  contractStarCreated(iterationId: $iterationId) {
    contractId
    iterationId
    isValid
    ddeContractValidated
    bdvAllPassed
    accClean
    createdAt
  }
}

# Subscribe to contract star updates
subscription OnContractStarUpdated($contractId: ID, $iterationId: ID) {
  contractStarUpdated(contractId: $contractId, iterationId: $iterationId) {
    contractId
    iterationId
    isValid
    ddeContractValidated
    bdvAllPassed
    accClean
    updatedAt
  }
}
```

### Using Subscriptions in Components

```typescript
import { useSubscription } from '@apollo/client';
import { ON_DDE_EVENT_CREATED } from '../graphql/subscriptions.graphql';

export function EventsLensRealTime({ iterationId }: { iterationId: string }) {
  const { data, loading, error } = useSubscription(ON_DDE_EVENT_CREATED, {
    variables: { iterationId },
  });

  React.useEffect(() => {
    if (data?.ddeEventCreated) {
      console.log('New DDE event:', data.ddeEventCreated);
      // Update UI, show notification, etc.
    }
  }, [data]);

  // ... rest of component
}
```

---

## Component Examples

### EventCard Component

**File**: `src/components/EventCard.tsx`

```typescript
import React from 'react';
import { DDEEvent, BDVEvent, ACCEvent } from '../generated/graphql';

interface EventCardProps {
  event: DDEEvent | BDVEvent | ACCEvent;
  type: 'DDE' | 'BDV' | 'ACC';
}

export function EventCard({ event, type }: EventCardProps) {
  const getTypeColor = () => {
    switch (type) {
      case 'DDE':
        return 'bg-blue-100 text-blue-800';
      case 'BDV':
        return 'bg-green-100 text-green-800';
      case 'ACC':
        return 'bg-red-100 text-red-800';
    }
  };

  return (
    <div className="border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-2">
        <span className={`px-2 py-1 rounded text-xs font-semibold ${getTypeColor()}`}>
          {type}
        </span>
        <span className="text-xs text-gray-500">
          {new Date(event.timestamp).toLocaleString()}
        </span>
      </div>

      <h3 className="font-semibold text-sm mb-1">{event.eventId}</h3>

      {'contractId' in event && event.contractId && (
        <p className="text-sm text-gray-600">
          Contract: <span className="font-mono">{event.contractId}</span>
        </p>
      )}

      {'eventType' in event && (
        <p className="text-sm text-gray-600">Type: {event.eventType}</p>
      )}

      {event.correlations && event.correlations.length > 0 && (
        <div className="mt-2 pt-2 border-t">
          <p className="text-xs text-gray-500">
            {event.correlations.length} correlation(s)
          </p>
        </div>
      )}
    </div>
  );
}
```

### ContractStarCard Component

**File**: `src/components/ContractStarCard.tsx`

```typescript
import React from 'react';
import { ContractStar } from '../generated/graphql';
import { CheckCircle, XCircle, Clock } from 'lucide-react';

interface ContractStarCardProps {
  star: ContractStar;
  onDeploy?: (contractId: string) => void;
}

export function ContractStarCard({ star, onDeploy }: ContractStarCardProps) {
  const StatusIcon = ({ passed }: { passed: boolean }) =>
    passed ? (
      <CheckCircle className="w-5 h-5 text-green-500" />
    ) : (
      <XCircle className="w-5 h-5 text-red-500" />
    );

  const canDeploy = star.isValid;

  return (
    <div className="border rounded-lg p-6 shadow-sm">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-bold text-lg">{star.contractId}</h3>
          <p className="text-sm text-gray-500">
            {star.isComplete ? 'Complete' : 'Incomplete'}
          </p>
        </div>

        {canDeploy ? (
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-semibold">
            ✅ Ready
          </span>
        ) : (
          <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-semibold">
            ⚠️ Not Ready
          </span>
        )}
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <StatusIcon passed={star.ddeContractValidated} />
          <span className="text-sm">
            DDE: Contract Validated
          </span>
        </div>

        <div className="flex items-center gap-2">
          <StatusIcon passed={star.bdvAllPassed} />
          <span className="text-sm">
            BDV: All Scenarios Passed ({star.bdvScenarios.length} scenarios)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <StatusIcon passed={star.accClean} />
          <span className="text-sm">
            ACC: Clean Architecture ({star.accViolations.length} violations)
          </span>
        </div>
      </div>

      {onDeploy && (
        <button
          onClick={() => onDeploy(star.contractId)}
          disabled={!canDeploy}
          className={`
            mt-4 w-full py-2 px-4 rounded font-semibold transition-colors
            ${
              canDeploy
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }
          `}
        >
          {canDeploy ? '🚀 Deploy' : '⏳ Not Ready to Deploy'}
        </button>
      )}

      <div className="mt-4 pt-4 border-t text-xs text-gray-500">
        <p>Created: {new Date(star.createdAt).toLocaleString()}</p>
        <p>Updated: {new Date(star.updatedAt).toLocaleString()}</p>
      </div>
    </div>
  );
}
```

---

## Error Handling

### Global Error Boundary

```typescript
import React from 'react';
import { ApolloError } from '@apollo/client';

interface Props {
  error?: ApolloError;
  onRetry?: () => void;
}

export function ErrorDisplay({ error, onRetry }: Props) {
  if (!error) return null;

  const isNetworkError = error.networkError;
  const hasGraphQLErrors = error.graphQLErrors && error.graphQLErrors.length > 0;

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <h3 className="text-red-800 font-semibold mb-2">
        {isNetworkError ? 'Network Error' : 'GraphQL Error'}
      </h3>

      {hasGraphQLErrors && (
        <ul className="list-disc list-inside text-red-700 text-sm mb-2">
          {error.graphQLErrors.map((err, i) => (
            <li key={i}>{err.message}</li>
          ))}
        </ul>
      )}

      {isNetworkError && (
        <p className="text-red-700 text-sm mb-2">
          Unable to connect to GraphQL server. Please check your connection.
        </p>
      )}

      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      )}
    </div>
  );
}
```

---

## Performance Optimization

### Query Batching

Apollo Client automatically batches queries by default. To enable:

```typescript
import { BatchHttpLink } from '@apollo/client/link/batch-http';

const batchLink = new BatchHttpLink({
  uri: 'http://localhost:8000/graphql',
  batchMax: 5, // Max 5 queries per batch
  batchInterval: 20, // Wait 20ms before sending batch
});
```

### Cache Policies

```typescript
// Component-level cache policy
const { data } = useQuery(GET_DDE_EVENTS, {
  fetchPolicy: 'cache-first', // Use cache if available
  nextFetchPolicy: 'cache-and-network', // Then update from network
});

// Polling with cache
const { data } = useQuery(GET_CONTRACT_STARS, {
  pollInterval: 10000, // Poll every 10s
  fetchPolicy: 'cache-and-network',
});
```

---

## Testing

### Mocked Provider for Unit Tests

```typescript
import { MockedProvider } from '@apollo/client/testing';
import { render } from '@testing-library/react';
import { GET_DDE_EVENTS } from '../graphql/events.graphql';

const mocks = [
  {
    request: {
      query: GET_DDE_EVENTS,
      variables: { iterationId: 'test-123', first: 10 },
    },
    result: {
      data: {
        ddeEvents: {
          edges: [
            {
              node: {
                eventId: 'evt-1',
                iterationId: 'test-123',
                eventType: 'CONTRACT_VALIDATED',
                // ... other fields
              },
              cursor: 'cursor-1',
            },
          ],
          pageInfo: {
            hasNextPage: false,
            endCursor: 'cursor-1',
          },
          totalCount: 1,
        },
      },
    },
  },
];

test('renders events', () => {
  render(
    <MockedProvider mocks={mocks} addTypename={false}>
      <EventsLens iterationId="test-123" />
    </MockedProvider>
  );
  // ... assertions
});
```

---

## Summary

This guide provides everything needed to integrate the React frontend with the GraphQL API:

✅ Apollo Client setup with HTTP and WebSocket
✅ Example queries for all 4 lenses
✅ Custom React hooks
✅ TypeScript type generation
✅ Component examples
✅ Real-time subscriptions
✅ Error handling patterns
✅ Performance optimization
✅ Testing with MockedProvider

**Next Steps**:
1. Generate TypeScript types: `npm run codegen`
2. Implement the 4 lens components
3. Add graph visualization with Cytoscape.js
4. Test end-to-end with GraphQL server

---

**🎯 Generated with [Claude Code](https://claude.com/claude-code)**

**Co-Authored-By**: Claude <noreply@anthropic.com>
