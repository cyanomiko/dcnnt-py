import setuptools
from os import path


here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setuptools.setup(
    name='dcnnt',
    version='0.5.0',
    author='cyanomiko',
    author_email='cyanomiko@protonmail.com',
    description='UI-less tool to connect Android phone with desktop',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/cyanomiko/dcnnt-py',
    packages=setuptools.find_packages(),
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Communications :: File Sharing',
        'Topic :: System :: Networking',
    ],
    keywords=['phone', 'android', 'sync', 'device'],
    python_requires='>=3.6',
    install_requires=['pycryptodome>=3.9.3'],
    entry_points={
        'console_scripts': [
            'dcnnt=dcnnt.dcnnt:main',
        ],
    },
)
