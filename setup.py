from pathlib import Path
from setuptools import setup

requirements = Path('requirements.txt')
install_requires = []
for line in requirements.read_text(encoding='utf8').splitlines():
    req = line.strip()
    if req.startswith('#'):
        continue
    install_requires.append(req)

setup(
    name='trivialscan-api',
    version='0.0.2',
    author='Christopher Langton',
    author_email='chris@trivialsec.com',
    description='Validate the security of your TLS connections so that they deserve your trust.',
    long_description_content_type='text/markdown',
    url='https://gitlab.com/trivialsec/trivialscan-api',
    project_urls={
        'Source': 'https://gitlab.com/trivialsec/trivialscan-api',
        'Documentation': 'https://gitlab.com/trivialsec/trivialscan-api/-/blob/main/docs/0.index.md',
        'Tracker': 'https://gitlab.com/trivialsec/trivialscan-api/-/issues',
    },
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    ],
    include_package_data=True,
    install_requires=install_requires,
    python_requires='>=3.9',
    options={'bdist_wheel': {'universal': '1'}},
)
