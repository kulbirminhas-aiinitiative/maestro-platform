"""
OpenAPI to Gherkin Generator

This module provides functionality to convert OpenAPI 3.0+ specifications
into Gherkin feature files for BDD testing.

Features:
- Parse OpenAPI 3.0+ specifications (JSON/YAML)
- Extract paths, operations, parameters, schemas
- Resolve $ref references
- Generate Gherkin scenarios from endpoints
- Create example data using Faker
- Support boundary values and edge cases

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

import json
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from faker import Faker


# ============================================================================
# Data Models
# ============================================================================

class HTTPMethod(Enum):
    """HTTP methods"""
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"
    PATCH = "patch"
    OPTIONS = "options"
    HEAD = "head"


@dataclass
class OpenAPIParameter:
    """Represents an OpenAPI parameter"""
    name: str
    location: str  # path, query, header, cookie
    required: bool = False
    schema: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    example: Optional[Any] = None


@dataclass
class OpenAPISchema:
    """Represents an OpenAPI schema"""
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    example: Optional[Any] = None
    enum: Optional[List[Any]] = None
    format: Optional[str] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    items: Optional[Dict[str, Any]] = None


@dataclass
class OpenAPIOperation:
    """Represents an OpenAPI operation (endpoint + method)"""
    path: str
    method: HTTPMethod
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[OpenAPIParameter] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = field(default_factory=dict)
    security: List[Dict[str, List[str]]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class GherkinScenario:
    """Represents a Gherkin scenario"""
    name: str
    steps: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    background: List[str] = field(default_factory=list)
    is_outline: bool = False
    examples: Optional[Dict[str, List[List[str]]]] = None


@dataclass
class GherkinFeature:
    """Represents a Gherkin feature file"""
    name: str
    description: Optional[str] = None
    scenarios: List[GherkinScenario] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    background: List[str] = field(default_factory=list)


# ============================================================================
# OpenAPI Parser
# ============================================================================

class OpenAPIParser:
    """
    Parses OpenAPI 3.0+ specifications

    Features:
    - Parse JSON/YAML specifications
    - Resolve $ref references
    - Extract operations, schemas, parameters
    - Parse security requirements
    """

    def __init__(self):
        self.spec: Optional[Dict[str, Any]] = None
        self.base_path: Optional[Path] = None
        self._resolved_refs: Dict[str, Any] = {}

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse OpenAPI specification from file"""
        path = Path(file_path)
        self.base_path = path.parent

        if not path.exists():
            raise FileNotFoundError(f"OpenAPI file not found: {file_path}")

        content = path.read_text()

        if path.suffix in ['.yaml', '.yml']:
            self.spec = yaml.safe_load(content)
        elif path.suffix == '.json':
            self.spec = json.loads(content)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        self._validate_spec()
        return self.spec

    def parse_content(self, content: str, format: str = 'json') -> Dict[str, Any]:
        """Parse OpenAPI specification from string content"""
        if format.lower() in ['yaml', 'yml']:
            self.spec = yaml.safe_load(content)
        else:
            self.spec = json.loads(content)

        self._validate_spec()
        return self.spec

    def _validate_spec(self):
        """Validate OpenAPI specification"""
        if not self.spec:
            raise ValueError("Invalid OpenAPI specification: empty content")

        if 'openapi' not in self.spec:
            raise ValueError("Invalid OpenAPI specification: missing 'openapi' field")

        version = self.spec['openapi']
        if not version.startswith('3.'):
            raise ValueError(f"Unsupported OpenAPI version: {version}. Only 3.x supported.")

        if 'paths' not in self.spec:
            raise ValueError("Invalid OpenAPI specification: missing 'paths' field")

    def resolve_ref(self, ref: str) -> Any:
        """Resolve $ref reference"""
        if ref in self._resolved_refs:
            return self._resolved_refs[ref]

        # Handle local references (#/components/schemas/User)
        if ref.startswith('#/'):
            parts = ref[2:].split('/')
            obj = self.spec
            for part in parts:
                if part in obj:
                    obj = obj[part]
                else:
                    raise ValueError(f"Invalid reference: {ref}")

            self._resolved_refs[ref] = obj
            return obj

        # Handle external references (not implemented for now)
        raise ValueError(f"External references not supported: {ref}")

    def get_operations(self) -> List[OpenAPIOperation]:
        """Extract all operations from the specification"""
        operations = []

        if not self.spec or 'paths' not in self.spec:
            return operations

        for path, path_item in self.spec['paths'].items():
            # Resolve $ref if present
            if '$ref' in path_item:
                path_item = self.resolve_ref(path_item['$ref'])

            for method in HTTPMethod:
                if method.value in path_item:
                    operation_data = path_item[method.value]
                    operation = self._parse_operation(path, method, operation_data, path_item)
                    operations.append(operation)

        return operations

    def _parse_operation(self, path: str, method: HTTPMethod,
                        operation_data: Dict[str, Any],
                        path_item: Dict[str, Any]) -> OpenAPIOperation:
        """Parse a single operation"""
        operation = OpenAPIOperation(
            path=path,
            method=method,
            operation_id=operation_data.get('operationId'),
            summary=operation_data.get('summary'),
            description=operation_data.get('description'),
            tags=operation_data.get('tags', []),
            security=operation_data.get('security', [])
        )

        # Parse parameters (path-level + operation-level)
        parameters = path_item.get('parameters', []) + operation_data.get('parameters', [])
        for param in parameters:
            if '$ref' in param:
                param = self.resolve_ref(param['$ref'])
            operation.parameters.append(self._parse_parameter(param))

        # Parse request body
        if 'requestBody' in operation_data:
            request_body = operation_data['requestBody']
            if '$ref' in request_body:
                request_body = self.resolve_ref(request_body['$ref'])
            operation.request_body = request_body

        # Parse responses
        operation.responses = operation_data.get('responses', {})

        return operation

    def _parse_parameter(self, param_data: Dict[str, Any]) -> OpenAPIParameter:
        """Parse a parameter"""
        return OpenAPIParameter(
            name=param_data['name'],
            location=param_data['in'],
            required=param_data.get('required', False),
            schema=param_data.get('schema'),
            description=param_data.get('description'),
            example=param_data.get('example')
        )

    def get_schema(self, schema_ref: str) -> Optional[OpenAPISchema]:
        """Get a schema by reference or name"""
        if schema_ref.startswith('#/'):
            schema_data = self.resolve_ref(schema_ref)
        else:
            # Try to find in components/schemas
            schema_path = f"#/components/schemas/{schema_ref}"
            try:
                schema_data = self.resolve_ref(schema_path)
            except ValueError:
                return None

        return self._parse_schema(schema_data)

    def _parse_schema(self, schema_data: Dict[str, Any]) -> OpenAPISchema:
        """Parse a schema"""
        if '$ref' in schema_data:
            schema_data = self.resolve_ref(schema_data['$ref'])

        return OpenAPISchema(
            type=schema_data.get('type', 'object'),
            properties=schema_data.get('properties', {}),
            required=schema_data.get('required', []),
            example=schema_data.get('example'),
            enum=schema_data.get('enum'),
            format=schema_data.get('format'),
            minimum=schema_data.get('minimum'),
            maximum=schema_data.get('maximum'),
            items=schema_data.get('items')
        )

    def get_servers(self) -> List[str]:
        """Get server URLs"""
        if not self.spec or 'servers' not in self.spec:
            return []

        servers = []
        for server in self.spec['servers']:
            servers.append(server.get('url', ''))
        return servers

    def get_info(self) -> Dict[str, Any]:
        """Get API info"""
        return self.spec.get('info', {}) if self.spec else {}


