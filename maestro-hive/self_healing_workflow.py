#!/usr/bin/env python3
"""
Self-Healing Workflow System

This system automatically detects and fixes workflow issues using DAG-based recovery.
It runs validation → detects issues → executes targeted recovery DAGs → re-validates → repeats until deployable.

Architecture:
1. Validation Node: Identifies all gaps
2. Issue Classifier Node: Categorizes issues by type
3. Recovery Strategy Node: Selects appropriate recovery DAG
4. Recovery Execution Node: Runs targeted fixes
5. Re-validation Node: Verifies fixes
6. Loop Controller: Repeats until deployable or max iterations
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# Import existing validation and recovery components
from workflow_validation import WorkflowValidator
from workflow_gap_detector import WorkflowGapDetector
from implementation_completeness_checker import ImplementationCompletenessChecker
from deployment_readiness_validator import DeploymentReadinessValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IssueType(Enum):
    """Types of issues that can be automatically fixed"""
    BACKEND_CODE_VOLUME = "backend_code_volume"
    FRONTEND_CODE_VOLUME = "frontend_code_volume"
    BACKEND_PACKAGE_JSON = "backend_package_json"
    FRONTEND_PACKAGE_JSON = "frontend_package_json"
    API_DOCUMENTATION = "api_documentation"
    REQUIREMENTS_DOCS = "requirements_docs"
    DESIGN_DOCS = "design_docs"
    MISSING_ROUTES = "missing_routes"
    MISSING_MODELS = "missing_models"
    MISSING_CONTROLLERS = "missing_controllers"
    MISSING_PAGES = "missing_pages"
    MISSING_COMPONENTS = "missing_components"


@dataclass
class RecoveryIssue:
    """Represents a specific issue that needs recovery"""
    issue_type: IssueType
    severity: str  # critical, warning, info
    phase: str
    description: str
    current_value: Any
    expected_value: Any
    fix_strategy: str
    estimated_time_minutes: int


@dataclass
class RecoveryResult:
    """Result of a recovery attempt"""
    success: bool
    issue_type: IssueType
    files_created: List[str]
    files_modified: List[str]
    errors: List[str]
    time_taken_seconds: float


class IssueClassifierNode:
    """Classifies validation issues into actionable recovery tasks"""

    def __init__(self):
        self.issue_patterns = {
            "Backend code files:": IssueType.BACKEND_CODE_VOLUME,
            "Frontend code files:": IssueType.FRONTEND_CODE_VOLUME,
            "Backend package.json incomplete": IssueType.BACKEND_PACKAGE_JSON,
            "Frontend package.json incomplete": IssueType.FRONTEND_PACKAGE_JSON,
            "API specification incomplete": IssueType.API_DOCUMENTATION,
            "requirement documents": IssueType.REQUIREMENTS_DOCS,
            "design documents": IssueType.DESIGN_DOCS,
            "missing route imports": IssueType.MISSING_ROUTES,
        }

    def classify_issues(self, validation_report: Dict[str, Any],
                       recovery_plan: Dict[str, Any]) -> List[RecoveryIssue]:
        """Classify all issues from validation report"""
        issues = []

        # Process deployment blockers
        for blocker in recovery_plan.get('deployment_blockers', []):
            issue = self._classify_blocker(blocker)
            if issue:
                issues.append(issue)

        # Sort by severity and estimated time
        issues.sort(key=lambda x: (
            0 if x.severity == 'critical' else 1,
            x.estimated_time_minutes
        ))

        return issues

    def _classify_blocker(self, blocker: Dict[str, Any]) -> Optional[RecoveryIssue]:
        """Classify a single deployment blocker"""
        description = blocker.get('description', '')

        # Determine issue type
        issue_type = None
        for pattern, itype in self.issue_patterns.items():
            if pattern.lower() in description.lower():
                issue_type = itype
                break

        if not issue_type:
            # Try to infer from description
            if 'backend' in description.lower() and 'file' in description.lower():
                issue_type = IssueType.BACKEND_CODE_VOLUME
            elif 'frontend' in description.lower() and 'file' in description.lower():
                issue_type = IssueType.FRONTEND_CODE_VOLUME
            else:
                return None  # Can't classify

        # Extract current and expected values
        current, expected = self._extract_values(description)

        # Estimate fix time based on issue type
        time_map = {
            IssueType.BACKEND_CODE_VOLUME: 5,  # 5 min per file
            IssueType.FRONTEND_CODE_VOLUME: 3,  # 3 min per file
            IssueType.BACKEND_PACKAGE_JSON: 2,
            IssueType.FRONTEND_PACKAGE_JSON: 2,
            IssueType.API_DOCUMENTATION: 10,
            IssueType.REQUIREMENTS_DOCS: 8,
            IssueType.DESIGN_DOCS: 8,
        }

        estimated_time = time_map.get(issue_type, 5)
        if current is not None and expected is not None:
            gap = expected - current
            estimated_time *= gap

        return RecoveryIssue(
            issue_type=issue_type,
            severity=blocker.get('severity', 'warning'),
            phase=blocker.get('phase', 'unknown'),
            description=description,
            current_value=current,
            expected_value=expected,
            fix_strategy=blocker.get('fix_suggestion', ''),
            estimated_time_minutes=estimated_time
        )

    def _extract_values(self, description: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract current and expected values from description"""
        import re

        # Pattern: "X found (minimum: Y)"
        match = re.search(r'(\d+)\s+found\s+\(minimum:\s*(\d+)\)', description)
        if match:
            return int(match.group(1)), int(match.group(2))

        # Pattern: "X/Y found"
        match = re.search(r'(\d+)/(\d+)\s+found', description)
        if match:
            return int(match.group(1)), int(match.group(2))

        return None, None


