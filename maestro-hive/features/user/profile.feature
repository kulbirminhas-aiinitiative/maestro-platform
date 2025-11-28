# BDV Feature File - User Profile Management
# Contract: UserProfileAPI v1.0

@contract:UserProfileAPI:v1.0
@mvp
Feature: User Profile Management
  As a registered user
  I want to manage my profile information
  So that I can keep my account details up to date

  Background:
    Given the UserProfileAPI v1.0 contract is available
    And the profile service is running
    And a user "bob@example.com" is logged in with a valid token

  @happy_path
  Scenario: Get user profile
    Given the user "bob@example.com" has a complete profile
    When the user requests GET /api/users/{user_id}/profile
    Then the response status is 200
    And the response body contains:
      | field         | value                   |
      | email         | bob@example.com         |
      | display_name  | Bob Smith               |
      | avatar_url    | https://cdn.../avatar.png |
      | created_at    | 2025-01-15T10:00:00Z    |

  @happy_path
  Scenario: Update full profile with valid data
    Given the user "bob@example.com" has an existing profile
    When the user requests PUT /api/users/{user_id}/profile with:
      """
      {
        "display_name": "Robert Smith",
        "bio": "Software engineer and dog lover",
        "location": "San Francisco, CA",
        "website": "https://bobsmith.dev"
      }
      """
    Then the response status is 200
    And the profile is updated with the new data
    And the response body contains the updated profile
    And an audit log entry is created

  @happy_path
  Scenario: Partial update profile with PATCH
    Given the user "bob@example.com" has an existing profile
    When the user requests PATCH /api/users/{user_id}/profile with:
      """
      {
        "bio": "Updated bio - passionate about React and TypeScript"
      }
      """
    Then the response status is 200
    And only the "bio" field is updated
    And other fields remain unchanged

  @validation
  Scenario: Update profile with invalid email format
    When the user requests PUT /api/users/{user_id}/profile with:
      """
      {
        "email": "invalid-email-format"
      }
      """
    Then the response status is 400
    And the response body contains error "Invalid email format"

  @validation
  Scenario: Update profile with excessively long bio
    When the user requests PUT /api/users/{user_id}/profile with:
      """
      {
        "bio": "<2000 character string>"
      }
      """
    Then the response status is 400
    And the response body contains error "Bio exceeds maximum length of 1000 characters"

  @validation
  Scenario: Update profile with invalid website URL
    When the user requests PUT /api/users/{user_id}/profile with:
      """
      {
        "website": "not-a-valid-url"
      }
      """
    Then the response status is 400
    And the response body contains error "Invalid website URL format"

  @security
  Scenario: Attempt to update another user's profile
    Given another user "alice@example.com" exists with user_id "user-456"
    When the user "bob@example.com" requests PUT /api/users/user-456/profile with valid data
    Then the response status is 403
    And the response body contains error "Forbidden: Cannot update another user's profile"

  @security
  Scenario: Update profile without authentication
    When an unauthenticated request is made to PUT /api/users/{user_id}/profile
    Then the response status is 401
    And the response body contains error "Authentication required"

  @avatar_upload
  Scenario: Upload profile avatar
    Given the user "bob@example.com" has a profile
    When the user uploads an avatar image via POST /api/users/{user_id}/profile/avatar with:
      | file_name     | avatar.png              |
      | content_type  | image/png               |
      | size_bytes    | 524288                  |
    Then the response status is 200
    And the avatar is stored in object storage
    And the profile "avatar_url" is updated with the CDN URL
    And the old avatar is marked for deletion

  @avatar_upload
  Scenario: Reject oversized avatar upload
    When the user uploads an avatar image via POST /api/users/{user_id}/profile/avatar with:
      | file_name     | large_avatar.png        |
      | size_bytes    | 5242880                 |
    Then the response status is 413
    And the response body contains error "Avatar file size exceeds maximum of 2MB"

  @data_privacy
  Scenario: Delete user profile
    Given the user "bob@example.com" has a profile
    When the user requests DELETE /api/users/{user_id}/profile
    Then the response status is 204
    And the profile is soft-deleted in the database
    And all personal data is anonymized
    And profile-related artifacts are marked for archival
