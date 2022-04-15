from setuptools import setup, find_packages

setup(
    name="trivialscan-api",
    version="0.0.1",
    author='Christopher Langton',
    author_email='chris@trivialsec.com',
    description="Validate the security of your TLS connections so that they deserve your trust.",
    long_description="""
""",
    long_description_content_type="text/markdown",
    url="https://gitlab.com/trivialsec/trivialscan-api",
    project_urls={
        "Source": "https://gitlab.com/trivialsec/trivialscan-api",
        "Documentation": "https://gitlab.com/trivialsec/trivialscan-api/-/blob/main/docs/0.index.md",
        "Tracker": "https://gitlab.com/trivialsec/trivialscan-api/-/issues",
    },
    classifiers=[
        "Operating System :: OS Independent",
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
    include_package_data=True,
    install_requires=[
        'trivialscan==2.3.1',
        'fastapi==0.75.1',
        'validators==0.18.2',
        'uvicorn[standard]'
    ],
    python_requires=">=3.9",
    options={"bdist_wheel": {"universal": "1"}},
)