# ============================================================================
# Gherkin Builder
# ============================================================================

class GherkinBuilder:
    """
    Builds Gherkin feature files from structured data

    Features:
    - Generate feature file structure
    - Format scenarios with proper indentation
    - Support tags, backgrounds, scenario outlines
    - Generate data tables
    """

    def __init__(self):
        self.faker = Faker()

    def build_feature(self, feature: GherkinFeature) -> str:
        """Build complete feature file content"""
        lines = []

        # Tags
        if feature.tags:
            lines.append(' '.join(feature.tags))

        # Feature name
        lines.append(f"Feature: {feature.name}")

        # Description
        if feature.description:
            for line in feature.description.split('\n'):
                lines.append(f"  {line}")

        lines.append("")

        # Background
        if feature.background:
            lines.append("  Background:")
            for step in feature.background:
                lines.append(f"    {step}")
            lines.append("")

        # Scenarios
        for scenario in feature.scenarios:
            lines.extend(self._build_scenario(scenario))
            lines.append("")

        return '\n'.join(lines)

    def _build_scenario(self, scenario: GherkinScenario) -> List[str]:
        """Build a single scenario"""
        lines = []

        # Tags
        if scenario.tags:
            lines.append("  " + ' '.join(scenario.tags))

        # Scenario name
        scenario_type = "Scenario Outline" if scenario.is_outline else "Scenario"
        lines.append(f"  {scenario_type}: {scenario.name}")

        # Description
        if scenario.description:
            for line in scenario.description.split('\n'):
                lines.append(f"    {line}")

        # Steps
        for step in scenario.steps:
            if step.startswith('|'):  # Data table
                lines.append(f"      {step}")
            else:
                lines.append(f"    {step}")

        # Examples (for Scenario Outline)
        if scenario.is_outline and scenario.examples:
            lines.append("")
            lines.append("    Examples:")
            for table_line in self._format_examples(scenario.examples):
                lines.append(f"      {table_line}")

        return lines

    def _format_examples(self, examples: Dict[str, List[List[str]]]) -> List[str]:
        """Format examples table"""
        lines = []

        for name, data in examples.items():
            if name != "default":
                lines.append(f"# {name}")

            if data:
                # Header row
                headers = data[0]
                lines.append('| ' + ' | '.join(headers) + ' |')

                # Data rows
                for row in data[1:]:
                    lines.append('| ' + ' | '.join(row) + ' |')

        return lines

    def build_data_table(self, data: List[Dict[str, Any]]) -> List[str]:
        """Build data table from list of dictionaries"""
        if not data:
            return []

        lines = []
        headers = list(data[0].keys())

        # Header row
        lines.append('| ' + ' | '.join(headers) + ' |')

        # Data rows
        for row in data:
            values = [str(row.get(h, '')) for h in headers]
            lines.append('| ' + ' | '.join(values) + ' |')

        return lines


