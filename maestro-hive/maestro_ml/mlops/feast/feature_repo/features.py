"""
Maestro ML Feature Definitions
Phase 1.2.1 - Design data schema for ML features
Phase 1.2.3 - Build feature extraction service
"""

from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Float64, Int64, String, Bool, UnixTimestamp

# ========================================
# Entities
# ========================================

# User Entity - represents team members
user_entity = Entity(
    name="user",
    join_keys=["user_id"],
    description="Team member/user in the platform",
)

# Task Entity - represents work items
task_entity = Entity(
    name="task",
    join_keys=["task_id"],
    description="Work item/task in the platform",
)

# Project Entity - represents projects/boards
project_entity = Entity(
    name="project",
    join_keys=["project_id"],
    description="Project/board in the platform",
)

# Team Entity - represents teams
team_entity = Entity(
    name="team",
    join_keys=["team_id"],
    description="Team in the organization",
)

# ========================================
# Feature Sources
# ========================================

# User Features Source
user_features_source = FileSource(
    path="s3://maestro-ml-artifacts/feast/data/user_features.parquet",
    timestamp_field="event_timestamp",
)

# Task Features Source
task_features_source = FileSource(
    path="s3://maestro-ml-artifacts/feast/data/task_features.parquet",
    timestamp_field="event_timestamp",
)

# Project Features Source
project_features_source = FileSource(
    path="s3://maestro-ml-artifacts/feast/data/project_features.parquet",
    timestamp_field="event_timestamp",
)

# User Activity Source
user_activity_source = FileSource(
    path="s3://maestro-ml-artifacts/feast/data/user_activity.parquet",
    timestamp_field="event_timestamp",
)

# ========================================
# Feature Views
# ========================================

# User Profile Features
# Used for: Task Assignment, Personalization
user_profile_features = FeatureView(
    name="user_profile_features",
    entities=[user_entity],
    ttl=timedelta(days=1),
    schema=[
        Field(name="skill_score_backend", dtype=Float32),
        Field(name="skill_score_frontend", dtype=Float32),
        Field(name="skill_score_design", dtype=Float32),
        Field(name="skill_score_devops", dtype=Float32),
        Field(name="skill_score_data", dtype=Float32),
        Field(name="total_tasks_completed", dtype=Int64),
        Field(name="avg_task_completion_time_hours", dtype=Float32),
        Field(name="current_workload_hours", dtype=Float32),
        Field(name="availability_percentage", dtype=Float32),
        Field(name="team_id", dtype=String),
        Field(name="role", dtype=String),
        Field(name="seniority_level", dtype=String),
        Field(name="collaboration_score", dtype=Float32),
        Field(name="quality_score", dtype=Float32),
    ],
    source=user_features_source,
    online=True,
    description="User profile and skill features for task assignment and personalization",
    tags={"team": "ml-platform", "capability": "task-assignment"},
)

# User Activity Features
# Used for: Anomaly Detection, Personalization
user_activity_features = FeatureView(
    name="user_activity_features",
    entities=[user_entity],
    ttl=timedelta(hours=6),
    schema=[
        Field(name="tasks_created_last_24h", dtype=Int64),
        Field(name="tasks_completed_last_24h", dtype=Int64),
        Field(name="comments_posted_last_24h", dtype=Int64),
        Field(name="active_hours_last_7d", dtype=Float32),
        Field(name="login_count_last_7d", dtype=Int64),
        Field(name="avg_response_time_minutes", dtype=Float32),
        Field(name="collaboration_events_last_24h", dtype=Int64),
        Field(name="notifications_sent_last_24h", dtype=Int64),
    ],
    source=user_activity_source,
    online=True,
    description="User activity metrics for anomaly detection and engagement",
    tags={"team": "ml-platform", "capability": "anomaly-detection"},
)

# Task Features
# Used for: Task Assignment, Timeline Prediction
task_features = FeatureView(
    name="task_features",
    entities=[task_entity],
    ttl=timedelta(hours=1),
    schema=[
        Field(name="task_priority", dtype=String),
        Field(name="task_complexity_score", dtype=Float32),
        Field(name="estimated_hours", dtype=Float32),
        Field(name="actual_hours_spent", dtype=Float32),
        Field(name="dependency_count", dtype=Int64),
        Field(name="blocked_count", dtype=Int64),
        Field(name="comment_count", dtype=Int64),
        Field(name="attachment_count", dtype=Int64),
        Field(name="assignee_count", dtype=Int64),
        Field(name="subtask_count", dtype=Int64),
        Field(name="completion_percentage", dtype=Float32),
        Field(name="days_since_created", dtype=Int64),
        Field(name="days_until_due", dtype=Int64),
        Field(name="task_type", dtype=String),
        Field(name="project_id", dtype=String),
        Field(name="is_overdue", dtype=Bool),
    ],
    source=task_features_source,
    online=True,
    description="Task characteristics for assignment and timeline prediction",
    tags={"team": "ml-platform", "capability": "timeline-prediction"},
)

