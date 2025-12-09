#!/usr/bin/env python3
"""
License Scanner: SPDX-compatible license scanning for compliance.

Scans project dependencies for license compliance using SPDX identifiers.
Integrates with package managers (pip, npm) and provides violation detection.

EU AI Act Article 12 Compliance: Provides audit trail for third-party components.
SOC2 CC6.1: Change management control evidence.
"""

import json
import re
import subprocess
import hashlib
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class LicenseRisk(Enum):
    """Risk level for licenses."""
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    BANNED = "banned"
    UNKNOWN = "unknown"


class ScanStatus(Enum):
    """Status of a license scan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LicenseInfo:
    """Information about a package's license."""
    package: str
    version: str
    license_id: str  # SPDX identifier
    license_name: str
    risk_level: LicenseRisk
    is_compliant: bool
    source: str  # pip, npm, etc.
    repository_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['risk_level'] = self.risk_level.value
        return data


@dataclass
class LicenseViolation:
    """A license policy violation."""
    package: str
    version: str
    license_id: str
    violation_type: str  # banned, restricted_without_approval
    severity: str  # critical, high, medium, low
    reason: str
    remediation: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ScanResult:
    """Result of a license scan."""
    scan_id: str
    project_id: str
    status: ScanStatus
    started_at: str
    completed_at: Optional[str] = None
    packages_scanned: int = 0
    packages: List[LicenseInfo] = field(default_factory=list)
    violations: List[LicenseViolation] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'scan_id': self.scan_id,
            'project_id': self.project_id,
            'status': self.status.value,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'packages_scanned': self.packages_scanned,
            'packages': [p.to_dict() for p in self.packages],
            'violations': [v.to_dict() for v in self.violations],
            'summary': self.summary
        }
        return data


class LicensePolicy:
    """License policy configuration."""

    # Default SPDX-compliant allowed licenses
    DEFAULT_ALLOWED = {
        'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause',
        'ISC', 'Python-2.0', 'PSF-2.0', 'Unlicense', 'CC0-1.0',
        'MPL-2.0', 'WTFPL', 'Zlib', 'BSL-1.0'
    }

    # Restricted licenses (require approval)
    DEFAULT_RESTRICTED = {
        'GPL-2.0', 'GPL-3.0', 'LGPL-2.1', 'LGPL-3.0',
        'GPL-2.0-only', 'GPL-3.0-only', 'LGPL-2.1-only', 'LGPL-3.0-only',
        'AGPL-3.0', 'AGPL-3.0-only', 'EPL-1.0', 'EPL-2.0'
    }

    # Banned licenses
    DEFAULT_BANNED = {
        'SSPL-1.0', 'Commons-Clause', 'Elastic-2.0',
        'BUSL-1.1', 'Prosperity-3.0.0'
    }

    def __init__(
        self,
        allowed: Optional[Set[str]] = None,
        restricted: Optional[Set[str]] = None,
        banned: Optional[Set[str]] = None,
        exceptions: Optional[Dict[str, Dict]] = None
    ):
        """
        Initialize license policy.

        Args:
            allowed: Set of allowed SPDX license IDs
            restricted: Set of restricted license IDs
            banned: Set of banned license IDs
            exceptions: Package-specific exceptions {package: {reason, approver}}
        """
        self.allowed = allowed or self.DEFAULT_ALLOWED.copy()
        self.restricted = restricted or self.DEFAULT_RESTRICTED.copy()
        self.banned = banned or self.DEFAULT_BANNED.copy()
        self.exceptions = exceptions or {}

    @classmethod
    def from_yaml(cls, path: str) -> 'LicensePolicy':
        """Load policy from YAML file."""
        import yaml
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        return cls(
            allowed=set(config.get('allowed_licenses', [])),
            restricted=set(config.get('restricted_licenses', [])),
            banned=set(config.get('banned_licenses', [])),
            exceptions={e['package']: e for e in config.get('exceptions', [])}
        )

    def classify(self, package: str, license_id: str) -> LicenseRisk:
        """
        Classify a license for a package.

        Args:
            package: Package name
            license_id: SPDX license identifier

        Returns:
            LicenseRisk classification
        """
        # Check exceptions first
        if package in self.exceptions:
            return LicenseRisk.ALLOWED

        # Normalize license ID
        normalized = self._normalize_license(license_id)

        if normalized in self.allowed:
            return LicenseRisk.ALLOWED
        elif normalized in self.restricted:
            return LicenseRisk.RESTRICTED
        elif normalized in self.banned:
            return LicenseRisk.BANNED
        else:
            return LicenseRisk.UNKNOWN

    def _normalize_license(self, license_id: str) -> str:
        """Normalize license identifier to SPDX format."""
        # Common mappings
        mappings = {
            'MIT License': 'MIT',
            'Apache License 2.0': 'Apache-2.0',
            'Apache Software License': 'Apache-2.0',
            'BSD License': 'BSD-3-Clause',
            'BSD-3': 'BSD-3-Clause',
            'BSD-2': 'BSD-2-Clause',
            'Python Software Foundation License': 'PSF-2.0',
            'ISC License': 'ISC',
            'GNU General Public License v3': 'GPL-3.0',
            'GNU General Public License v2': 'GPL-2.0',
            'Mozilla Public License 2.0': 'MPL-2.0',
        }
        return mappings.get(license_id, license_id)


