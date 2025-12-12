@contract:contract_7c572da32d30:v1.0
Feature: Backend Developer Contract
  

  @criterion_1
  Scenario: Acceptance Criterion 1
    Given the system is in initial state
    When the criterion is evaluated
    Then it should satisfy: Deliverables complete

  @criterion_2
  Scenario: Acceptance Criterion 2
    Given the system is in initial state
    When the criterion is evaluated
    Then it should satisfy: Quality gate passed

  @deliverable
  Scenario: Deliverable - backend_developer_deliverables
    Given the contract execution is complete
    When I check for deliverable "backend_developer_deliverables"
    Then the deliverable should exist as a file
