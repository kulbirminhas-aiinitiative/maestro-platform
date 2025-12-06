@contract:e2e_contract:v1.0
Feature: End-to-End Test Contract
  Full pipeline test

  @criterion_1
  Scenario: Acceptance Criterion 1
    Given the system is in initial state
    When the criterion is evaluated
    Then it should satisfy: System initializes correctly

  @deliverable
  Scenario: Deliverable - main.py
    Given the contract execution is complete
    When I check for deliverable "main.py"
    Then the deliverable should exist as a file
