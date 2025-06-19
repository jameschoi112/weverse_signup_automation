from setuptools import setup, find_packages

setup(
    name="weverse-automation",
    version="1.0.0",
    description="위버스 회원가입 자동화 도구",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "playwright>=1.40.0",
        "aiohttp>=3.9.0",
        "google-api-python-client>=2.110.0",
        "google-auth-httplib2>=0.2.0",
        "google-auth-oauthlib>=1.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "weverse-automation=scripts.run_automation:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)