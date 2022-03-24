from setuptools import setup

requirements = '''
    viable
'''

console_scripts = '''
    testpkg-example=testpkg.example:main
'''

name='testpkg'

packages=f'''
    {name}
'''

setup(
    name=name,
    packages=packages.split(),
    version='0.1',
    description='Testing viable',
    url='https://github.com/danr/viable',
    author='Dan Rosén',
    author_email='danr42@gmail.com',
    python_requires='>=3.10',
    license='MIT',
    install_requires=requirements.split(),
    entry_points={'console_scripts': console_scripts.split()}
)
