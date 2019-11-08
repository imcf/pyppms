"""Setup for the pumapy package."""

from setuptools import setup

setup(
    name='pumapy',
    version='1.0.0',
    packages=['pumapy'],
    package_dir={'': 'src'},
    url='https://github.com/imcf/pumapy',
    license='GPLv3',
    author='Niko Ehrenfeuchter',
    author_email='nikolaus.ehrenfeuchter@unibas.ch',
    description="A Python 3 package to communicate with Stratocore's PUMAPI.",
    install_requires=['requests']
)
