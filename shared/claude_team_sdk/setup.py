"""
Setup script for Claude Team SDK
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="claude-team-sdk",
    version="1.0.0",
    author="MAESTRO Team",
    author_email="team@maestro.ai",
    description="True multi-agent collaboration framework using Claude Code SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/maestro/claude-team-sdk",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "claude-code-sdk>=0.0.25",
        "anyio>=4.0.0",
        "dynaconf>=3.2.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "database": [
            "sqlalchemy>=2.0.0",
            "asyncpg>=0.29.0",
        ],
        "all": [
            "sqlalchemy>=2.0.0",
            "asyncpg>=0.29.0",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "claude-team=claude_team_sdk.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "claude_team_sdk": ["py.typed"],
    },
)
