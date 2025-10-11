module.exports = {
  ci: {
    collect: {
      url: [
        'http://localhost:3001',
        'http://localhost:3001/login',
        'http://localhost:3001/dashboard',
        'http://localhost:3001/boards'
      ],
      startServerCommand: 'docker-compose -f docker-compose.dev.yml up -d',
      startServerReadyPattern: 'ready',
      startServerReadyTimeout: 60000
    },
    assert: {
      assertions: {
        'categories:performance': ['error', {minScore: 0.8}],
        'categories:accessibility': ['error', {minScore: 0.9}],
        'categories:best-practices': ['error', {minScore: 0.9}],
        'categories:seo': ['error', {minScore: 0.8}],
        'first-contentful-paint': ['error', {maxNumericValue: 2000}],
        'largest-contentful-paint': ['error', {maxNumericValue: 3000}],
        'cumulative-layout-shift': ['error', {maxNumericValue: 0.1}],
        'total-blocking-time': ['error', {maxNumericValue: 300}]
      }
    },
    upload: {
      target: 'temporary-public-storage'
    }
  }
};