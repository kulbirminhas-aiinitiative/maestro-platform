@contract:contract_bf4362c0eaf0:v1.0
Feature: Solution Architect Contract
  

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
  Scenario: Deliverable - solution_architect_deliverables
    Given the contract execution is complete
    When I check for deliverable "solution_architect_deliverables"
    Then the deliverable should exist as a file
