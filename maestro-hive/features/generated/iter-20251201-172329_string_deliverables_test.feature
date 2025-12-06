@contract:test_contract_bdv_2:v1.0
Feature: String Deliverables Test
  Test with string deliverables

  @criterion_1
  Scenario: Acceptance Criterion 1
    Given the system is in initial state
    When the criterion is evaluated
    Then it should satisfy: Feature works

  @deliverable
  Scenario: Deliverable - file1.py
    Given the contract execution is complete
    When I check for deliverable "file1.py"
    Then the deliverable should exist as a file

  @deliverable
  Scenario: Deliverable - file2.py
    Given the contract execution is complete
    When I check for deliverable "file2.py"
    Then the deliverable should exist as a file

  @deliverable
  Scenario: Deliverable - file3.py
    Given the contract execution is complete
    When I check for deliverable "file3.py"
    Then the deliverable should exist as a file
