"""
Gherkin Feature File Parser

Parses Gherkin feature files and extracts structured data for BDV validation.

Key Features:
- Full Gherkin syntax support (Feature, Scenario, Scenario Outline, Background)
- Tag parsing including contract tags (@contract:API:v1.2)
- Step extraction (Given, When, Then, And, But)
- Data table parsing
- Multi-line string (docstring) support
- Comment handling
- Unicode support
- Language tag support (@language:en)
- Performance optimized for large files (100+ scenarios)

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from enum import Enum


class StepKeyword(str, Enum):
    """Gherkin step keywords"""
    GIVEN = "Given"
    WHEN = "When"
    THEN = "Then"
    AND = "And"
    BUT = "But"


class GherkinKeyword(str, Enum):
    """Gherkin structural keywords"""
    FEATURE = "Feature"
    BACKGROUND = "Background"
    SCENARIO = "Scenario"
    SCENARIO_OUTLINE = "Scenario Outline"
    EXAMPLES = "Examples"


@dataclass
class DataTable:
    """Represents a Gherkin data table"""
    headers: List[str]
    rows: List[List[str]]

    def to_dict_list(self) -> List[Dict[str, str]]:
        """Convert table to list of dictionaries"""
        return [
            {self.headers[i]: cell for i, cell in enumerate(row)}
            for row in self.rows
        ]


@dataclass
class Step:
    """Represents a Gherkin step"""
    keyword: StepKeyword
    text: str
    line_number: int
    data_table: Optional[DataTable] = None
    doc_string: Optional[str] = None
    parameters: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Extract step parameters from text"""
        # Extract parameters in <angle_brackets> or "quoted"
        angle_params = re.findall(r'<([^>]+)>', self.text)
        quoted_params = re.findall(r'"([^"]+)"', self.text)
        self.parameters = angle_params + quoted_params


@dataclass
class Example:
    """Represents an Examples table in a Scenario Outline"""
    line_number: int
    tags: List[str] = field(default_factory=list)
    data_table: Optional[DataTable] = None


@dataclass
class Scenario:
    """Represents a Gherkin scenario"""
    name: str
    line_number: int
    type: str  # "scenario" or "scenario_outline"
    tags: List[str] = field(default_factory=list)
    steps: List[Step] = field(default_factory=list)
    examples: List[Example] = field(default_factory=list)
    description: str = ""

    @property
    def is_outline(self) -> bool:
        """Check if this is a Scenario Outline"""
        return self.type == "scenario_outline"

    def expand_outline(self) -> List['Scenario']:
        """
        Expand Scenario Outline into individual scenarios using Examples.
        Returns list of concrete scenarios with parameters substituted.
        """
        if not self.is_outline or not self.examples:
            return [self]

        expanded = []
        for example_idx, example in enumerate(self.examples):
            if not example.data_table:
                continue

            # Generate scenario for each row in examples table
            for row_idx, row in enumerate(example.data_table.rows):
                # Create parameter mapping
                params = {
                    header: value
                    for header, value in zip(example.data_table.headers, row)
                }

                # Create new scenario with substituted values
                scenario_name = self._substitute_params(self.name, params)
                new_steps = []

                for step in self.steps:
                    substituted_text = self._substitute_params(step.text, params)
                    new_step = Step(
                        keyword=step.keyword,
                        text=substituted_text,
                        line_number=step.line_number,
                        data_table=step.data_table,
                        doc_string=step.doc_string
                    )
                    new_steps.append(new_step)

                expanded_scenario = Scenario(
                    name=f"{scenario_name} [Example {example_idx+1}, Row {row_idx+1}]",
                    line_number=self.line_number,
                    type="scenario",
                    tags=self.tags + example.tags,
                    steps=new_steps,
                    description=self.description
                )
                expanded.append(expanded_scenario)

        return expanded

    @staticmethod
    def _substitute_params(text: str, params: Dict[str, str]) -> str:
        """Substitute <parameters> in text with values from params dict"""
        result = text
        for key, value in params.items():
            result = result.replace(f"<{key}>", value)
        return result


@dataclass
class Background:
    """Represents a Gherkin background"""
    line_number: int
    steps: List[Step] = field(default_factory=list)
    description: str = ""


