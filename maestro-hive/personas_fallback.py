"""
Fallback Persona Definitions

This module provides basic persona definitions when maestro-engine is not available.
These are simplified versions for testing and demonstration purposes.
"""

from typing import Dict, List, Any


class SDLCPersonasFallback:
    """
    Fallback persona definitions for SDLC team.
    
    Used when maestro-engine is not available.
    """
    
    @staticmethod
    def get_all_personas() -> Dict[str, Dict[str, Any]]:
        """Get all persona definitions"""
        return {
            "requirement_analyst": SDLCPersonasFallback.requirement_analyst(),
            "solution_architect": SDLCPersonasFallback.solution_architect(),
            "frontend_developer": SDLCPersonasFallback.frontend_developer(),
            "backend_developer": SDLCPersonasFallback.backend_developer(),
            "devops_engineer": SDLCPersonasFallback.devops_engineer(),
            "qa_engineer": SDLCPersonasFallback.qa_engineer(),
            "security_specialist": SDLCPersonasFallback.security_specialist(),
            "ui_ux_designer": SDLCPersonasFallback.ui_ux_designer(),
            "technical_writer": SDLCPersonasFallback.technical_writer(),
            "deployment_specialist": SDLCPersonasFallback.deployment_specialist(),
            "deployment_integration_tester": SDLCPersonasFallback.deployment_specialist(),
            "database_specialist": SDLCPersonasFallback.database_specialist(),
            "test_engineer": SDLCPersonasFallback.test_engineer(),
        }
    
    @staticmethod
    def requirement_analyst() -> Dict[str, Any]:
        return {
            "id": "requirement_analyst",
            "name": "Requirements Analyst",
            "role": "Requirements Analyst",
            "expertise": ["requirement_analysis", "user_stories", "acceptance_criteria"],
            "responsibilities": [
                "Analyze and document requirements",
                "Create user stories",
                "Define acceptance criteria",
                "Identify stakeholders"
            ],
            "deliverables": [
                "requirements_document",
                "user_stories",
                "acceptance_criteria"
            ]
        }
    
    @staticmethod
    def solution_architect() -> Dict[str, Any]:
        return {
            "id": "solution_architect",
            "name": "Solution Architect",
            "role": "Solution Architect",
            "expertise": ["architecture_design", "system_design", "technology_selection"],
            "responsibilities": [
                "Design system architecture",
                "Select technologies",
                "Define interfaces",
                "Create architecture diagrams"
            ],
            "deliverables": [
                "architecture_document",
                "system_diagrams",
                "technology_stack"
            ]
        }
    
    @staticmethod
    def frontend_developer() -> Dict[str, Any]:
        return {
            "id": "frontend_developer",
            "name": "Frontend Developer",
            "role": "Frontend Developer",
            "expertise": ["react", "typescript", "css", "html", "ui_development"],
            "responsibilities": [
                "Develop user interfaces",
                "Implement UI components",
                "Integrate with backend APIs",
                "Ensure responsive design"
            ],
            "deliverables": [
                "ui_components",
                "frontend_code",
                "style_sheets",
                "integration_code"
            ]
        }
    
    @staticmethod
    def backend_developer() -> Dict[str, Any]:
        return {
            "id": "backend_developer",
            "name": "Backend Developer",
            "role": "Backend Developer",
            "expertise": ["nodejs", "python", "rest_api", "database", "microservices"],
            "responsibilities": [
                "Develop backend services",
                "Implement REST APIs",
                "Design database schemas",
                "Write business logic"
            ],
            "deliverables": [
                "api_endpoints",
                "backend_code",
                "database_schema",
                "api_documentation"
            ]
        }
    
    @staticmethod
    def devops_engineer() -> Dict[str, Any]:
        return {
            "id": "devops_engineer",
            "name": "DevOps Engineer",
            "role": "DevOps Engineer",
            "expertise": ["docker", "kubernetes", "ci_cd", "cloud", "automation"],
            "responsibilities": [
                "Setup CI/CD pipelines",
                "Configure deployment",
                "Manage infrastructure",
                "Monitor systems"
            ],
            "deliverables": [
                "docker_files",
                "ci_cd_config",
                "deployment_scripts",
                "infrastructure_code"
            ]
        }
    
    @staticmethod
    def qa_engineer() -> Dict[str, Any]:
        return {
            "id": "qa_engineer",
            "name": "QA Engineer",
            "role": "QA Engineer",
            "expertise": ["testing", "test_automation", "quality_assurance", "bug_tracking"],
            "responsibilities": [
                "Create test plans",
                "Write test cases",
                "Execute tests",
                "Report bugs"
            ],
            "deliverables": [
                "test_plan",
                "test_cases",
                "test_results",
                "bug_reports"
            ]
        }
    
    @staticmethod
    def security_specialist() -> Dict[str, Any]:
        return {
            "id": "security_specialist",
            "name": "Security Specialist",
            "role": "Security Specialist",
            "expertise": ["security", "vulnerability_assessment", "penetration_testing"],
            "responsibilities": [
                "Conduct security audits",
                "Identify vulnerabilities",
                "Recommend security measures",
                "Review code for security issues"
            ],
            "deliverables": [
                "security_audit_report",
                "vulnerability_report",
                "security_recommendations"
            ]
        }
    
    @staticmethod
    def ui_ux_designer() -> Dict[str, Any]:
        return {
            "id": "ui_ux_designer",
            "name": "UI/UX Designer",
            "role": "UI/UX Designer",
            "expertise": ["ui_design", "ux_design", "prototyping", "user_research"],
            "responsibilities": [
                "Design user interfaces",
                "Create prototypes",
                "Conduct user research",
                "Define user flows"
            ],
            "deliverables": [
                "ui_designs",
                "prototypes",
                "user_flows",
                "design_system"
            ]
        }
    
    @staticmethod
    def technical_writer() -> Dict[str, Any]:
        return {
            "id": "technical_writer",
            "name": "Technical Writer",
            "role": "Technical Writer",
            "expertise": ["technical_writing", "documentation", "api_documentation"],
            "responsibilities": [
                "Write documentation",
                "Create user guides",
                "Document APIs",
                "Maintain documentation"
            ],
            "deliverables": [
                "user_documentation",
                "api_documentation",
                "technical_guides",
                "readme_files"
            ]
        }
    
    @staticmethod
    def deployment_specialist() -> Dict[str, Any]:
        return {
            "id": "deployment_specialist",
            "name": "Deployment Specialist",
            "role": "Deployment Specialist",
            "expertise": ["deployment", "release_management", "integration"],
            "responsibilities": [
                "Plan deployments",
                "Execute releases",
                "Perform integration testing",
                "Manage rollbacks"
            ],
            "deliverables": [
                "deployment_plan",
                "release_notes",
                "integration_tests",
                "rollback_procedures"
            ]
        }
    
    @staticmethod
    def deployment_integration_tester() -> Dict[str, Any]:
        """Alias for deployment_specialist"""
        return SDLCPersonasFallback.deployment_specialist()
    
    @staticmethod
    def database_specialist() -> Dict[str, Any]:
        return {
            "id": "database_specialist",
            "name": "Database Specialist",
            "role": "Database Specialist",
            "expertise": ["database_design", "sql", "performance_tuning", "data_modeling"],
            "responsibilities": [
                "Design database schemas",
                "Optimize queries",
                "Manage data migrations",
                "Ensure data integrity"
            ],
            "deliverables": [
                "database_schema",
                "migration_scripts",
                "query_optimization",
                "data_model"
            ]
        }
    
    @staticmethod
    def test_engineer() -> Dict[str, Any]:
        """Alias for qa_engineer"""
        return SDLCPersonasFallback.qa_engineer()


# Alias for compatibility
SDLCPersonas = SDLCPersonasFallback
