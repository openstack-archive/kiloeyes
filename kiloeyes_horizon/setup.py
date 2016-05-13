import setuptools
from setuptools import setup, find_packages

setuptools.setup(
    name='kiloeyes_horizon',
    version='0.0.1',
    url='https://github.com/openstack/kiloeyes/kiloeyes_horizon',
    author='Vishnu Govindaraj',
    author_email='vg249@cornell.edu',
    packages=find_packages(),
    include_package_data = True,
    setup_requires=['pbr'],
    pbr=True,
)
