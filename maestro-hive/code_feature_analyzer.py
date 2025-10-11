#!/usr/bin/env python3
"""
Code Feature Analyzer - Week 7-8 Requirements Traceability

Analyzes implemented code and extracts features through reverse engineering.
Works without PRD by identifying patterns in code structure.

Key Features:
- Extract API endpoints from backend routes
- Extract database models and entities
- Extract UI components from frontend
- Group related code into features
- Estimate feature completeness
- Pattern recognition for common features
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)


class FeatureCategory(Enum):
    """Common feature categories"""
    AUTHENTICATION = "authentication"
    USER_MANAGEMENT = "user_management"
    CRUD_OPERATIONS = "crud_operations"
    SEARCH = "search"
    FILE_UPLOAD = "file_upload"
    ADMIN = "admin"
    REPORTING = "reporting"
    NOTIFICATION = "notification"
    PAYMENT = "payment"
    INTEGRATION = "integration"
    OTHER = "other"


@dataclass
class APIEndpoint:
    """Represents an API endpoint"""
    method: str  # GET, POST, PUT, DELETE
    path: str  # /api/users/:id
    file: str  # backend/src/routes/user.routes.ts
    handler: Optional[str] = None  # getUserById
    middleware: List[str] = field(default_factory=list)  # ['authMiddleware']


@dataclass
class DatabaseModel:
    """Represents a database model/entity"""
    name: str  # User
    fields: List[str]  # ['id', 'email', 'name']
    file: str  # backend/src/models/User.ts
    relations: List[str] = field(default_factory=list)  # ['Post', 'Comment']


@dataclass
class UIComponent:
    """Represents a UI component"""
    name: str  # UserList
    type: str  # 'page' | 'component' | 'form'
    file: str  # frontend/src/pages/Users.tsx
    props: List[str] = field(default_factory=list)  # ['userId', 'onSave']
    apis_used: List[str] = field(default_factory=list)  # ['/api/users']


@dataclass
class CodeFeature:
    """Represents a feature extracted from code"""
    id: str  # IMPL-1
    name: str  # "User Management"
    category: FeatureCategory
    confidence: float  # 0.0 - 1.0
    endpoints: List[APIEndpoint] = field(default_factory=list)
    models: List[DatabaseModel] = field(default_factory=list)
    components: List[UIComponent] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    completeness: float = 0.0  # 0.0 - 1.0
    has_tests: bool = False
    has_validation: bool = False
    has_error_handling: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['category'] = self.category.value
        return data


class CodeFeatureAnalyzer:
    """Analyzes code to extract implemented features"""

    def __init__(self, impl_dir: Path):
        self.impl_dir = impl_dir
        self.backend_dir = impl_dir / "backend"
        self.frontend_dir = impl_dir / "frontend"
        self.features: List[CodeFeature] = []

    async def analyze(self) -> List[CodeFeature]:
        """Run complete code analysis"""
        logger.info(f"🔍 Analyzing code in {self.impl_dir}")

        # Extract all code elements
        endpoints = await self.extract_endpoints()
        models = await self.extract_models()
        components = await self.extract_components()
        test_files = await self.find_test_files()

        logger.info(f"  Found {len(endpoints)} endpoints")
        logger.info(f"  Found {len(models)} models")
        logger.info(f"  Found {len(components)} components")
        logger.info(f"  Found {len(test_files)} test files")

        # Group into features
        self.features = await self.group_into_features(
            endpoints, models, components, test_files
        )

        logger.info(f"✅ Identified {len(self.features)} features")

        return self.features

    async def extract_endpoints(self) -> List[APIEndpoint]:
        """Extract API endpoints from backend route files"""
        endpoints = []

        if not self.backend_dir.exists():
            logger.warning("  No backend directory found")
            return endpoints

        # Find route files
        route_files = list(self.backend_dir.rglob("*route*.ts")) + \
                     list(self.backend_dir.rglob("*route*.js")) + \
                     list(self.backend_dir.rglob("*routes.ts")) + \
                     list(self.backend_dir.rglob("*routes.js"))

        for file in route_files:
            try:
                content = file.read_text()
                file_endpoints = self._parse_endpoints_from_file(content, str(file.relative_to(self.impl_dir)))
                endpoints.extend(file_endpoints)
            except Exception as e:
                logger.debug(f"  Error parsing {file.name}: {e}")

        return endpoints

    def _parse_endpoints_from_file(self, content: str, file_path: str) -> List[APIEndpoint]:
        """Parse endpoints from route file content"""
        endpoints = []

        # Pattern 1: router.get('/path', handler)
        # Pattern 2: app.post('/path', middleware, handler)
        # Pattern 3: route.put('/path', ...)
        patterns = [
            r'(?:router|app|route)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            r'\.(?:get|post|put|delete|patch)\s*\(["\']([^"\']+)["\']'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:
                    method, path = match.groups()
                    method = method.upper()
                elif len(match.groups()) == 1:
                    # Guess method from context
                    method = "GET"
                    path = match.group(1)
                else:
                    continue

                # Clean up path
                path = path.strip()
                if not path.startswith('/'):
                    path = '/' + path

                endpoints.append(APIEndpoint(
                    method=method,
                    path=path,
                    file=file_path
                ))

        return endpoints

    async def extract_models(self) -> List[DatabaseModel]:
        """Extract database models from backend"""
        models = []

        if not self.backend_dir.exists():
            return models

        # Find model files
        model_dirs = [
            self.backend_dir / "src" / "models",
            self.backend_dir / "models",
            self.backend_dir / "src" / "entities"
        ]

        model_files = []
        for model_dir in model_dirs:
            if model_dir.exists():
                model_files.extend(list(model_dir.glob("*.ts")))
                model_files.extend(list(model_dir.glob("*.js")))

        for file in model_files:
            try:
                content = file.read_text()
                file_models = self._parse_models_from_file(content, str(file.relative_to(self.impl_dir)))
                models.extend(file_models)
            except Exception as e:
                logger.debug(f"  Error parsing {file.name}: {e}")

        return models

    def _parse_models_from_file(self, content: str, file_path: str) -> List[DatabaseModel]:
        """Parse models from model file content"""
        models = []

        # Pattern 1: interface User { ... }
        # Pattern 2: class User { ... }
        # Pattern 3: type User = { ... }

        # Find interface/class/type declarations
        patterns = [
            r'(?:interface|class|type)\s+(\w+)\s*(?:extends\s+\w+)?\s*\{([^}]+)\}',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                model_name = match.group(1)
                body = match.group(2)

                # Extract field names
                fields = []
                field_pattern = r'(\w+)[\s:?]'
                for field_match in re.finditer(field_pattern, body):
                    field_name = field_match.group(1)
                    if field_name not in ['constructor', 'function', 'return']:
                        fields.append(field_name)

                if fields:  # Only add if we found fields
                    models.append(DatabaseModel(
                        name=model_name,
                        fields=fields[:10],  # Limit to first 10 fields
                        file=file_path
                    ))

        return models

    async def extract_components(self) -> List[UIComponent]:
        """Extract UI components from frontend"""
        components = []

        if not self.frontend_dir.exists():
            logger.warning("  No frontend directory found")
            return components

        # Find component files
        component_files = list(self.frontend_dir.rglob("*.tsx")) + \
                         list(self.frontend_dir.rglob("*.jsx"))

        for file in component_files:
            try:
                content = file.read_text()
                file_components = self._parse_components_from_file(content, str(file.relative_to(self.impl_dir)))
                components.extend(file_components)
            except Exception as e:
                logger.debug(f"  Error parsing {file.name}: {e}")

        return components

    def _parse_components_from_file(self, content: str, file_path: str) -> List[UIComponent]:
        """Parse components from React file content"""
        components = []

        # Pattern 1: function ComponentName() { ... }
        # Pattern 2: const ComponentName = () => { ... }
        # Pattern 3: export default function ComponentName() { ... }

        patterns = [
            r'(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)',
            r'(?:export\s+)?const\s+([A-Z]\w+)\s*=\s*\(',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                component_name = match.group(1)

                # Determine type
                comp_type = "component"
                if "page" in file_path.lower() or "pages" in file_path.lower():
                    comp_type = "page"
                elif "form" in component_name.lower():
                    comp_type = "form"

                # Extract API calls
                apis_used = []
                api_patterns = [
                    r'fetch\s*\(\s*["`\']([^"`\']+)["`\']',
                    r'axios\.(?:get|post|put|delete)\s*\(\s*["`\']([^"`\']+)["`\']',
                ]
                for api_pattern in api_patterns:
                    for api_match in re.finditer(api_pattern, content):
                        apis_used.append(api_match.group(1))

                components.append(UIComponent(
                    name=component_name,
                    type=comp_type,
                    file=file_path,
                    apis_used=list(set(apis_used))  # Deduplicate
                ))

        return components

    async def find_test_files(self) -> List[str]:
        """Find test files in implementation"""
        test_files = []

        # Common test file patterns
        test_patterns = ["*test.ts", "*test.js", "*.spec.ts", "*.spec.js"]

        for pattern in test_patterns:
            test_files.extend([str(f.relative_to(self.impl_dir)) for f in self.impl_dir.rglob(pattern)])

        return test_files

    async def group_into_features(
        self,
        endpoints: List[APIEndpoint],
        models: List[DatabaseModel],
        components: List[UIComponent],
        test_files: List[str]
    ) -> List[CodeFeature]:
        """Group code elements into logical features"""
        features = []
        feature_id = 1

        # Strategy: Group by base resource path
        # /api/users, /api/users/:id -> "User Management"
        # /api/auth/* -> "Authentication"

        # Extract base paths from endpoints
        base_paths: Dict[str, List[APIEndpoint]] = {}
        for endpoint in endpoints:
            base = self._extract_base_path(endpoint.path)
            if base not in base_paths:
                base_paths[base] = []
            base_paths[base].append(endpoint)

        # Create features from base paths
        for base_path, path_endpoints in base_paths.items():
            feature_name = self._generate_feature_name(base_path)
            category = self._identify_category(base_path, path_endpoints)

            # Find related models
            related_models = self._find_related_models(base_path, models)

            # Find related components
            related_components = self._find_related_components(base_path, components, path_endpoints)

            # Find related tests
            related_tests = self._find_related_tests(base_path, test_files)

            # Calculate completeness
            completeness = self._calculate_completeness(
                path_endpoints, related_models, related_components, related_tests
            )

            # Calculate confidence
            confidence = self._calculate_confidence(
                path_endpoints, related_models, related_components
            )

            feature = CodeFeature(
                id=f"IMPL-{feature_id}",
                name=feature_name,
                category=category,
                confidence=confidence,
                endpoints=path_endpoints,
                models=related_models,
                components=related_components,
                test_files=related_tests,
                completeness=completeness,
                has_tests=len(related_tests) > 0,
                has_validation=any('validation' in e.file.lower() for e in path_endpoints),
                has_error_handling=True  # Assume true for now
            )

            features.append(feature)
            feature_id += 1

        return features

    def _extract_base_path(self, path: str) -> str:
        """Extract base resource path from endpoint"""
        # /api/users/:id -> /api/users
        # /api/auth/login -> /api/auth

        parts = path.split('/')
        # Remove empty parts and parameters
        filtered = [p for p in parts if p and not p.startswith(':')]

        # Take first 3 parts (/api/resource)
        if len(filtered) >= 3:
            return '/' + '/'.join(filtered[:3])
        elif len(filtered) >= 2:
            return '/' + '/'.join(filtered[:2])
        else:
            return path

    def _generate_feature_name(self, base_path: str) -> str:
        """Generate human-readable feature name from base path"""
        # /api/users -> "User Management"
        # /api/auth -> "Authentication"

        parts = [p for p in base_path.split('/') if p]
        if not parts:
            return "Unknown Feature"

        resource = parts[-1]

        # Special cases
        if resource == 'auth':
            return "Authentication"
        elif resource == 'admin':
            return "Admin Panel"

        # Convert to title case
        name = resource.replace('_', ' ').replace('-', ' ').title()

        # Singularize if plural
        if name.endswith('s'):
            name = name[:-1]

        return f"{name} Management"

    def _identify_category(self, base_path: str, endpoints: List[APIEndpoint]) -> FeatureCategory:
        """Identify feature category from path and endpoints"""
        path_lower = base_path.lower()

        # Check path keywords
        if 'auth' in path_lower or 'login' in path_lower:
            return FeatureCategory.AUTHENTICATION
        elif 'user' in path_lower:
            return FeatureCategory.USER_MANAGEMENT
        elif 'search' in path_lower:
            return FeatureCategory.SEARCH
        elif 'upload' in path_lower or 'file' in path_lower:
            return FeatureCategory.FILE_UPLOAD
        elif 'admin' in path_lower:
            return FeatureCategory.ADMIN
        elif 'report' in path_lower:
            return FeatureCategory.REPORTING
        elif 'notification' in path_lower or 'notify' in path_lower:
            return FeatureCategory.NOTIFICATION
        elif 'payment' in path_lower or 'pay' in path_lower:
            return FeatureCategory.PAYMENT

        # Check if CRUD (has GET, POST, PUT/DELETE)
        methods = {e.method for e in endpoints}
        if {'GET', 'POST'}.issubset(methods):
            return FeatureCategory.CRUD_OPERATIONS

        return FeatureCategory.OTHER

    def _find_related_models(self, base_path: str, models: List[DatabaseModel]) -> List[DatabaseModel]:
        """Find models related to a base path"""
        related = []

        # Extract resource name from path
        resource = base_path.split('/')[-1]
        resource_clean = resource.replace('_', '').replace('-', '').lower()

        for model in models:
            model_clean = model.name.lower()
            # Check if model name contains resource name or vice versa
            if resource_clean in model_clean or model_clean in resource_clean:
                related.append(model)

        return related

    def _find_related_components(
        self,
        base_path: str,
        components: List[UIComponent],
        endpoints: List[APIEndpoint]
    ) -> List[UIComponent]:
        """Find components related to a base path"""
        related = []

        # Extract resource name from path
        resource = base_path.split('/')[-1]
        resource_clean = resource.replace('_', '').replace('-', '').lower()

        # Get all endpoint paths for this feature
        endpoint_paths = {e.path for e in endpoints}

        for component in components:
            component_clean = component.name.lower()

            # Check if component name matches resource
            if resource_clean in component_clean:
                related.append(component)
                continue

            # Check if component uses any of the feature's endpoints
            if any(api in endpoint_paths for api in component.apis_used):
                related.append(component)
                continue

        return related

    def _find_related_tests(self, base_path: str, test_files: List[str]) -> List[str]:
        """Find test files related to a base path"""
        related = []

        resource = base_path.split('/')[-1]
        resource_clean = resource.replace('_', '').replace('-', '').lower()

        for test_file in test_files:
            test_clean = test_file.lower()
            if resource_clean in test_clean:
                related.append(test_file)

        return related

    def _calculate_completeness(
        self,
        endpoints: List[APIEndpoint],
        models: List[DatabaseModel],
        components: List[UIComponent],
        tests: List[str]
    ) -> float:
        """Calculate feature completeness score (0.0 - 1.0)"""
        score = 0.0

        # Has endpoints (30%)
        if endpoints:
            score += 0.3

        # Has models (20%)
        if models:
            score += 0.2

        # Has components (20%)
        if components:
            score += 0.2

        # Has tests (30%)
        if tests:
            score += 0.3

        return round(score, 2)

    def _calculate_confidence(
        self,
        endpoints: List[APIEndpoint],
        models: List[DatabaseModel],
        components: List[UIComponent]
    ) -> float:
        """Calculate confidence that this is a real feature (0.0 - 1.0)"""
        score = 0.0

        # More endpoints = higher confidence
        if len(endpoints) >= 4:
            score += 0.4
        elif len(endpoints) >= 2:
            score += 0.3
        elif len(endpoints) >= 1:
            score += 0.2

        # Has models
        if models:
            score += 0.3

        # Has components
        if components:
            score += 0.3

        return min(round(score, 2), 1.0)


async def analyze_code_features(impl_dir: Path) -> List[CodeFeature]:
    """Main entry point for code feature analysis"""
    analyzer = CodeFeatureAnalyzer(impl_dir)
    features = await analyzer.analyze()
    return features


async def generate_feature_report(impl_dir: Path, output_file: Optional[Path] = None) -> Dict[str, Any]:
    """Generate feature analysis report"""
    features = await analyze_code_features(impl_dir)

    report = {
        "workflow_dir": str(impl_dir),
        "total_features": len(features),
        "features": [f.to_dict() for f in features],
        "summary": {
            "by_category": {},
            "with_tests": sum(1 for f in features if f.has_tests),
            "average_completeness": round(sum(f.completeness for f in features) / len(features), 2) if features else 0.0,
            "average_confidence": round(sum(f.confidence for f in features) / len(features), 2) if features else 0.0
        }
    }

    # Count by category
    for feature in features:
        cat = feature.category.value
        report["summary"]["by_category"][cat] = report["summary"]["by_category"].get(cat, 0) + 1

    # Save to file if requested
    if output_file:
        output_file.write_text(json.dumps(report, indent=2))
        logger.info(f"📄 Saved report to {output_file}")

    return report


if __name__ == "__main__":
    # Test on Batch 5 workflow
    import asyncio

    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

    async def main():
        impl_dir = Path("/tmp/maestro_workflow/wf-1760076571-6b932a66/implementation")

        print("=" * 80)
        print("CODE FEATURE ANALYZER - TEST RUN")
        print("=" * 80)
        print(f"Analyzing: {impl_dir}\n")

        report = await generate_feature_report(
            impl_dir,
            impl_dir / "CODE_FEATURE_ANALYSIS.json"
        )

        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print(f"\n📊 Summary:")
        print(f"  Total Features: {report['total_features']}")
        print(f"  With Tests: {report['summary']['with_tests']}")
        print(f"  Avg Completeness: {report['summary']['average_completeness']:.0%}")
        print(f"  Avg Confidence: {report['summary']['average_confidence']:.0%}")

        print(f"\n📋 Features by Category:")
        for category, count in report['summary']['by_category'].items():
            print(f"  {category}: {count}")

        print(f"\n✅ Identified Features:")
        for feature_data in report['features']:
            print(f"\n  {feature_data['id']}: {feature_data['name']}")
            print(f"    Category: {feature_data['category']}")
            print(f"    Confidence: {feature_data['confidence']:.0%}")
            print(f"    Completeness: {feature_data['completeness']:.0%}")
            print(f"    Endpoints: {len(feature_data['endpoints'])}")
            print(f"    Models: {len(feature_data['models'])}")
            print(f"    Components: {len(feature_data['components'])}")
            print(f"    Has Tests: {'✅' if feature_data['has_tests'] else '❌'}")

    asyncio.run(main())
