from setuptools import setup, find_packages

setup(
    name="custom-ai-agent",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[],
    python_requires=">=3.7",
    author="Handsome Agent Team",
    description="Modular AI Agent framework",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
    ],
)
