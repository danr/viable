from setuptools import setup

requirements = '''
    flask
    sorcery
    inotify_simple
'''

console_scripts = '''
'''

name='viable'

packages=f'''
    {name}
'''

setup(
    name=name,
    packages=packages.split(),
    version='0.1',
    description='A viable alternative to frontend programming from python',
    url='https://github.com/danr/viable',
    author='Dan Rosén',
    author_email='danr42@gmail.com',
    python_requires='>=3.10',
    license='MIT',
    install_requires=requirements.split(),
    entry_points={'console_scripts': console_scripts.split()}
)
