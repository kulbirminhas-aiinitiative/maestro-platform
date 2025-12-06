"""
Cypress E2E Test Templates - MD-2523

End-to-end testing templates for web applications using Cypress.
"""

from typing import Dict, Any
from .models import TestTemplate, TestType, TestFramework


class CypressE2ETemplate(TestTemplate):
    """Cypress end-to-end test template."""

    def __init__(self, app_name: str = "app", base_url: str = "http://localhost:3000"):
        super().__init__(
            name="cypress_e2e_template",
            description="Comprehensive Cypress E2E test template with page objects",
            test_type=TestType.E2E,
            framework=TestFramework.CYPRESS,
            file_extension=".cy.js",
            tags=["e2e", "cypress", "web", "ui"],
            dependencies=["cypress>=12.0.0"],
            variables={"app_name": app_name, "base_url": base_url},
        )

        self.template_content = '''/**
 * E2E Tests for {{ app_name }}
 * Base URL: {{ base_url }}
 *
 * @description Comprehensive end-to-end tests covering user flows
 */

// ==============================================================================
// Configuration & Setup
// ==============================================================================

describe('{{ app_name }} E2E Tests', () => {
  beforeEach(() => {
    // Reset state before each test
    cy.clearLocalStorage();
    cy.clearCookies();

    // Visit base URL
    cy.visit('/');
  });

  // ==============================================================================
  // Authentication Flow Tests
  // ==============================================================================

  describe('Authentication', () => {
    it('should display login form on homepage', () => {
      cy.get('[data-testid="login-form"]').should('be.visible');
      cy.get('[data-testid="email-input"]').should('be.visible');
      cy.get('[data-testid="password-input"]').should('be.visible');
      cy.get('[data-testid="login-button"]').should('be.visible');
    });

    it('should login with valid credentials', () => {
      cy.get('[data-testid="email-input"]').type('user@example.com');
      cy.get('[data-testid="password-input"]').type('password123');
      cy.get('[data-testid="login-button"]').click();

      // Verify successful login
      cy.url().should('include', '/dashboard');
      cy.get('[data-testid="user-menu"]').should('be.visible');
    });

    it('should show error for invalid credentials', () => {
      cy.get('[data-testid="email-input"]').type('invalid@example.com');
      cy.get('[data-testid="password-input"]').type('wrongpassword');
      cy.get('[data-testid="login-button"]').click();

      cy.get('[data-testid="error-message"]')
        .should('be.visible')
        .and('contain', 'Invalid credentials');
    });

    it('should logout successfully', () => {
      // Login first
      cy.login('user@example.com', 'password123');

      // Logout
      cy.get('[data-testid="user-menu"]').click();
      cy.get('[data-testid="logout-button"]').click();

      // Verify logged out
      cy.url().should('include', '/login');
      cy.get('[data-testid="login-form"]').should('be.visible');
    });
  });

  // ==============================================================================
  // Navigation Tests
  // ==============================================================================

  describe('Navigation', () => {
    beforeEach(() => {
      // Login before navigation tests
      cy.login('user@example.com', 'password123');
    });

    it('should navigate to dashboard', () => {
      cy.get('[data-testid="nav-dashboard"]').click();
      cy.url().should('include', '/dashboard');
      cy.get('[data-testid="dashboard-title"]').should('be.visible');
    });

    it('should navigate to settings', () => {
      cy.get('[data-testid="nav-settings"]').click();
      cy.url().should('include', '/settings');
    });

    it('should navigate using breadcrumbs', () => {
      cy.visit('/dashboard/projects/123');
      cy.get('[data-testid="breadcrumb-dashboard"]').click();
      cy.url().should('include', '/dashboard');
    });
  });

  // ==============================================================================
  // CRUD Operations Tests
  // ==============================================================================

  describe('Resource Management', () => {
    beforeEach(() => {
      cy.login('user@example.com', 'password123');
      cy.visit('/resources');
    });

    it('should create a new resource', () => {
      cy.get('[data-testid="create-resource-button"]').click();

      // Fill form
      cy.get('[data-testid="resource-name-input"]').type('New Resource');
      cy.get('[data-testid="resource-description-input"]')
        .type('Test resource description');
      cy.get('[data-testid="resource-type-select"]').select('Type A');

      // Submit
      cy.get('[data-testid="submit-button"]').click();

      // Verify created
      cy.get('[data-testid="success-toast"]')
        .should('be.visible')
        .and('contain', 'Resource created');
      cy.get('[data-testid="resource-list"]')
        .should('contain', 'New Resource');
    });

    it('should edit an existing resource', () => {
      cy.get('[data-testid="resource-row"]').first().within(() => {
        cy.get('[data-testid="edit-button"]').click();
      });

      cy.get('[data-testid="resource-name-input"]')
        .clear()
        .type('Updated Resource');
      cy.get('[data-testid="submit-button"]').click();

      cy.get('[data-testid="success-toast"]')
        .should('be.visible')
        .and('contain', 'Resource updated');
    });

    it('should delete a resource with confirmation', () => {
      cy.get('[data-testid="resource-row"]').first().within(() => {
        cy.get('[data-testid="delete-button"]').click();
      });

      // Confirmation dialog
      cy.get('[data-testid="confirm-dialog"]').should('be.visible');
      cy.get('[data-testid="confirm-delete-button"]').click();

      cy.get('[data-testid="success-toast"]')
        .should('be.visible')
        .and('contain', 'Resource deleted');
    });
  });

  // ==============================================================================
  // Form Validation Tests
  // ==============================================================================

  describe('Form Validation', () => {
    beforeEach(() => {
      cy.login('user@example.com', 'password123');
      cy.visit('/resources/new');
    });

    it('should show validation errors for empty required fields', () => {
      cy.get('[data-testid="submit-button"]').click();

      cy.get('[data-testid="name-error"]')
        .should('be.visible')
        .and('contain', 'Name is required');
    });

    it('should validate email format', () => {
      cy.get('[data-testid="email-input"]').type('invalid-email');
      cy.get('[data-testid="submit-button"]').click();

      cy.get('[data-testid="email-error"]')
        .should('be.visible')
        .and('contain', 'Invalid email format');
    });

    it('should validate minimum length', () => {
      cy.get('[data-testid="password-input"]').type('123');
      cy.get('[data-testid="submit-button"]').click();

      cy.get('[data-testid="password-error"]')
        .should('be.visible')
        .and('contain', 'minimum');
    });
  });

  // ==============================================================================
  // API Integration Tests
  // ==============================================================================

  describe('API Integration', () => {
    it('should handle API errors gracefully', () => {
      cy.intercept('GET', '/api/resources', {
        statusCode: 500,
        body: { error: 'Internal Server Error' },
      });

      cy.login('user@example.com', 'password123');
      cy.visit('/resources');

      cy.get('[data-testid="error-message"]')
        .should('be.visible')
        .and('contain', 'Something went wrong');
    });

    it('should show loading state during API calls', () => {
      cy.intercept('GET', '/api/resources', (req) => {
        req.on('response', (res) => {
          res.setDelay(1000);
        });
      });

      cy.login('user@example.com', 'password123');
      cy.visit('/resources');

      cy.get('[data-testid="loading-spinner"]').should('be.visible');
    });
  });

  // ==============================================================================
  // Responsive Design Tests
  // ==============================================================================

  describe('Responsive Design', () => {
    const viewports = [
      { device: 'mobile', width: 375, height: 667 },
      { device: 'tablet', width: 768, height: 1024 },
      { device: 'desktop', width: 1280, height: 720 },
    ];

    viewports.forEach(({ device, width, height }) => {
      it(`should render correctly on ${device}`, () => {
        cy.viewport(width, height);
        cy.visit('/');

        // Check main elements are visible
        cy.get('[data-testid="header"]').should('be.visible');
        cy.get('[data-testid="main-content"]').should('be.visible');

        // Mobile-specific checks
        if (device === 'mobile') {
          cy.get('[data-testid="mobile-menu-button"]').should('be.visible');
          cy.get('[data-testid="desktop-nav"]').should('not.be.visible');
        }
      });
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    beforeEach(() => {
      cy.visit('/');
      cy.injectAxe();
    });

    it('should have no accessibility violations on homepage', () => {
      cy.checkA11y();
    });

    it('should have no accessibility violations on dashboard', () => {
      cy.login('user@example.com', 'password123');
      cy.visit('/dashboard');
      cy.injectAxe();
      cy.checkA11y();
    });

    it('should support keyboard navigation', () => {
      cy.get('body').tab();
      cy.focused().should('have.attr', 'data-testid', 'skip-link');

      cy.focused().tab();
      cy.focused().should('have.attr', 'data-testid', 'nav-link-1');
    });
  });
});
'''