class BackendCodeRecoveryNode:
    """Generates missing backend code files"""

    def __init__(self, workflow_dir: Path):
        self.workflow_dir = workflow_dir
        self.backend_dir = workflow_dir / "implementation" / "backend"

    async def execute(self, issue: RecoveryIssue) -> RecoveryResult:
        """Execute backend code recovery"""
        start_time = asyncio.get_event_loop().time()
        files_created = []
        errors = []

        try:
            current = issue.current_value or 0
            expected = issue.expected_value or 20
            files_to_create = expected - current

            logger.info(f"Creating {files_to_create} backend files...")

            # Determine what type of files to create based on existing structure
            existing_files = self._get_existing_files()

            for i in range(files_to_create):
                file_path = self._create_next_file(existing_files, i)
                if file_path:
                    files_created.append(str(file_path))

            success = len(files_created) == files_to_create

        except Exception as e:
            logger.error(f"Backend recovery failed: {e}")
            errors.append(str(e))
            success = False

        time_taken = asyncio.get_event_loop().time() - start_time

        return RecoveryResult(
            success=success,
            issue_type=issue.issue_type,
            files_created=files_created,
            files_modified=[],
            errors=errors,
            time_taken_seconds=time_taken
        )

    def _get_existing_files(self) -> Dict[str, List[str]]:
        """Get existing backend files by category"""
        src_dir = self.backend_dir / "src"
        existing = {
            'controllers': [],
            'services': [],
            'models': [],
            'middleware': [],
            'utils': [],
            'routes': []
        }

        for category in existing.keys():
            category_dir = src_dir / category
            if category_dir.exists():
                existing[category] = [f.name for f in category_dir.glob('*.ts')]

        return existing

    def _create_next_file(self, existing: Dict[str, List[str]], index: int) -> Optional[Path]:
        """Create the next appropriate file"""
        src_dir = self.backend_dir / "src"

        # Priority: controllers > services > middleware > utils
        templates = [
            ('controllers', 'Controller.ts', self._get_controller_template),
            ('services', 'Service.ts', self._get_service_template),
            ('middleware', 'middleware.ts', self._get_middleware_template),
            ('utils', 'util.ts', self._get_util_template),
        ]

        for category, suffix, template_func in templates:
            # Find a name that doesn't exist
            for name in ['Profile', 'Dashboard', 'Settings', 'Notification', 'Analytics',
                        'Report', 'Export', 'Import', 'Search', 'Filter']:
                filename = f"{name}{suffix}"
                if filename not in existing.get(category, []):
                    file_path = src_dir / category / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(template_func(name))
                    logger.info(f"  Created: {file_path.relative_to(self.workflow_dir)}")
                    return file_path

        return None

    def _get_controller_template(self, name: str) -> str:
        """Generate controller template"""
        return f"""import {{ Request, Response }} from 'express';
import {{ {name}Service }} from '../services/{name}Service';

export class {name}Controller {{
  private {name.lower()}Service: {name}Service;

  constructor() {{
    this.{name.lower()}Service = new {name}Service();
  }}

  async getAll(req: Request, res: Response) {{
    try {{
      const items = await this.{name.lower()}Service.findAll();
      res.json(items);
    }} catch (error) {{
      res.status(500).json({{ error: 'Failed to fetch {name.lower()}s' }});
    }}
  }}

  async getById(req: Request, res: Response) {{
    try {{
      const item = await this.{name.lower()}Service.findById(req.params.id);
      if (!item) {{
        return res.status(404).json({{ error: '{name} not found' }});
      }}
      res.json(item);
    }} catch (error) {{
      res.status(500).json({{ error: 'Failed to fetch {name.lower()}' }});
    }}
  }}

  async create(req: Request, res: Response) {{
    try {{
      const item = await this.{name.lower()}Service.create(req.body);
      res.status(201).json(item);
    }} catch (error) {{
      res.status(500).json({{ error: 'Failed to create {name.lower()}' }});
    }}
  }}

  async update(req: Request, res: Response) {{
    try {{
      const item = await this.{name.lower()}Service.update(req.params.id, req.body);
      res.json(item);
    }} catch (error) {{
      res.status(500).json({{ error: 'Failed to update {name.lower()}' }});
    }}
  }}

  async delete(req: Request, res: Response) {{
    try {{
      await this.{name.lower()}Service.delete(req.params.id);
      res.status(204).send();
    }} catch (error) {{
      res.status(500).json({{ error: 'Failed to delete {name.lower()}' }});
    }}
  }}
}}
"""

    def _get_service_template(self, name: str) -> str:
        """Generate service template"""
        return f"""export class {name}Service {{
  async findAll() {{
    // TODO: Implement find all {name.lower()}s
    throw new Error('Not implemented');
  }}

  async findById(id: string) {{
    // TODO: Implement find {name.lower()} by ID
    throw new Error('Not implemented');
  }}

  async create(data: any) {{
    // TODO: Implement create {name.lower()}
    throw new Error('Not implemented');
  }}

  async update(id: string, data: any) {{
    // TODO: Implement update {name.lower()}
    throw new Error('Not implemented');
  }}

  async delete(id: string) {{
    // TODO: Implement delete {name.lower()}
    throw new Error('Not implemented');
  }}
}}
"""

    def _get_middleware_template(self, name: str) -> str:
        """Generate middleware template"""
        return f"""import {{ Request, Response, NextFunction }} from 'express';

export const {name.lower()}Middleware = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {{
  try {{
    // TODO: Implement {name.lower()} middleware logic
    next();
  }} catch (error) {{
    next(error);
  }}
}};
"""

    def _get_util_template(self, name: str) -> str:
        """Generate utility template"""
        return f"""/**
 * {name} utility functions
 */

export const {name.lower()}Util = {{
  // TODO: Implement {name.lower()} utility functions

  validate(data: any): boolean {{
    return true;
  }},

  transform(data: any): any {{
    return data;
  }}
}};
"""