# Project Features
# Used for: Timeline Prediction, Analytics
project_features = FeatureView(
    name="project_features",
    entities=[project_entity],
    ttl=timedelta(hours=12),
    schema=[
        Field(name="total_tasks", dtype=Int64),
        Field(name="completed_tasks", dtype=Int64),
        Field(name="in_progress_tasks", dtype=Int64),
        Field(name="blocked_tasks", dtype=Int64),
        Field(name="overdue_tasks", dtype=Int64),
        Field(name="team_size", dtype=Int64),
        Field(name="avg_task_completion_time_hours", dtype=Float32),
        Field(name="project_complexity_score", dtype=Float32),
        Field(name="budget_utilized_percentage", dtype=Float32),
        Field(name="velocity_last_sprint", dtype=Float32),
        Field(name="velocity_last_3_sprints", dtype=Float32),
        Field(name="risk_score", dtype=Float32),
        Field(name="days_since_started", dtype=Int64),
        Field(name="days_until_deadline", dtype=Int64),
        Field(name="project_type", dtype=String),
        Field(name="is_delayed", dtype=Bool),
    ],
    source=project_features_source,
    online=True,
    description="Project-level features for timeline and resource planning",
    tags={"team": "ml-platform", "capability": "timeline-prediction"},
)

# Historical Task Assignment Features
# Used for: Task Assignment Model Training
historical_task_assignment_source = FileSource(
    path="s3://maestro-ml-artifacts/feast/data/historical_assignments.parquet",
    timestamp_field="assignment_timestamp",
)

historical_task_assignments = FeatureView(
    name="historical_task_assignments",
    entities=[task_entity, user_entity],
    ttl=timedelta(days=90),
    schema=[
        Field(name="assignment_success", dtype=Bool),
        Field(name="completion_time_hours", dtype=Float32),
        Field(name="quality_rating", dtype=Float32),
        Field(name="user_satisfaction_score", dtype=Float32),
        Field(name="skill_match_score", dtype=Float32),
        Field(name="workload_at_assignment", dtype=Float32),
    ],
    source=historical_task_assignment_source,
    online=False,  # Only for offline training
    description="Historical assignment outcomes for model training",
    tags={"team": "ml-platform", "capability": "task-assignment"},
)

# ========================================
# On-Demand Feature Views (Computed Features)
# ========================================

from feast import on_demand_feature_view
from feast.data_source import RequestSource

# Request data for on-demand features
task_request = RequestSource(
    name="task_request",
    schema=[
        Field(name="current_timestamp", dtype=UnixTimestamp),
        Field(name="task_created_at", dtype=UnixTimestamp),
    ],
)

@on_demand_feature_view(
    sources=[task_features, task_request],
    schema=[
        Field(name="task_age_hours", dtype=Float32),
        Field(name="urgency_score", dtype=Float32),
    ],
    description="Computed task urgency features",
)
def task_urgency_features(inputs: dict) -> dict:
    """Compute real-time task urgency metrics"""
    task_age_hours = (
        inputs["current_timestamp"] - inputs["task_created_at"]
    ) / 3600.0

    # Calculate urgency based on age, due date, and priority
    urgency_score = 0.0
    if inputs["days_until_due"] < 1:
        urgency_score = 1.0
    elif inputs["days_until_due"] < 3:
        urgency_score = 0.8
    elif inputs["task_priority"] == "high":
        urgency_score = 0.6
    else:
        urgency_score = 0.3

    return {
        "task_age_hours": task_age_hours,
        "urgency_score": urgency_score,
    }

# User workload on-demand features
user_request = RequestSource(
    name="user_request",
    schema=[
        Field(name="requested_hours", dtype=Float32),
    ],
)

@on_demand_feature_view(
    sources=[user_profile_features, user_request],
    schema=[
        Field(name="workload_capacity_available", dtype=Float32),
        Field(name="can_accommodate_task", dtype=Bool),
    ],
    description="Real-time user capacity calculation",
)
def user_capacity_features(inputs: dict) -> dict:
    """Calculate if user has capacity for new task"""
    max_weekly_hours = 40.0
    current_workload = inputs["current_workload_hours"]
    requested = inputs["requested_hours"]

    available_capacity = max_weekly_hours - current_workload
    can_accommodate = available_capacity >= requested

    return {
        "workload_capacity_available": available_capacity,
        "can_accommodate_task": can_accommodate,
    }
