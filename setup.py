"""
Setup script for AutoDev package.
"""
from setuptools import setup, find_packages
import os

# Read the contents of README.md
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# Read the requirements from requirements.txt
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = f.read().splitlines()

# Package metadata
setup(
    name="autodev",
    version="0.1.0",
    description="AI-powered software development assistant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AutoDev Team",
    author_email="info@autodev.ai",
    url="https://github.com/autodev/autodev",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "autodev=autodev.cli:main",
        ],
    },
)