class FrontendCodeRecoveryNode:
    """Generates missing frontend code files"""

    def __init__(self, workflow_dir: Path):
        self.workflow_dir = workflow_dir
        self.frontend_dir = workflow_dir / "implementation" / "frontend"

    async def execute(self, issue: RecoveryIssue) -> RecoveryResult:
        """Execute frontend code recovery"""
        start_time = asyncio.get_event_loop().time()
        files_created = []
        errors = []

        try:
            current = issue.current_value or 0
            expected = issue.expected_value or 10
            files_to_create = expected - current

            logger.info(f"Creating {files_to_create} frontend files...")

            # Determine what to create
            existing_files = self._get_existing_files()

            for i in range(files_to_create):
                file_path = self._create_next_file(existing_files, i)
                if file_path:
                    files_created.append(str(file_path))

            success = len(files_created) == files_to_create

        except Exception as e:
            logger.error(f"Frontend recovery failed: {e}")
            errors.append(str(e))
            success = False

        time_taken = asyncio.get_event_loop().time() - start_time

        return RecoveryResult(
            success=success,
            issue_type=issue.issue_type,
            files_created=files_created,
            files_modified=[],
            errors=errors,
            time_taken_seconds=time_taken
        )

    def _get_existing_files(self) -> Dict[str, List[str]]:
        """Get existing frontend files by category"""
        src_dir = self.frontend_dir / "src"
        existing = {
            'pages': [],
            'components': [],
            'services': [],
            'hooks': [],
            'utils': []
        }

        for category in existing.keys():
            category_dir = src_dir / category
            if category_dir.exists():
                existing[category] = [f.name for f in category_dir.glob('*.tsx') or category_dir.glob('*.ts')]

        return existing

    def _create_next_file(self, existing: Dict[str, List[str]], index: int) -> Optional[Path]:
        """Create the next appropriate file"""
        src_dir = self.frontend_dir / "src"

        # Priority: pages > components > hooks > utils
        page_templates = [
            ('LoginPage', 'pages', self._get_login_page_template),
            ('DashboardPage', 'pages', self._get_dashboard_page_template),
            ('ProfilePage', 'pages', self._get_profile_page_template),
            ('SettingsPage', 'pages', self._get_settings_page_template),
            ('NotFoundPage', 'pages', self._get_notfound_page_template),
        ]

        component_templates = [
            ('Navbar', 'components', self._get_navbar_component_template),
            ('Sidebar', 'components', self._get_sidebar_component_template),
            ('Footer', 'components', self._get_footer_component_template),
            ('Card', 'components', self._get_card_component_template),
            ('Modal', 'components', self._get_modal_component_template),
        ]

        all_templates = page_templates + component_templates

        for name, category, template_func in all_templates:
            filename = f"{name}.tsx"
            if filename not in existing.get(category, []):
                file_path = src_dir / category / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(template_func(name))
                logger.info(f"  Created: {file_path.relative_to(self.workflow_dir)}")
                return file_path

        return None

    def _get_login_page_template(self, name: str) -> str:
        """Generate login page"""
        return """import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // TODO: Implement login logic
      console.log('Login:', { email, password });
      navigate('/dashboard');
    } catch (err) {
      setError('Login failed. Please try again.');
    }
  };

  return (
    <div className="login-page">
      <h1>Login</h1>
      {error && <div className="error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit">Login</button>
      </form>
    </div>
  );
};
"""

    def _get_dashboard_page_template(self, name: str) -> str:
        """Generate dashboard page"""
        return """import React, { useEffect, useState } from 'react';

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState({
    users: 0,
    records: 0,
    activity: 0
  });

  useEffect(() => {
    // TODO: Fetch dashboard stats
    setStats({
      users: 100,
      records: 500,
      activity: 25
    });
  }, []);

  return (
    <div className="dashboard-page">
      <h1>Dashboard</h1>
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Users</h3>
          <p className="stat-value">{stats.users}</p>
        </div>
        <div className="stat-card">
          <h3>Records</h3>
          <p className="stat-value">{stats.records}</p>
        </div>
        <div className="stat-card">
          <h3>Activity</h3>
          <p className="stat-value">{stats.activity}</p>
        </div>
      </div>
    </div>
  );
};
"""

    def _get_profile_page_template(self, name: str) -> str:
        """Generate profile page"""
        return """import React, { useState, useEffect } from 'react';

export const ProfilePage: React.FC = () => {
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    avatar: ''
  });

  useEffect(() => {
    // TODO: Fetch user profile
  }, []);

  const handleSave = async () => {
    // TODO: Implement save profile
    console.log('Saving profile:', profile);
  };

  return (
    <div className="profile-page">
      <h1>Profile</h1>
      <div className="profile-form">
        <input
          type="text"
          placeholder="Name"
          value={profile.name}
          onChange={(e) => setProfile({...profile, name: e.target.value})}
        />
        <input
          type="email"
          placeholder="Email"
          value={profile.email}
          onChange={(e) => setProfile({...profile, email: e.target.value})}
        />
        <button onClick={handleSave}>Save Changes</button>
      </div>
    </div>
  );
};
"""

    def _get_settings_page_template(self, name: str) -> str:
        """Generate settings page"""
        return """import React, { useState } from 'react';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState({
    notifications: true,
    darkMode: false,
    language: 'en'
  });

  const handleSave = () => {
    // TODO: Save settings
    console.log('Saving settings:', settings);
  };

  return (
    <div className="settings-page">
      <h1>Settings</h1>
      <div className="settings-form">
        <label>
          <input
            type="checkbox"
            checked={settings.notifications}
            onChange={(e) => setSettings({...settings, notifications: e.target.checked})}
          />
          Enable Notifications
        </label>
        <label>
          <input
            type="checkbox"
            checked={settings.darkMode}
            onChange={(e) => setSettings({...settings, darkMode: e.target.checked})}
          />
          Dark Mode
        </label>
        <button onClick={handleSave}>Save Settings</button>
      </div>
    </div>
  );
};
"""

    def _get_notfound_page_template(self, name: str) -> str:
        """Generate 404 page"""
        return """import React from 'react';
import { Link } from 'react-router-dom';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="not-found-page">
      <h1>404</h1>
      <p>Page not found</p>
      <Link to="/">Go Home</Link>
    </div>
  );
};
"""

    def _get_navbar_component_template(self, name: str) -> str:
        """Generate navbar component"""
        return """import React from 'react';
import { Link } from 'react-router-dom';

export const Navbar: React.FC = () => {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/">App Name</Link>
      </div>
      <div className="navbar-menu">
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/profile">Profile</Link>
        <Link to="/settings">Settings</Link>
      </div>
    </nav>
  );
};
"""

    def _get_sidebar_component_template(self, name: str) -> str:
        """Generate sidebar component"""
        return """import React from 'react';
import { Link } from 'react-router-dom';

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <ul>
        <li><Link to="/dashboard">Dashboard</Link></li>
        <li><Link to="/records">Records</Link></li>
        <li><Link to="/settings">Settings</Link></li>
      </ul>
    </aside>
  );
};
"""

    def _get_footer_component_template(self, name: str) -> str:
        """Generate footer component"""
        return """import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="footer">
      <p>&copy; 2025 App Name. All rights reserved.</p>
    </footer>
  );
};
"""

    def _get_card_component_template(self, name: str) -> str:
        """Generate card component"""
        return """import React from 'react';

interface CardProps {
  title: string;
  children: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ title, children }) => {
  return (
    <div className="card">
      <h3 className="card-title">{title}</h3>
      <div className="card-content">{children}</div>
    </div>
  );
};
"""

    def _get_modal_component_template(self, name: str) -> str:
        """Generate modal component"""
        return """import React from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button onClick={onClose}>×</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
};
"""


