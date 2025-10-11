"""
Feature Extraction Service
Extracts ML features from raw data for training and inference
"""

from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging


@dataclass
class FeatureExtractionConfig:
    """Configuration for feature extraction"""
    feature_definitions: Dict[str, Any]
    aggregation_window: str = "7d"  # 7 days
    min_data_points: int = 5
    handle_missing: str = "impute"  # impute, drop, or zero
    normalize: bool = True


class FeatureExtractor:
    """Extract features from raw data"""

    def __init__(self, config: FeatureExtractionConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def extract_user_features(self, user_data: pd.DataFrame, activity_data: pd.DataFrame) -> pd.DataFrame:
        """Extract user-level features"""
        features = []

        for user_id in user_data['user_id'].unique():
            user_activities = activity_data[activity_data['user_id'] == user_id]

            feature_dict = {
                'user_id': user_id,
                'event_timestamp': datetime.now()
            }

            # Skill scores from historical performance
            if 'task_type' in user_activities.columns and 'completion_time' in user_activities.columns:
                for task_type in ['backend', 'frontend', 'database', 'devops']:
                    type_tasks = user_activities[user_activities['task_type'] == task_type]
                    if len(type_tasks) > 0:
                        avg_time = type_tasks['completion_time'].mean()
                        # Lower time = higher skill (inverse relationship)
                        skill_score = 1.0 / (1.0 + avg_time / 3600)  # Normalize by hour
                        feature_dict[f'skill_score_{task_type}'] = round(skill_score, 3)
                    else:
                        feature_dict[f'skill_score_{task_type}'] = 0.0

            # Workload features
            recent_activities = user_activities[
                user_activities['timestamp'] >= (datetime.now() - timedelta(days=7))
            ]

            feature_dict['current_workload_hours'] = len(recent_activities) * 2.0  # Estimate 2h per task
            feature_dict['tasks_completed_7d'] = len(recent_activities)
            feature_dict['tasks_completed_30d'] = len(user_activities[
                user_activities['timestamp'] >= (datetime.now() - timedelta(days=30))
            ])

            # Velocity
            if len(recent_activities) > 0:
                feature_dict['avg_completion_time_hours'] = recent_activities['completion_time'].mean() / 3600
            else:
                feature_dict['avg_completion_time_hours'] = 0.0

            # Collaboration
            if 'collaborators' in user_activities.columns:
                feature_dict['avg_collaborators'] = user_activities['collaborators'].apply(
                    lambda x: len(x) if isinstance(x, list) else 0
                ).mean()
            else:
                feature_dict['avg_collaborators'] = 0.0

            # Availability
            feature_dict['availability_hours_per_week'] = 40.0  # Default, should come from calendar
            feature_dict['current_capacity_percentage'] = max(0, min(100,
                100 * (1 - feature_dict['current_workload_hours'] / feature_dict['availability_hours_per_week'])
            ))

            # Quality metrics
            if 'bugs_introduced' in user_activities.columns:
                feature_dict['bug_rate'] = user_activities['bugs_introduced'].sum() / max(1, len(user_activities))
            else:
                feature_dict['bug_rate'] = 0.0

            # Experience
            feature_dict['experience_years'] = user_data[user_data['user_id'] == user_id]['experience_years'].iloc[0] if 'experience_years' in user_data.columns else 2.0

            features.append(feature_dict)

        return pd.DataFrame(features)

    def extract_task_features(self, task_data: pd.DataFrame) -> pd.DataFrame:
        """Extract task-level features"""
        features = []

        for _, task in task_data.iterrows():
            feature_dict = {
                'task_id': task['task_id'],
                'event_timestamp': datetime.now()
            }

            # Complexity score (based on description length, requirements, etc.)
            if 'description' in task:
                feature_dict['description_length'] = len(str(task['description']))
                feature_dict['complexity_score'] = min(1.0, feature_dict['description_length'] / 1000.0)
            else:
                feature_dict['complexity_score'] = 0.5  # Default medium complexity

            # Priority mapping
            priority_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            feature_dict['priority'] = priority_map.get(task.get('priority', 'medium'), 2)

            # Estimated effort
            feature_dict['estimated_hours'] = task.get('estimated_hours', 8.0)

            # Required skills
            required_skills = task.get('required_skills', [])
            if isinstance(required_skills, str):
                required_skills = [s.strip() for s in required_skills.split(',')]

            for skill in ['backend', 'frontend', 'database', 'devops', 'testing']:
                feature_dict[f'requires_{skill}'] = 1 if skill in required_skills else 0

            # Dependencies
            dependencies = task.get('dependencies', [])
            if isinstance(dependencies, str):
                dependencies = [d.strip() for d in dependencies.split(',') if d.strip()]

            feature_dict['num_dependencies'] = len(dependencies)
            feature_dict['has_blockers'] = 1 if len(dependencies) > 0 else 0

            # Deadline urgency
            if 'deadline' in task:
                deadline = pd.to_datetime(task['deadline'])
                days_until_deadline = (deadline - datetime.now()).days
                feature_dict['days_until_deadline'] = days_until_deadline
                feature_dict['is_urgent'] = 1 if days_until_deadline < 3 else 0
            else:
                feature_dict['days_until_deadline'] = 30
                feature_dict['is_urgent'] = 0

            features.append(feature_dict)

        return pd.DataFrame(features)

    def extract_project_features(self, project_data: pd.DataFrame, task_data: pd.DataFrame) -> pd.DataFrame:
        """Extract project-level features"""
        features = []

        for _, project in project_data.iterrows():
            project_id = project['project_id']
            project_tasks = task_data[task_data['project_id'] == project_id]

            feature_dict = {
                'project_id': project_id,
                'event_timestamp': datetime.now()
            }

            # Size metrics
            feature_dict['total_tasks'] = len(project_tasks)
            feature_dict['completed_tasks'] = len(project_tasks[project_tasks['status'] == 'completed'])
            feature_dict['in_progress_tasks'] = len(project_tasks[project_tasks['status'] == 'in_progress'])
            feature_dict['blocked_tasks'] = len(project_tasks[project_tasks['status'] == 'blocked'])

            # Progress
            if len(project_tasks) > 0:
                feature_dict['completion_percentage'] = 100 * feature_dict['completed_tasks'] / len(project_tasks)
            else:
                feature_dict['completion_percentage'] = 0.0

            # Velocity
            completed_last_week = len(project_tasks[
                (project_tasks['status'] == 'completed') &
                (pd.to_datetime(project_tasks['completed_at']) >= datetime.now() - timedelta(days=7))
            ])
            feature_dict['velocity_tasks_per_week'] = completed_last_week

            # Risk indicators
            overdue_tasks = len(project_tasks[
                (pd.to_datetime(project_tasks['deadline']) < datetime.now()) &
                (project_tasks['status'] != 'completed')
            ])
            feature_dict['overdue_tasks'] = overdue_tasks
            feature_dict['risk_score'] = min(1.0, overdue_tasks / max(1, len(project_tasks)))

            # Team size
            if 'team_members' in project:
                team_members = project['team_members']
                if isinstance(team_members, str):
                    team_members = [m.strip() for m in team_members.split(',')]
                feature_dict['team_size'] = len(team_members)
            else:
                feature_dict['team_size'] = 5  # Default

            # Budget/cost (if available)
            feature_dict['estimated_budget'] = project.get('budget', 100000.0)
            feature_dict['spent_budget'] = project.get('spent', 0.0)
            feature_dict['budget_utilization'] = feature_dict['spent_budget'] / feature_dict['estimated_budget'] if feature_dict['estimated_budget'] > 0 else 0.0

            features.append(feature_dict)

        return pd.DataFrame(features)

    def extract_team_features(self, team_data: pd.DataFrame, user_data: pd.DataFrame) -> pd.DataFrame:
        """Extract team-level features"""
        features = []

        for _, team in team_data.iterrows():
            team_id = team['team_id']
            team_members = team.get('members', [])

            if isinstance(team_members, str):
                team_members = [m.strip() for m in team_members.split(',')]

            team_user_data = user_data[user_data['user_id'].isin(team_members)]

            feature_dict = {
                'team_id': team_id,
                'event_timestamp': datetime.now()
            }

            # Size
            feature_dict['team_size'] = len(team_members)

            # Skill diversity
            if 'skills' in team_user_data.columns:
                all_skills = set()
                for skills in team_user_data['skills']:
                    if isinstance(skills, str):
                        all_skills.update([s.strip() for s in skills.split(',')])
                    elif isinstance(skills, list):
                        all_skills.update(skills)
                feature_dict['skill_diversity'] = len(all_skills)
            else:
                feature_dict['skill_diversity'] = 5  # Default

            # Experience distribution
            if 'experience_years' in team_user_data.columns:
                feature_dict['avg_experience_years'] = team_user_data['experience_years'].mean()
                feature_dict['min_experience_years'] = team_user_data['experience_years'].min()
                feature_dict['max_experience_years'] = team_user_data['experience_years'].max()
            else:
                feature_dict['avg_experience_years'] = 3.0
                feature_dict['min_experience_years'] = 1.0
                feature_dict['max_experience_years'] = 5.0

            # Workload balance
            if 'current_workload_hours' in team_user_data.columns:
                feature_dict['avg_workload_hours'] = team_user_data['current_workload_hours'].mean()
                feature_dict['workload_std'] = team_user_data['current_workload_hours'].std()
                feature_dict['is_balanced'] = 1 if feature_dict['workload_std'] < 10 else 0
            else:
                feature_dict['avg_workload_hours'] = 20.0
                feature_dict['workload_std'] = 5.0
                feature_dict['is_balanced'] = 1

            # Collaboration score (based on shared projects/tasks)
            feature_dict['collaboration_score'] = 0.7  # Placeholder, would calculate from activity data

            features.append(feature_dict)

        return pd.DataFrame(features)

    def normalize_features(self, features: pd.DataFrame, exclude_cols: List[str] = None) -> pd.DataFrame:
        """Normalize numeric features to 0-1 range"""
        if not self.config.normalize:
            return features

        if exclude_cols is None:
            exclude_cols = ['user_id', 'task_id', 'project_id', 'team_id', 'event_timestamp']

        numeric_cols = features.select_dtypes(include=[np.number]).columns
        cols_to_normalize = [col for col in numeric_cols if col not in exclude_cols]

        for col in cols_to_normalize:
            min_val = features[col].min()
            max_val = features[col].max()

            if max_val > min_val:
                features[col] = (features[col] - min_val) / (max_val - min_val)

        return features

    def handle_missing_values(self, features: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in features"""
        if self.config.handle_missing == "drop":
            return features.dropna()
        elif self.config.handle_missing == "zero":
            return features.fillna(0)
        elif self.config.handle_missing == "impute":
            # Use median for numeric, mode for categorical
            numeric_cols = features.select_dtypes(include=[np.number]).columns
            categorical_cols = features.select_dtypes(include=['object']).columns

            for col in numeric_cols:
                features[col] = features[col].fillna(features[col].median())

            for col in categorical_cols:
                features[col] = features[col].fillna(features[col].mode().iloc[0] if not features[col].mode().empty else "unknown")

        return features
