@contract:test_contract_bdv_1:v1.0
Feature: Test Contract
  Test contract for validation

  @criterion_1
  Scenario: Acceptance Criterion 1
    Given the system is in initial state
    When the criterion is evaluated
    Then it should satisfy: User can authenticate

  @criterion_2
  Scenario: Acceptance Criterion 2
    Given the system is in initial state
    When the criterion is evaluated
    Then it should satisfy: System validates input

  @deliverable
  Scenario: Deliverable - auth.py
    Given the contract execution is complete
    When I check for deliverable "auth.py"
    Then the deliverable should exist as a file
