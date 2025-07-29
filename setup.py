from setuptools import setup, find_packages

setup(
    name="llm-game-engine",
    version="0.1.0",
    description="A Python-based game engine for LLM-powered character interactions",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    python_requires=">=3.12",
    install_requires=[
        "openai>=1.0.0",
        "anthropic>=0.8.0",
        "requests>=2.31.0",
        "aiosqlite>=0.19.0",
        "pyyaml>=6.0",
        "jsonschema>=4.17.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.12",
    ],
)