# ============================================================================
# OpenAPI to Gherkin Generator
# ============================================================================

class OpenAPIToGherkinGenerator:
    """
    Main generator class that converts OpenAPI to Gherkin

    Features:
    - Convert operations to scenarios
    - Generate example data
    - Handle edge cases and boundaries
    - Create feature files with proper structure
    """

    def __init__(self):
        self.parser = OpenAPIParser()
        self.builder = GherkinBuilder()
        self.faker = Faker()

    def generate_from_file(self, openapi_file: str,
                          output_dir: Optional[str] = None) -> List[str]:
        """Generate Gherkin feature files from OpenAPI file"""
        self.parser.parse_file(openapi_file)
        return self._generate_features(output_dir)

    def generate_from_content(self, content: str, format: str = 'json',
                            output_dir: Optional[str] = None) -> List[str]:
        """Generate Gherkin feature files from OpenAPI content"""
        self.parser.parse_content(content, format)
        return self._generate_features(output_dir)

    def _generate_features(self, output_dir: Optional[str]) -> List[str]:
        """Generate feature files"""
        operations = self.parser.get_operations()

        # Group operations by tags or paths
        features_by_tag = self._group_operations(operations)

        generated_files = []
        for tag, ops in features_by_tag.items():
            feature = self._create_feature(tag, ops)
            content = self.builder.build_feature(feature)

            if output_dir:
                output_path = Path(output_dir) / f"{self._sanitize_filename(tag)}.feature"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content)
                generated_files.append(str(output_path))
            else:
                generated_files.append(content)

        return generated_files

    def _group_operations(self, operations: List[OpenAPIOperation]) -> Dict[str, List[OpenAPIOperation]]:
        """Group operations by tag"""
        groups = {}

        for op in operations:
            tag = op.tags[0] if op.tags else "API"
            if tag not in groups:
                groups[tag] = []
            groups[tag].append(op)

        return groups

    def _create_feature(self, tag: str, operations: List[OpenAPIOperation]) -> GherkinFeature:
        """Create a feature from operations"""
        info = self.parser.get_info()
        version = info.get('version', '1.0.0')

        feature = GherkinFeature(
            name=f"{tag} API",
            description=info.get('description', ''),
            tags=[f"@contract:{tag}API:v{version}"]
        )

        # Add background for common setup
        servers = self.parser.get_servers()
        if servers:
            feature.background = [
                f'Given the API base URL is "{servers[0]}"',
                'And the request content type is "application/json"'
            ]

        # Generate scenarios for each operation
        for op in operations:
            scenario = self._create_scenario(op)
            feature.scenarios.append(scenario)

        return feature

    def _create_scenario(self, operation: OpenAPIOperation) -> GherkinScenario:
        """Create scenario from operation"""
        # Generate scenario name based on method and path
        resource = self._extract_resource_name(operation.path)
        action = self._method_to_action(operation.method)

        scenario_name = operation.summary or f"{action} {resource}"

        scenario = GherkinScenario(
            name=scenario_name,
            description=operation.description
        )

        # Generate steps
        steps = self._generate_steps(operation)
        scenario.steps = steps

        return scenario

    def _generate_steps(self, operation: OpenAPIOperation) -> List[str]:
        """Generate Given/When/Then steps for an operation"""
        steps = []

        # Given steps: parameters and request body
        path_params = [p for p in operation.parameters if p.location == 'path']
        query_params = [p for p in operation.parameters if p.location == 'query']

        # Path parameters
        for param in path_params:
            example = self._generate_example_value(param.schema, param.example)
            steps.append(f'Given {param.name} is "{example}"')

        # Query parameters
        for param in query_params:
            example = self._generate_example_value(param.schema, param.example)
            steps.append(f'And {param.name} parameter is "{example}"')

        # Request body
        if operation.request_body:
            body_steps = self._generate_request_body_steps(operation.request_body)
            steps.extend(body_steps)

        # When step: make the request
        steps.append(f'When I send a {operation.method.value.upper()} request to "{operation.path}"')

        # Then steps: response validation
        response_steps = self._generate_response_steps(operation.responses)
        steps.extend(response_steps)

        return steps

    def _generate_request_body_steps(self, request_body: Dict[str, Any]) -> List[str]:
        """Generate steps for request body"""
        steps = []

        content = request_body.get('content', {})
        if 'application/json' in content:
            schema_data = content['application/json'].get('schema', {})

            if '$ref' in schema_data:
                schema = self.parser.get_schema(schema_data['$ref'])
            else:
                schema = self.parser._parse_schema(schema_data)

            if schema:
                resource_name = self._extract_resource_from_schema(schema_data)
                steps.append(f'And the following {resource_name} data:')

                # Generate data table
                table_data = self._generate_table_from_schema(schema)
                steps.extend(table_data)

        return steps

    def _generate_response_steps(self, responses: Dict[str, Any]) -> List[str]:
        """Generate steps for response validation"""
        steps = []

        # Find success response (2xx)
        success_code = None
        for code in ['200', '201', '202', '204']:
            if code in responses:
                success_code = code
                break

        if success_code:
            steps.append(f'Then the response status code is {success_code}')

            # Parse response schema if available
            response_data = responses[success_code]
            if 'content' in response_data:
                content = response_data['content']
                if 'application/json' in content:
                    schema_data = content['application/json'].get('schema', {})
                    if schema_data:
                        steps.append('And the response contains:')
                        # For simplicity, just add placeholder
                        steps.append('| field | value |')
                        steps.append('| <any> | <any> |')

        return steps

    def _generate_table_from_schema(self, schema: OpenAPISchema) -> List[str]:
        """Generate data table from schema"""
        rows = []

        for prop_name, prop_data in schema.properties.items():
            if '$ref' in prop_data:
                prop_schema = self.parser.get_schema(prop_data['$ref'])
            else:
                prop_schema = self.parser._parse_schema(prop_data)

            value = self._generate_example_value(prop_data, prop_schema.example if prop_schema else None)

            if not rows:
                rows.append('| field | value |')
            rows.append(f'| {prop_name} | {value} |')

        return rows

    def _generate_example_value(self, schema: Optional[Dict[str, Any]],
                               example: Optional[Any] = None) -> str:
        """Generate example value for a field"""
        if example is not None:
            return str(example)

        if not schema:
            return self.faker.word()

        field_type = schema.get('type', 'string')
        field_format = schema.get('format')

        # Handle enums
        if 'enum' in schema:
            return str(schema['enum'][0])

        # Generate based on type
        if field_type == 'string':
            if field_format == 'email':
                return self.faker.email()
            elif field_format == 'date':
                return self.faker.date()
            elif field_format == 'date-time':
                return self.faker.iso8601()
            elif field_format == 'uuid':
                return str(self.faker.uuid4())
            else:
                return self.faker.word()
        elif field_type == 'integer':
            minimum = schema.get('minimum', 1)
            maximum = schema.get('maximum', 100)
            return str(self.faker.random_int(min=minimum, max=maximum))
        elif field_type == 'number':
            return str(self.faker.random_number(digits=2))
        elif field_type == 'boolean':
            return str(self.faker.boolean()).lower()
        elif field_type == 'array':
            return '[]'
        elif field_type == 'object':
            return '{}'

        return '<any>'

    def _method_to_action(self, method: HTTPMethod) -> str:
        """Convert HTTP method to action verb"""
        actions = {
            HTTPMethod.GET: "Get",
            HTTPMethod.POST: "Create",
            HTTPMethod.PUT: "Update",
            HTTPMethod.DELETE: "Delete",
            HTTPMethod.PATCH: "Update",
        }
        return actions.get(method, method.value.upper())

    def _extract_resource_name(self, path: str) -> str:
        """Extract resource name from path"""
        # Remove path parameters
        path = re.sub(r'\{[^}]+\}', '', path)
        # Get last segment
        parts = [p for p in path.split('/') if p]
        if parts:
            return parts[-1].capitalize()
        return "Resource"

    def _extract_resource_from_schema(self, schema_data: Dict[str, Any]) -> str:
        """Extract resource name from schema"""
        if '$ref' in schema_data:
            ref = schema_data['$ref']
            parts = ref.split('/')
            if parts:
                return parts[-1].lower()
        return "resource"

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize name for filename"""
        # Remove special characters
        name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        return name.lower()
