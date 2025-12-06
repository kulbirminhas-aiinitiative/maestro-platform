@contract:test_contract_bdv_3:v1.0
Feature: Dict Deliverables Test
  Test with dict deliverables

  @criterion_1
  Scenario: Acceptance Criterion 1
    Given the system is in initial state
    When the criterion is evaluated
    Then it should satisfy: Feature works

  @deliverable
  Scenario: Deliverable - auth_module
    Given the contract execution is complete
    When I check for deliverable "auth_module"
    Then the deliverable should exist as a module

  @deliverable
  Scenario: Deliverable - config.json
    Given the contract execution is complete
    When I check for deliverable "config.json"
    Then the deliverable should exist as a config
