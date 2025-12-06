@contract:test_contract_1:v1.0
Feature: Test Contract
  Test contract for validation

  @criterion_1
  Scenario: Acceptance Criterion 1
    Given the system is in initial state
    When the criterion is evaluated
    Then it should satisfy: User can log in

  @criterion_2
  Scenario: Acceptance Criterion 2
    Given the system is in initial state
    When the criterion is evaluated
    Then it should satisfy: System validates input

  @criterion_3
  Scenario: Acceptance Criterion 3
    Given the system is in initial state
    When the criterion is evaluated
    Then it should satisfy: Data is persisted

  @deliverable
  Scenario: Deliverable - login.py
    Given the contract execution is complete
    When I check for deliverable "login.py"
    Then the deliverable should exist as a file

  @deliverable
  Scenario: Deliverable - validator.py
    Given the contract execution is complete
    When I check for deliverable "validator.py"
    Then the deliverable should exist as a file
