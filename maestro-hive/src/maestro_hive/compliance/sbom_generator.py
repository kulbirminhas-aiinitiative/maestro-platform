#!/usr/bin/env python3
"""
SBOM Generator: Software Bill of Materials in CycloneDX format.

Generates SBOMs for compliance with EU AI Act Article 12 and SOC2 requirements.
Supports CycloneDX 1.4+ JSON and XML formats.
"""

import json
import hashlib
import uuid
import subprocess
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """CycloneDX component types."""
    APPLICATION = "application"
    LIBRARY = "library"
    FRAMEWORK = "framework"
    CONTAINER = "container"
    OPERATING_SYSTEM = "operating-system"
    DEVICE = "device"
    FILE = "file"


class HashAlgorithm(Enum):
    """Supported hash algorithms."""
    MD5 = "MD5"
    SHA1 = "SHA-1"
    SHA256 = "SHA-256"
    SHA512 = "SHA-512"


@dataclass
class ComponentHash:
    """Hash of a component."""
    algorithm: HashAlgorithm
    value: str

    def to_dict(self) -> Dict[str, str]:
        return {"alg": self.algorithm.value, "content": self.value}


@dataclass
class ExternalReference:
    """External reference for a component."""
    type: str  # vcs, issue-tracker, website, documentation, etc.
    url: str
    comment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {"type": self.type, "url": self.url}
        if self.comment:
            data["comment"] = self.comment
        return data


@dataclass
class License:
    """License information."""
    id: Optional[str] = None  # SPDX ID
    name: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {}
        if self.id:
            data["license"] = {"id": self.id}
        elif self.name:
            data["license"] = {"name": self.name}
            if self.url:
                data["license"]["url"] = self.url
        return data


@dataclass
class Component:
    """CycloneDX component."""
    type: ComponentType
    name: str
    version: str
    bom_ref: Optional[str] = None
    supplier: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    group: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None  # required, optional, excluded
    hashes: List[ComponentHash] = field(default_factory=list)
    licenses: List[License] = field(default_factory=list)
    purl: Optional[str] = None  # Package URL
    external_refs: List[ExternalReference] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.bom_ref:
            self.bom_ref = f"{self.name}@{self.version}"

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "type": self.type.value,
            "name": self.name,
            "version": self.version,
            "bom-ref": self.bom_ref
        }

        if self.supplier:
            data["supplier"] = {"name": self.supplier}
        if self.author:
            data["author"] = self.author
        if self.publisher:
            data["publisher"] = self.publisher
        if self.group:
            data["group"] = self.group
        if self.description:
            data["description"] = self.description
        if self.scope:
            data["scope"] = self.scope
        if self.hashes:
            data["hashes"] = [h.to_dict() for h in self.hashes]
        if self.licenses:
            data["licenses"] = [lic.to_dict() for lic in self.licenses]
        if self.purl:
            data["purl"] = self.purl
        if self.external_refs:
            data["externalReferences"] = [r.to_dict() for r in self.external_refs]
        if self.properties:
            data["properties"] = [
                {"name": k, "value": v} for k, v in self.properties.items()
            ]

        return data


@dataclass
class Dependency:
    """Dependency relationship."""
    ref: str  # bom-ref of the component
    depends_on: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"ref": self.ref, "dependsOn": self.depends_on}