class CypressComponentTemplate(TestTemplate):
    """Cypress component testing template."""

    def __init__(self, component_name: str = "Component"):
        super().__init__(
            name="cypress_component_template",
            description="Cypress component test template for isolated component testing",
            test_type=TestType.UNIT,
            framework=TestFramework.CYPRESS,
            file_extension=".cy.jsx",
            tags=["component", "cypress", "react", "ui"],
            dependencies=["cypress>=12.0.0"],
            variables={"component_name": component_name},
        )

        self.template_content = '''/**
 * Component Tests for {{ component_name }}
 *
 * @description Isolated component tests using Cypress Component Testing
 */

import React from 'react';
// import { {{ component_name }} } from './{{ component_name }}';

describe('{{ component_name }}', () => {
  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('should render with default props', () => {
      // cy.mount(<{{ component_name }} />);
      // cy.get('[data-testid="{{ component_name.lower() }}"]').should('be.visible');
    });

    it('should render with custom props', () => {
      // cy.mount(<{{ component_name }} title="Custom Title" variant="primary" />);
      // cy.get('[data-testid="{{ component_name.lower() }}"]')
      //   .should('contain', 'Custom Title');
    });

    it('should render children correctly', () => {
      // cy.mount(
      //   <{{ component_name }}>
      //     <span data-testid="child">Child Content</span>
      //   </{{ component_name }}>
      // );
      // cy.get('[data-testid="child"]').should('be.visible');
    });
  });

  // ==============================================================================
  // Interaction Tests
  // ==============================================================================

  describe('Interactions', () => {
    it('should handle click events', () => {
      const onClick = cy.stub().as('onClick');
      // cy.mount(<{{ component_name }} onClick={onClick} />);
      // cy.get('[data-testid="{{ component_name.lower() }}"]').click();
      // cy.get('@onClick').should('have.been.calledOnce');
    });

    it('should handle input changes', () => {
      const onChange = cy.stub().as('onChange');
      // cy.mount(<{{ component_name }} onChange={onChange} />);
      // cy.get('input').type('test value');
      // cy.get('@onChange').should('have.been.called');
    });

    it('should handle form submission', () => {
      const onSubmit = cy.stub().as('onSubmit');
      // cy.mount(<{{ component_name }} onSubmit={onSubmit} />);
      // cy.get('form').submit();
      // cy.get('@onSubmit').should('have.been.calledOnce');
    });
  });

  // ==============================================================================
  // State Tests
  // ==============================================================================

  describe('State Management', () => {
    it('should toggle state on button click', () => {
      // cy.mount(<{{ component_name }} initialOpen={false} />);
      // cy.get('[data-testid="toggle-button"]').click();
      // cy.get('[data-testid="content"]').should('be.visible');
    });

    it('should update displayed count', () => {
      // cy.mount(<{{ component_name }} />);
      // cy.get('[data-testid="counter"]').should('contain', '0');
      // cy.get('[data-testid="increment"]').click();
      // cy.get('[data-testid="counter"]').should('contain', '1');
    });
  });

  // ==============================================================================
  // Styling Tests
  // ==============================================================================

  describe('Styling', () => {
    it('should apply primary variant styles', () => {
      // cy.mount(<{{ component_name }} variant="primary" />);
      // cy.get('[data-testid="{{ component_name.lower() }}"]')
      //   .should('have.css', 'background-color', 'rgb(0, 123, 255)');
    });

    it('should apply disabled styles', () => {
      // cy.mount(<{{ component_name }} disabled />);
      // cy.get('[data-testid="{{ component_name.lower() }}"]')
      //   .should('have.css', 'opacity', '0.5')
      //   .and('have.attr', 'disabled');
    });
  });
});
'''


