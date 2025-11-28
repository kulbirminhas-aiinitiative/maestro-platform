"""
Setup configuration for ML Pipeline Orchestration
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ml-pipeline-orchestration",
    version="1.0.0",
    author="AI Developer Team",
    author_email="team@example.com",
    description="Production-ready ML pipeline orchestration with DAG execution engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/ml-pipeline-orchestration",
    packages=find_packages(exclude=["tests", "examples", "docs"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "isort>=5.13.0",
        ],
        "docs": [
            "mkdocs>=1.5.3",
            "mkdocs-material>=9.5.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "ml-pipeline=ml_pipeline.api:main",
        ],
    },
)