@dataclass
class SBOM:
    """CycloneDX Software Bill of Materials."""
    serial_number: str
    version: int
    metadata: Dict[str, Any]
    components: List[Component]
    dependencies: List[Dependency] = field(default_factory=list)
    spec_version: str = "1.4"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bomFormat": "CycloneDX",
            "specVersion": self.spec_version,
            "serialNumber": self.serial_number,
            "version": self.version,
            "metadata": self.metadata,
            "components": [c.to_dict() for c in self.components],
            "dependencies": [d.to_dict() for d in self.dependencies]
        }

    def to_json(self, indent: int = 2) -> str:
        """Export as JSON."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_xml(self) -> str:
        """Export as CycloneDX XML."""
        root = ET.Element("bom", {
            "xmlns": "http://cyclonedx.org/schema/bom/1.4",
            "version": str(self.version),
            "serialNumber": self.serial_number
        })

        # Metadata
        metadata = ET.SubElement(root, "metadata")
        timestamp = ET.SubElement(metadata, "timestamp")
        timestamp.text = self.metadata.get("timestamp", datetime.utcnow().isoformat())

        if "component" in self.metadata:
            comp = self.metadata["component"]
            comp_elem = ET.SubElement(metadata, "component", {"type": comp.get("type", "application")})
            name = ET.SubElement(comp_elem, "name")
            name.text = comp.get("name", "")
            version = ET.SubElement(comp_elem, "version")
            version.text = comp.get("version", "")

        # Components
        components = ET.SubElement(root, "components")
        for comp in self.components:
            comp_elem = ET.SubElement(components, "component", {
                "type": comp.type.value,
                "bom-ref": comp.bom_ref
            })
            name = ET.SubElement(comp_elem, "name")
            name.text = comp.name
            version = ET.SubElement(comp_elem, "version")
            version.text = comp.version

            if comp.purl:
                purl = ET.SubElement(comp_elem, "purl")
                purl.text = comp.purl

            if comp.licenses:
                licenses = ET.SubElement(comp_elem, "licenses")
                for lic in comp.licenses:
                    lic_elem = ET.SubElement(licenses, "license")
                    if lic.id:
                        id_elem = ET.SubElement(lic_elem, "id")
                        id_elem.text = lic.id
                    elif lic.name:
                        name_elem = ET.SubElement(lic_elem, "name")
                        name_elem.text = lic.name

        # Dependencies
        if self.dependencies:
            deps = ET.SubElement(root, "dependencies")
            for dep in self.dependencies:
                dep_elem = ET.SubElement(deps, "dependency", {"ref": dep.ref})
                for d in dep.depends_on:
                    ET.SubElement(dep_elem, "dependency", {"ref": d})

        return ET.tostring(root, encoding='unicode')


class SBOMGenerator:
    """
    Generates Software Bill of Materials.

    Supports multiple package ecosystems and output formats.
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize SBOM generator.

        Args:
            output_dir: Directory for SBOM output files
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / 'sbom'
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        project_path: str,
        project_name: Optional[str] = None,
        project_version: str = "1.0.0",
        include_dev: bool = False,
        output_format: str = "json"
    ) -> SBOM:
        """
        Generate SBOM for a project.

        Args:
            project_path: Path to project root
            project_name: Name of the project
            project_version: Version of the project
            include_dev: Include dev dependencies
            output_format: 'json' or 'xml'

        Returns:
            SBOM object
        """
        project_path = Path(project_path)
        project_name = project_name or project_path.name

        # Generate serial number
        serial_number = f"urn:uuid:{uuid.uuid4()}"

        # Build metadata
        metadata = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tools": [
                {
                    "vendor": "Fifth-9",
                    "name": "maestro-sbom-generator",
                    "version": "1.0.0"
                }
            ],
            "component": {
                "type": "application",
                "name": project_name,
                "version": project_version
            }
        }

        components = []
        dependencies = []

        # Scan Python dependencies
        if (project_path / 'requirements.txt').exists() or \
           (project_path / 'pyproject.toml').exists():
            py_components = self._scan_python(project_path, include_dev)
            components.extend(py_components)

        # Scan npm dependencies
        if (project_path / 'package.json').exists():
            npm_components, npm_deps = self._scan_npm(project_path, include_dev)
            components.extend(npm_components)
            dependencies.extend(npm_deps)

        # Create SBOM
        sbom = SBOM(
            serial_number=serial_number,
            version=1,
            metadata=metadata,
            components=components,
            dependencies=dependencies
        )

        # Save to file
        output_file = self.output_dir / f"{project_name}-sbom.{output_format}"
        with open(output_file, 'w') as f:
            if output_format == 'json':
                f.write(sbom.to_json())
            else:
                f.write(sbom.to_xml())

        logger.info(f"SBOM generated: {output_file} ({len(components)} components)")

        return sbom

    def _scan_python(self, project_path: Path, include_dev: bool) -> List[Component]:
        """Scan Python packages."""
        components = []

        try:
            result = subprocess.run(
                ['pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                packages = json.loads(result.stdout)

                for pkg in packages:
                    name = pkg['name']
                    version = pkg['version']

                    # Get license info
                    license_info = self._get_pip_license(name)

                    # Create purl
                    purl = f"pkg:pypi/{name}@{version}"

                    component = Component(
                        type=ComponentType.LIBRARY,
                        name=name,
                        version=version,
                        purl=purl,
                        licenses=[License(id=license_info)] if license_info else []
                    )
                    components.append(component)

        except Exception as e:
            logger.error(f"Error scanning Python packages: {e}")

        return components

    def _get_pip_license(self, package: str) -> Optional[str]:
        """Get license for pip package."""
        try:
            result = subprocess.run(
                ['pip', 'show', package],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('License:'):
                        return line.split(':', 1)[1].strip()

        except Exception:
            pass

        return None

    def _scan_npm(
        self, project_path: Path, include_dev: bool
    ) -> tuple[List[Component], List[Dependency]]:
        """Scan npm packages."""
        components = []
        dependencies = []

        try:
            cmd = ['npm', 'ls', '--json', '--all']
            if not include_dev:
                cmd.append('--production')

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=120
            )

            if result.stdout:
                data = json.loads(result.stdout)

                # Process root
                root_name = data.get('name', project_path.name)
                root_version = data.get('version', '1.0.0')

                deps = data.get('dependencies', {})
                root_deps = []

                for name, info in deps.items():
                    comp, child_deps = self._process_npm_package(name, info)
                    components.append(comp)
                    root_deps.append(comp.bom_ref)

                    if child_deps:
                        dependencies.append(Dependency(
                            ref=comp.bom_ref,
                            depends_on=child_deps
                        ))

                # Add root dependency
                if root_deps:
                    dependencies.append(Dependency(
                        ref=f"{root_name}@{root_version}",
                        depends_on=root_deps
                    ))

        except Exception as e:
            logger.error(f"Error scanning npm packages: {e}")

        return components, dependencies

    def _process_npm_package(
        self, name: str, info: Dict[str, Any]
    ) -> tuple[Component, List[str]]:
        """Process an npm package."""
        version = info.get('version', 'unknown')
        license_id = info.get('license')

        if isinstance(license_id, dict):
            license_id = license_id.get('type')
        elif isinstance(license_id, list):
            license_id = license_id[0].get('type') if license_id else None

        purl = f"pkg:npm/{name}@{version}"

        component = Component(
            type=ComponentType.LIBRARY,
            name=name,
            version=version,
            purl=purl,
            licenses=[License(id=license_id)] if license_id else []
        )

        # Get child dependencies
        child_deps = []
        for dep_name, dep_info in info.get('dependencies', {}).items():
            dep_version = dep_info.get('version', 'unknown')
            child_deps.append(f"{dep_name}@{dep_version}")

        return component, child_deps


def generate_sbom(project_path: str, **kwargs) -> SBOM:
    """Convenience function to generate SBOM."""
    generator = SBOMGenerator()
    return generator.generate(project_path, **kwargs)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    fmt = sys.argv[2] if len(sys.argv) > 2 else 'json'

    generator = SBOMGenerator()
    sbom = generator.generate(path, output_format=fmt)

    print(sbom.to_json())