class CypressCommandsTemplate(TestTemplate):
    """Cypress custom commands template."""

    def __init__(self):
        super().__init__(
            name="cypress_commands_template",
            description="Cypress custom commands for reusable test utilities",
            test_type=TestType.E2E,
            framework=TestFramework.CYPRESS,
            file_extension=".js",
            tags=["commands", "cypress", "utilities"],
            dependencies=["cypress>=12.0.0"],
        )

        self.template_content = '''/**
 * Cypress Custom Commands
 *
 * @description Reusable custom commands for E2E tests
 */

// ==============================================================================
// Authentication Commands
// ==============================================================================

/**
 * Login command - authenticates user via UI or API
 * @param {string} email - User email
 * @param {string} password - User password
 * @param {object} options - Additional options
 */
Cypress.Commands.add('login', (email, password, options = {}) => {
  const { method = 'ui' } = options;

  if (method === 'api') {
    // API-based login (faster)
    cy.request('POST', '/api/auth/login', { email, password })
      .then((response) => {
        window.localStorage.setItem('authToken', response.body.token);
      });
  } else {
    // UI-based login
    cy.visit('/login');
    cy.get('[data-testid="email-input"]').type(email);
    cy.get('[data-testid="password-input"]').type(password);
    cy.get('[data-testid="login-button"]').click();
    cy.url().should('not.include', '/login');
  }
});

/**
 * Logout command
 */
Cypress.Commands.add('logout', () => {
  cy.get('[data-testid="user-menu"]').click();
  cy.get('[data-testid="logout-button"]').click();
  cy.url().should('include', '/login');
});

// ==============================================================================
// Data Management Commands
// ==============================================================================

/**
 * Create test data via API
 * @param {string} endpoint - API endpoint
 * @param {object} data - Data to create
 */
Cypress.Commands.add('createTestData', (endpoint, data) => {
  return cy.request({
    method: 'POST',
    url: `/api/${endpoint}`,
    body: data,
    headers: {
      Authorization: `Bearer ${window.localStorage.getItem('authToken')}`,
    },
  }).its('body');
});

/**
 * Clean up test data via API
 * @param {string} endpoint - API endpoint
 * @param {string} id - Resource ID to delete
 */
Cypress.Commands.add('cleanupTestData', (endpoint, id) => {
  return cy.request({
    method: 'DELETE',
    url: `/api/${endpoint}/${id}`,
    headers: {
      Authorization: `Bearer ${window.localStorage.getItem('authToken')}`,
    },
    failOnStatusCode: false,
  });
});

// ==============================================================================
// UI Interaction Commands
// ==============================================================================

/**
 * Select from dropdown by text
 * @param {string} selector - Dropdown selector
 * @param {string} text - Option text to select
 */
Cypress.Commands.add('selectByText', (selector, text) => {
  cy.get(selector).click();
  cy.get(`${selector} [data-testid="option"]`)
    .contains(text)
    .click();
});

/**
 * Fill form fields
 * @param {object} fieldValues - Object mapping field names to values
 */
Cypress.Commands.add('fillForm', (fieldValues) => {
  Object.entries(fieldValues).forEach(([field, value]) => {
    const selector = `[data-testid="${field}-input"]`;

    if (typeof value === 'boolean') {
      // Checkbox
      if (value) {
        cy.get(selector).check();
      } else {
        cy.get(selector).uncheck();
      }
    } else if (Array.isArray(value)) {
      // Multi-select
      value.forEach((v) => cy.selectByText(selector, v));
    } else {
      // Text input
      cy.get(selector).clear().type(value);
    }
  });
});

// ==============================================================================
// Assertion Commands
// ==============================================================================

/**
 * Assert toast notification
 * @param {string} type - Toast type (success, error, warning, info)
 * @param {string} message - Expected message content
 */
Cypress.Commands.add('assertToast', (type, message) => {
  cy.get(`[data-testid="${type}-toast"]`)
    .should('be.visible')
    .and('contain', message);
});

/**
 * Assert table row contains values
 * @param {number} rowIndex - Row index (0-based)
 * @param {object} values - Expected values by column
 */
Cypress.Commands.add('assertTableRow', (rowIndex, values) => {
  cy.get('[data-testid="table-row"]').eq(rowIndex).within(() => {
    Object.entries(values).forEach(([column, expected]) => {
      cy.get(`[data-testid="cell-${column}"]`).should('contain', expected);
    });
  });
});

// ==============================================================================
// Wait Commands
// ==============================================================================

/**
 * Wait for API response
 * @param {string} method - HTTP method
 * @param {string} url - URL pattern
 * @param {string} alias - Alias name
 */
Cypress.Commands.add('waitForApi', (method, url, alias) => {
  cy.intercept(method, url).as(alias);
  return cy.wait(`@${alias}`);
});

/**
 * Wait for element to be stable (no animations)
 * @param {string} selector - Element selector
 */
Cypress.Commands.add('waitForStable', (selector) => {
  let previousPosition = null;

  cy.get(selector).should(($el) => {
    const currentPosition = $el[0].getBoundingClientRect();
    if (previousPosition) {
      expect(currentPosition.top).to.equal(previousPosition.top);
      expect(currentPosition.left).to.equal(previousPosition.left);
    }
    previousPosition = currentPosition;
  });
});
'''
