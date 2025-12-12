@contract:contract_31dd1ded6b5d:v1.0
Feature: Database Specialist Contract
  

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
  Scenario: Deliverable - database_specialist_deliverables
    Given the contract execution is complete
    When I check for deliverable "database_specialist_deliverables"
    Then the deliverable should exist as a file
