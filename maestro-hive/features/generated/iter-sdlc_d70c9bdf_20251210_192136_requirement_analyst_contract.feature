@contract:contract_10a029599d77:v1.0
Feature: Requirement Analyst Contract
  

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
  Scenario: Deliverable - requirement_analyst_deliverables
    Given the contract execution is complete
    When I check for deliverable "requirement_analyst_deliverables"
    Then the deliverable should exist as a file
