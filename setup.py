from setuptools import setup, find_packages

try:
    long_description = open("README.md").read()
except IOError:
    long_description = ""

setup(
    name="python-autoreload",
    version="0.1.0",
    description="Python autoreload library",
    license="MIT",
    author="Dan Rosén",
    entry_points={
        'console_scripts': [
            'python-autoreload = autoreload:main',
        ]
    },
    py_modules=["autoreload"],
    packages=['autoreload'],
    package_data={
        '.': ["*.js"],
    },
    install_requires=[ r for r in open("requirements.txt").read().split('\n') if not r.startswith('#') ],
    long_description=long_description,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ]
)