@dataclass
class Feature:
    """Represents a complete Gherkin feature"""
    name: str
    line_number: int
    file_path: Optional[str] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)
    background: Optional[Background] = None
    scenarios: List[Scenario] = field(default_factory=list)
    language: str = "en"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def contract_tags(self) -> List[str]:
        """Extract contract tags from feature tags"""
        return [tag for tag in self.tags if tag.startswith("@contract:")]

    def total_scenarios(self, expanded: bool = False) -> int:
        """
        Get total scenario count.

        Args:
            expanded: If True, count expanded outline scenarios
        """
        if not expanded:
            return len(self.scenarios)

        total = 0
        for scenario in self.scenarios:
            if scenario.is_outline:
                total += len(scenario.expand_outline())
            else:
                total += 1
        return total


@dataclass
class ParseResult:
    """Result of parsing a feature file"""
    success: bool
    feature: Optional[Feature] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class FeatureParser:
    """
    Gherkin Feature File Parser

    Parses .feature files and extracts structured data for validation.
    Supports full Gherkin syntax including:
    - Feature, Background, Scenario, Scenario Outline
    - Tags (@tag, @contract:API:v1.2)
    - Steps (Given, When, Then, And, But)
    - Data tables
    - Multi-line strings (doc strings)
    - Comments
    - Unicode
    """

    def __init__(self):
        self.current_file: Optional[Path] = None
        self.lines: List[str] = []
        self.line_index: int = 0

    def parse_file(self, file_path: Union[str, Path]) -> ParseResult:
        """
        Parse a Gherkin feature file.

        Args:
            file_path: Path to .feature file

        Returns:
            ParseResult with parsed feature or errors
        """
        file_path = Path(file_path)
        self.current_file = file_path

        if not file_path.exists():
            return ParseResult(
                success=False,
                errors=[f"File not found: {file_path}"]
            )

        if not file_path.suffix == ".feature":
            return ParseResult(
                success=False,
                errors=[f"Not a .feature file: {file_path}"]
            )

        try:
            content = file_path.read_text(encoding="utf-8")
            return self.parse_content(content, str(file_path))
        except UnicodeDecodeError as e:
            return ParseResult(
                success=False,
                errors=[f"Unicode decode error: {e}"]
            )
        except Exception as e:
            return ParseResult(
                success=False,
                errors=[f"Unexpected error: {e}"]
            )

    def parse_content(self, content: str, file_path: Optional[str] = None) -> ParseResult:
        """
        Parse Gherkin content string.

        Args:
            content: Gherkin content
            file_path: Optional file path for reference

        Returns:
            ParseResult with parsed feature or errors
        """
        self.lines = content.split("\n")
        self.line_index = 0

        errors = []
        warnings = []

        # Extract language tag if present
        language = "en"
        initial_tags = []

        # Skip comments and extract initial tags
        while self.line_index < len(self.lines):
            line = self._current_line().strip()

            if not line or line.startswith("#"):
                self.line_index += 1
                continue

            if line.startswith("@language:"):
                language = line.split(":", 1)[1].strip()
                self.line_index += 1
                continue

            if line.startswith("@"):
                initial_tags.extend(self._parse_tags(line))
                self.line_index += 1
                continue

            break

        # Parse Feature keyword
        if self.line_index >= len(self.lines):
            return ParseResult(
                success=False,
                errors=["Empty file or missing Feature keyword"]
            )

        feature_line = self._current_line().strip()
        if not feature_line.startswith("Feature:"):
            return ParseResult(
                success=False,
                errors=[f"Missing Feature keyword at line {self.line_index + 1}"]
            )

        feature_name = feature_line[8:].strip()
        feature_line_number = self.line_index + 1
        self.line_index += 1

        # Parse feature description
        description = self._parse_description()

        # Initialize feature
        feature = Feature(
            name=feature_name,
            line_number=feature_line_number,
            file_path=file_path,
            description=description,
            tags=initial_tags,
            language=language
        )

        # Parse background and scenarios
        while self.line_index < len(self.lines):
            line = self._current_line().strip()

            if not line or line.startswith("#"):
                self.line_index += 1
                continue

            if line.startswith("Background:"):
                if feature.background:
                    warnings.append(f"Multiple Background sections found at line {self.line_index + 1}")
                feature.background = self._parse_background()
            elif line.startswith("@") or line.startswith("Scenario:") or line.startswith("Scenario Outline:"):
                # Parse scenario (will handle tags)
                scenario = self._parse_scenario()
                if scenario:
                    feature.scenarios.append(scenario)
            else:
                self.line_index += 1

        if not feature.scenarios and not feature.background:
            warnings.append("Feature has no scenarios or background")

        return ParseResult(
            success=True,
            feature=feature,
            warnings=warnings
        )

    def _current_line(self) -> str:
        """Get current line without advancing"""
        if self.line_index < len(self.lines):
            return self.lines[self.line_index]
        return ""

    def _parse_tags(self, line: str) -> List[str]:
        """Parse tags from a line"""
        # Tags are @word separated by spaces
        return [tag.strip() for tag in line.split() if tag.strip().startswith("@")]

    def _parse_description(self) -> str:
        """Parse multi-line description"""
        description_lines = []

        while self.line_index < len(self.lines):
            line = self.lines[self.line_index].strip()

            # Stop at keywords, tags, or step keywords (but not empty lines or comments)
            if (line.startswith("@") or
                any(line.startswith(kw.value + ":") for kw in GherkinKeyword) or
                any(line.startswith(kw.value + " ") for kw in StepKeyword)):
                break

            # Skip comments but continue parsing
            if line.startswith("#"):
                self.line_index += 1
                continue

            # Include empty lines in description (they separate paragraphs)
            description_lines.append(line)
            self.line_index += 1

            # Stop if we've hit two consecutive empty lines (end of description)
            if not line and self.line_index < len(self.lines):
                next_line = self.lines[self.line_index].strip()
                if not next_line:
                    break

        return "\n".join(description_lines).strip()

    def _parse_background(self) -> Background:
        """Parse Background section"""
        line_number = self.line_index + 1
        self.line_index += 1

        description = self._parse_description()
        steps = self._parse_steps()

        return Background(
            line_number=line_number,
            steps=steps,
            description=description
        )

    def _parse_scenario(self) -> Optional[Scenario]:
        """Parse Scenario or Scenario Outline"""
        # Parse tags before scenario
        tags = []
        while self.line_index < len(self.lines):
            line = self._current_line().strip()
            if line.startswith("@"):
                tags.extend(self._parse_tags(line))
                self.line_index += 1
            else:
                break

        if self.line_index >= len(self.lines):
            return None

        line = self._current_line().strip()
        if not (line.startswith("Scenario:") or line.startswith("Scenario Outline:")):
            return None

        is_outline = line.startswith("Scenario Outline:")
        keyword = "Scenario Outline:" if is_outline else "Scenario:"
        scenario_name = line[len(keyword):].strip()
        line_number = self.line_index + 1
        self.line_index += 1

        description = self._parse_description()
        steps = self._parse_steps()

        # Parse Examples if Scenario Outline
        examples = []
        if is_outline:
            examples = self._parse_examples()

        return Scenario(
            name=scenario_name,
            line_number=line_number,
            type="scenario_outline" if is_outline else "scenario",
            tags=tags,
            steps=steps,
            examples=examples,
            description=description
        )

    def _parse_steps(self) -> List[Step]:
        """Parse step list"""
        steps = []
        last_keyword = None

        while self.line_index < len(self.lines):
            line = self.lines[self.line_index].strip()

            # Skip empty lines and comments within steps
            if not line or line.startswith("#"):
                self.line_index += 1
                continue

            # Stop at tags or next section
            if (line.startswith("@") or
                line.startswith("Examples:") or
                line.startswith("Scenario:") or
                line.startswith("Scenario Outline:") or
                line.startswith("Background:")):
                break

            # Check for step keywords
            step_keyword = None
            for keyword in StepKeyword:
                if line.startswith(keyword.value + " "):
                    step_keyword = keyword
                    break

            if not step_keyword:
                # Not a step, break
                break

            # Parse step
            step_text = line[len(step_keyword.value):].strip()
            line_number = self.line_index + 1
            self.line_index += 1

            # Track last main keyword (Given/When/Then)
            if step_keyword in (StepKeyword.GIVEN, StepKeyword.WHEN, StepKeyword.THEN):
                last_keyword = step_keyword

            # Parse data table or doc string
            data_table = None
            doc_string = None

            next_line = self._current_line().strip() if self.line_index < len(self.lines) else ""

            if next_line.startswith("|"):
                data_table = self._parse_data_table()
            elif next_line.startswith('"""') or next_line.startswith("'''"):
                doc_string = self._parse_doc_string()

            step = Step(
                keyword=step_keyword,
                text=step_text,
                line_number=line_number,
                data_table=data_table,
                doc_string=doc_string
            )
            steps.append(step)

        return steps

    def _parse_data_table(self) -> DataTable:
        """Parse data table (| col1 | col2 |)"""
        rows = []

        while self.line_index < len(self.lines):
            line = self.lines[self.line_index].strip()

            if not line.startswith("|"):
                break

            # Parse row
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            rows.append(cells)
            self.line_index += 1

        if not rows:
            return DataTable(headers=[], rows=[])

        # First row is headers
        headers = rows[0]
        data_rows = rows[1:]

        return DataTable(headers=headers, rows=data_rows)

    def _parse_doc_string(self) -> str:
        """Parse multi-line doc string (triple quotes)"""
        delimiter = self._current_line().strip()[:3]  # """ or '''
        self.line_index += 1

        lines = []
        while self.line_index < len(self.lines):
            line = self.lines[self.line_index]

            if line.strip().startswith(delimiter):
                self.line_index += 1
                break

            lines.append(line)
            self.line_index += 1

        return "\n".join(lines)

    def _parse_examples(self) -> List[Example]:
        """Parse Examples sections for Scenario Outline"""
        examples = []

        while self.line_index < len(self.lines):
            # Skip empty lines and comments
            while self.line_index < len(self.lines):
                line = self._current_line().strip()
                if line and not line.startswith("#"):
                    break
                self.line_index += 1

            if self.line_index >= len(self.lines):
                break

            # Check for tags before Examples
            tags = []
            while self.line_index < len(self.lines):
                line = self._current_line().strip()
                if line.startswith("@"):
                    tags.extend(self._parse_tags(line))
                    self.line_index += 1
                elif line and not line.startswith("#"):
                    break
                else:
                    self.line_index += 1

            if self.line_index >= len(self.lines):
                break

            line = self._current_line().strip()
            if not line.startswith("Examples:"):
                break

            line_number = self.line_index + 1
            self.line_index += 1

            # Skip description and empty lines before table
            while self.line_index < len(self.lines):
                line = self._current_line().strip()
                if line.startswith("|") or not line or line.startswith("#"):
                    break
                self.line_index += 1

            # Parse data table
            data_table = None
            if self.line_index < len(self.lines) and self._current_line().strip().startswith("|"):
                data_table = self._parse_data_table()

            example = Example(
                line_number=line_number,
                tags=tags,
                data_table=data_table
            )
            examples.append(example)

        return examples

    def parse_summary(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse feature file and return summary statistics.

        Args:
            file_path: Path to .feature file

        Returns:
            Dictionary with summary: {
                'success': bool,
                'file_path': str,
                'test_count': int (total scenarios),
                'pass_rate': float (always 0 for parsing),
                'feature_name': str,
                'scenario_count': int,
                'outline_count': int,
                'total_steps': int,
                'contract_tags': List[str],
                'errors': List[str]
            }
        """
        result = self.parse_file(file_path)

        if not result.success:
            return {
                'success': False,
                'file_path': str(file_path),
                'test_count': 0,
                'pass_rate': 0.0,
                'errors': result.errors
            }

        feature = result.feature
        scenario_count = len([s for s in feature.scenarios if not s.is_outline])
        outline_count = len([s for s in feature.scenarios if s.is_outline])
        total_steps = sum(len(s.steps) for s in feature.scenarios)

        if feature.background:
            total_steps += len(feature.background.steps)

        return {
            'success': True,
            'file_path': str(file_path),
            'test_count': feature.total_scenarios(expanded=True),
            'pass_rate': 0.0,  # Parsing doesn't execute tests
            'feature_name': feature.name,
            'scenario_count': scenario_count,
            'outline_count': outline_count,
            'total_steps': total_steps,
            'contract_tags': feature.contract_tags,
            'tags': feature.tags,
            'errors': result.errors,
            'warnings': result.warnings
        }
