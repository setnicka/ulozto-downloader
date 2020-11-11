#!/usr/bin/python3

from distutils.core import setup
import setuptools  # noqa

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
  name='ulozto_downloader',
  version='1.4',
  license='MIT',
  description='Uloz.to quick multiple sessions downloader.',
  long_description=long_description,
  long_description_content_type="text/markdown",
  author='Jiří Setnička',
  author_email='setnicka@seznam.cz',
  url='https://github.com/setnicka/ulozto_downloader',
  install_requires=[
          'requests',
          'Pillow',
  ],
  python_requires='>=3.5',
  packages=setuptools.find_packages(),
  classifiers=[
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
  ],
  scripts=['ulozto-downloader']
)