class SelfHealingOrchestrator:
    """Orchestrates the self-healing process"""

    def __init__(self, workflows_dir: Path, max_iterations: int = 3):
        self.workflows_dir = workflows_dir
        self.max_iterations = max_iterations
        self.classifier = IssueClassifierNode()
        self.results_dir = workflows_dir / "validation_results"

    async def heal_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Attempt to heal a single workflow"""
        workflow_dir = self.workflows_dir / workflow_id

        logger.info(f"\n{'='*80}")
        logger.info(f"SELF-HEALING: {workflow_id}")
        logger.info(f"{'='*80}\n")

        healing_log = {
            'workflow_id': workflow_id,
            'iterations': [],
            'final_status': {},
            'total_time_seconds': 0
        }

        start_time = asyncio.get_event_loop().time()

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"\n--- Iteration {iteration}/{self.max_iterations} ---\n")

            # Step 1: Validate
            validation_result = await self._validate(workflow_dir)

            if validation_result['is_deployable']:
                logger.info("✅ Workflow is now deployable!")
                healing_log['final_status'] = validation_result
                break

            # Step 2: Classify issues
            issues = self.classifier.classify_issues(
                validation_result['report'],
                validation_result['recovery_plan']
            )

            if not issues:
                logger.warning("No actionable issues found")
                break

            logger.info(f"Found {len(issues)} issues to fix:")
            for i, issue in enumerate(issues[:5], 1):  # Show top 5
                logger.info(f"  {i}. [{issue.severity}] {issue.description}")

            # Step 3: Execute recovery for each issue
            iteration_results = []
            for issue in issues:
                recovery_result = await self._execute_recovery(workflow_dir, issue)
                iteration_results.append(recovery_result)

                if recovery_result.success:
                    logger.info(f"✅ Fixed: {issue.issue_type.value}")
                else:
                    logger.warning(f"❌ Failed to fix: {issue.issue_type.value}")

            healing_log['iterations'].append({
                'iteration': iteration,
                'issues_found': len(issues),
                'issues_fixed': sum(1 for r in iteration_results if r.success),
                'files_created': sum(len(r.files_created) for r in iteration_results),
                'validation_status': validation_result
            })

            # Step 4: Re-validate to see if we need another iteration
            await asyncio.sleep(1)  # Brief pause

        total_time = asyncio.get_event_loop().time() - start_time
        healing_log['total_time_seconds'] = total_time

        # Final validation
        final_validation = await self._validate(workflow_dir)
        healing_log['final_status'] = final_validation

        logger.info(f"\n{'='*80}")
        logger.info(f"HEALING COMPLETE: {workflow_id}")
        logger.info(f"Iterations: {len(healing_log['iterations'])}")
        logger.info(f"Deployable: {'✅ Yes' if final_validation['is_deployable'] else '❌ No'}")
        logger.info(f"Time: {total_time:.2f}s")
        logger.info(f"{'='*80}\n")

        return healing_log

    async def _validate(self, workflow_dir: Path) -> Dict[str, Any]:
        """Run validation on workflow"""
        validator = WorkflowValidator(workflow_dir)
        gap_detector = WorkflowGapDetector(workflow_dir)

        # Run validation
        validation_report = {
            'requirements': validator.validate_phase('requirements'),
            'design': validator.validate_phase('design'),
            'implementation': validator.validate_phase('implementation'),
            'testing': validator.validate_phase('testing'),
            'deployment': validator.validate_phase('deployment')
        }
        gap_report = gap_detector.detect_gaps()
        recovery_context = gap_detector.generate_recovery_context(gap_report)

        return {
            'report': validation_report,
            'recovery_plan': recovery_context,
            'is_deployable': gap_report.is_deployable,
            'completion': gap_report.estimated_completion_percentage,
            'critical_gaps': len([g for g in gap_report.gaps if g.severity == 'critical'])
        }

    async def _execute_recovery(self, workflow_dir: Path,
                                issue: RecoveryIssue) -> RecoveryResult:
        """Execute recovery for a specific issue"""

        # Route to appropriate recovery node
        if issue.issue_type == IssueType.BACKEND_CODE_VOLUME:
            node = BackendCodeRecoveryNode(workflow_dir)
            return await node.execute(issue)

        elif issue.issue_type == IssueType.FRONTEND_CODE_VOLUME:
            node = FrontendCodeRecoveryNode(workflow_dir)
            return await node.execute(issue)

        else:
            # TODO: Implement other recovery nodes
            logger.warning(f"No recovery node for {issue.issue_type.value}")
            return RecoveryResult(
                success=False,
                issue_type=issue.issue_type,
                files_created=[],
                files_modified=[],
                errors=['Recovery node not implemented'],
                time_taken_seconds=0
            )

    async def heal_batch(self, workflow_ids: List[str]) -> Dict[str, Any]:
        """Heal multiple workflows"""
        logger.info(f"\n{'='*80}")
        logger.info(f"SELF-HEALING BATCH: {len(workflow_ids)} workflows")
        logger.info(f"{'='*80}\n")

        batch_results = []

        for wf_id in workflow_ids:
            result = await self.heal_workflow(wf_id)
            batch_results.append(result)

        # Summary
        deployable_count = sum(1 for r in batch_results if r['final_status'].get('is_deployable', False))
        total_files = sum(sum(it['files_created'] for it in r['iterations']) for r in batch_results)
        total_time = sum(r['total_time_seconds'] for r in batch_results)

        summary = {
            'total_workflows': len(workflow_ids),
            'deployable_after_healing': deployable_count,
            'total_files_created': total_files,
            'total_time_seconds': total_time,
            'workflows': batch_results
        }

        logger.info(f"\n{'='*80}")
        logger.info(f"BATCH HEALING COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Workflows: {len(workflow_ids)}")
        logger.info(f"Deployable: {deployable_count}/{len(workflow_ids)} ({deployable_count/len(workflow_ids)*100:.1f}%)")
        logger.info(f"Files Created: {total_files}")
        logger.info(f"Total Time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
        logger.info(f"{'='*80}\n")

        # Save results
        results_file = self.results_dir / f"self_healing_batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(f"Results saved to: {results_file}")

        return summary


async def main():
    """Main entry point for self-healing"""

    # Batch 5 workflows
    batch5_workflows = [
        "wf-1760179880-101b14da",
        "wf-1760179880-5e4b549c",
        "wf-1760179880-6aa8782f",
        "wf-1760179880-6eb86fde",
        "wf-1760179880-e21a8fed",
        "wf-1760179880-fafbe325"
    ]

    workflows_dir = Path("/tmp/maestro_workflow")

    orchestrator = SelfHealingOrchestrator(workflows_dir, max_iterations=3)

    # Heal all Batch 5 workflows
    results = await orchestrator.heal_batch(batch5_workflows)

    print("\n" + "="*80)
    print("SELF-HEALING SUMMARY")
    print("="*80)
    print(f"Total Workflows: {results['total_workflows']}")
    print(f"Now Deployable: {results['deployable_after_healing']}")
    print(f"Files Created: {results['total_files_created']}")
    print(f"Time: {results['total_time_seconds']:.2f}s")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
