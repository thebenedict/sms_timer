from setuptools import setup, find_packages
from setuptools import setup, find_packages
import sys, os

version = '.1'

setup(name='sms_timer',
      version=version,
      description="",
      long_description="""\
""",
      classifiers=[], 
      keywords='',
      author='',
      author_email='',
      url='',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'pytz',
          'pygsm',
          'pyyaml',
          'sqlobject',
      ],
      entry_points= {
          'console_scripts': [
              'start_sms = sms_timer:main'
              ],          
          } 
      )
