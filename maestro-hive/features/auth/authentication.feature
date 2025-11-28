@contract:AuthAPI:v1.0
@critical
Feature: User Authentication
  As a registered user
  I want to authenticate with my credentials
  So that I can access protected resources

  Background:
    Given the system has the following registered users:
      | email                | password | role  |
      | alice@example.com    | p@ss123  | user  |
      | bob@example.com      | secure456| admin |
    And the AuthAPI v1.0 contract is deployed
    And the authentication service is running

  Scenario: Successful login with valid credentials
    Given a registered user "alice@example.com" with password "p@ss123"
    When she requests a token via POST /auth/token with:
      | email             | password |
      | alice@example.com | p@ss123  |
    Then the response status code should be 200
    And the response body should contain a "token" field
    And the token should be a valid JWT
    And the token should have claim "sub" with value "alice@example.com"
    And the token should have claim "role" with value "user"
    And the token should expire in 3600 seconds

  Scenario: Failed login with invalid password
    Given a registered user "alice@example.com" with password "p@ss123"
    When she requests a token via POST /auth/token with:
      | email             | password       |
      | alice@example.com | wrong_password |
    Then the response status code should be 401
    And the response body should contain error "invalid_credentials"
    And the response should not contain a "token" field

  Scenario Outline: Login rate limiting after failed attempts
    Given a user has failed <failed_attempts> login attempts
    When she attempts to login again
    Then the response status code should be <status_code>
    And the response should contain <message>

    Examples:
      | failed_attempts | status_code | message                     |
      | 3               | 401         | invalid_credentials         |
      | 5               | 429         | rate_limit_exceeded         |
      | 10              | 429         | account_temporarily_locked  |