class LicenseScanner:
    """
    License scanner for compliance checking.

    Scans Python (pip) and JavaScript (npm) dependencies
    and checks against license policy.
    """

    def __init__(
        self,
        policy: Optional[LicensePolicy] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize license scanner.

        Args:
            policy: License policy to use
            cache_dir: Directory for caching scan results
        """
        self.policy = policy or LicensePolicy()
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / '.maestro' / 'license_cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._scan_counter = 0

    def scan(
        self,
        project_path: str,
        project_id: Optional[str] = None,
        include_dev: bool = False,
        scan_type: str = 'full'
    ) -> ScanResult:
        """
        Scan a project for license compliance.

        Args:
            project_path: Path to project root
            project_id: Optional project identifier
            include_dev: Include dev dependencies
            scan_type: 'full' or 'incremental'

        Returns:
            ScanResult with all packages and violations
        """
        project_path = Path(project_path)
        project_id = project_id or project_path.name

        # Generate scan ID
        self._scan_counter += 1
        scan_id = f"SCAN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._scan_counter:04d}"

        result = ScanResult(
            scan_id=scan_id,
            project_id=project_id,
            status=ScanStatus.IN_PROGRESS,
            started_at=datetime.utcnow().isoformat()
        )

        try:
            packages = []

            # Scan Python packages
            if (project_path / 'requirements.txt').exists() or \
               (project_path / 'pyproject.toml').exists() or \
               (project_path / 'setup.py').exists():
                packages.extend(self._scan_pip(project_path, include_dev))

            # Scan npm packages
            if (project_path / 'package.json').exists():
                packages.extend(self._scan_npm(project_path, include_dev))

            # Check each package against policy
            for pkg in packages:
                risk = self.policy.classify(pkg.package, pkg.license_id)
                pkg.risk_level = risk
                pkg.is_compliant = risk in (LicenseRisk.ALLOWED,)

                # Create violation if not compliant
                if risk == LicenseRisk.BANNED:
                    result.violations.append(LicenseViolation(
                        package=pkg.package,
                        version=pkg.version,
                        license_id=pkg.license_id,
                        violation_type='banned',
                        severity='critical',
                        reason=f"License {pkg.license_id} is banned by policy",
                        remediation=f"Remove or replace package {pkg.package}"
                    ))
                elif risk == LicenseRisk.RESTRICTED:
                    result.violations.append(LicenseViolation(
                        package=pkg.package,
                        version=pkg.version,
                        license_id=pkg.license_id,
                        violation_type='restricted_without_approval',
                        severity='high',
                        reason=f"License {pkg.license_id} requires approval",
                        remediation=f"Get approval or replace {pkg.package}"
                    ))
                elif risk == LicenseRisk.UNKNOWN:
                    result.violations.append(LicenseViolation(
                        package=pkg.package,
                        version=pkg.version,
                        license_id=pkg.license_id,
                        violation_type='unknown_license',
                        severity='medium',
                        reason=f"License {pkg.license_id} not in policy",
                        remediation=f"Review and classify license for {pkg.package}"
                    ))

            result.packages = packages
            result.packages_scanned = len(packages)
            result.status = ScanStatus.COMPLETED
            result.completed_at = datetime.utcnow().isoformat()

            # Generate summary
            result.summary = {
                'total_packages': len(packages),
                'compliant': sum(1 for p in packages if p.is_compliant),
                'violations': len(result.violations),
                'by_risk': {
                    'allowed': sum(1 for p in packages if p.risk_level == LicenseRisk.ALLOWED),
                    'restricted': sum(1 for p in packages if p.risk_level == LicenseRisk.RESTRICTED),
                    'banned': sum(1 for p in packages if p.risk_level == LicenseRisk.BANNED),
                    'unknown': sum(1 for p in packages if p.risk_level == LicenseRisk.UNKNOWN)
                },
                'by_source': {}
            }

            # Count by source
            for pkg in packages:
                result.summary['by_source'][pkg.source] = \
                    result.summary['by_source'].get(pkg.source, 0) + 1

            # Cache result
            self._cache_result(result)

            logger.info(f"Scan {scan_id} completed: {len(packages)} packages, "
                       f"{len(result.violations)} violations")

        except Exception as e:
            result.status = ScanStatus.FAILED
            result.summary = {'error': str(e)}
            logger.error(f"Scan {scan_id} failed: {e}")

        return result

    def _scan_pip(self, project_path: Path, include_dev: bool) -> List[LicenseInfo]:
        """Scan pip packages."""
        packages = []

        try:
            # Get installed packages with pip show
            result = subprocess.run(
                ['pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                pkg_list = json.loads(result.stdout)

                for pkg in pkg_list:
                    name = pkg['name']
                    version = pkg['version']

                    # Get license info
                    license_info = self._get_pip_license(name)

                    packages.append(LicenseInfo(
                        package=name,
                        version=version,
                        license_id=license_info.get('license', 'UNKNOWN'),
                        license_name=license_info.get('license_name', 'Unknown'),
                        risk_level=LicenseRisk.UNKNOWN,  # Will be set by policy
                        is_compliant=False,  # Will be set by policy
                        source='pip',
                        repository_url=license_info.get('home_page'),
                        metadata=license_info
                    ))

        except subprocess.TimeoutExpired:
            logger.warning("pip list timed out")
        except Exception as e:
            logger.error(f"Error scanning pip packages: {e}")

        return packages

    def _get_pip_license(self, package: str) -> Dict[str, str]:
        """Get license info for a pip package."""
        try:
            result = subprocess.run(
                ['pip', 'show', package],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                info = {}
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip().lower().replace('-', '_')] = value.strip()
                return info

        except Exception as e:
            logger.debug(f"Error getting license for {package}: {e}")

        return {'license': 'UNKNOWN'}

    def _scan_npm(self, project_path: Path, include_dev: bool) -> List[LicenseInfo]:
        """Scan npm packages."""
        packages = []

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

            # npm ls may return non-zero even with output
            if result.stdout:
                data = json.loads(result.stdout)
                packages.extend(self._parse_npm_tree(data.get('dependencies', {})))

        except subprocess.TimeoutExpired:
            logger.warning("npm ls timed out")
        except Exception as e:
            logger.error(f"Error scanning npm packages: {e}")

        return packages

    def _parse_npm_tree(self, deps: Dict, seen: Optional[Set] = None) -> List[LicenseInfo]:
        """Parse npm dependency tree recursively."""
        if seen is None:
            seen = set()

        packages = []

        for name, info in deps.items():
            if name in seen:
                continue
            seen.add(name)

            version = info.get('version', 'unknown')
            license_id = info.get('license', 'UNKNOWN')

            # Handle complex license objects
            if isinstance(license_id, dict):
                license_id = license_id.get('type', 'UNKNOWN')
            elif isinstance(license_id, list):
                license_id = ' OR '.join(l.get('type', str(l)) for l in license_id)

            packages.append(LicenseInfo(
                package=name,
                version=version,
                license_id=license_id,
                license_name=license_id,
                risk_level=LicenseRisk.UNKNOWN,
                is_compliant=False,
                source='npm',
                repository_url=info.get('resolved'),
                metadata={'npm_info': info}
            ))

            # Recurse into nested dependencies
            if 'dependencies' in info:
                packages.extend(self._parse_npm_tree(info['dependencies'], seen))

        return packages

    def _cache_result(self, result: ScanResult) -> None:
        """Cache scan result."""
        cache_file = self.cache_dir / f"{result.scan_id}.json"
        with open(cache_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

    def get_scan(self, scan_id: str) -> Optional[ScanResult]:
        """Retrieve a cached scan result."""
        cache_file = self.cache_dir / f"{scan_id}.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                data = json.load(f)
                # Reconstruct ScanResult
                return ScanResult(
                    scan_id=data['scan_id'],
                    project_id=data['project_id'],
                    status=ScanStatus(data['status']),
                    started_at=data['started_at'],
                    completed_at=data.get('completed_at'),
                    packages_scanned=data['packages_scanned'],
                    summary=data['summary']
                )
        return None


def get_license_scanner(**kwargs) -> LicenseScanner:
    """Get license scanner instance."""
    return LicenseScanner(**kwargs)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    scanner = LicenseScanner()
    result = scanner.scan(path)

    print(json.dumps(result.to_dict(), indent=2))
