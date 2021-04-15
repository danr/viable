from setuptools import setup

long_description = open('README.md').read()

setup(
    name='viable',
    version='0.1.0',
    description='Python viable library',
    url='https://github.com/danr/viable',
    license='MIT',
    author='Dan Rosén',
    author_email='danr42@gmail.com',
    py_modules=['viable'],
    install_requires=['flask'],
    long_description=long_description,
)
