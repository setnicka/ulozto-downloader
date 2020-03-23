#!/usr/bin/python3

from distutils.core import setup
import setuptools  # noqa

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
  name='ulozto_downloader',
  version='1.3',
  license='MIT',
  description='Uloz.to quick multiple sessions downloader.',
  long_description=long_description,
  long_description_content_type="text/markdown",
  author='Jiří Setnička',
  author_email='setnicka@seznam.cz',
  url='https://github.com/setnicka/ulozto_downloader',
  download_url='https://github.com/setnicka/ulozto_downloader/archive/1.3.tar.gz',
  install_requires=[
          'requests',
          'Pillow',
  ],
  python_requires='>=3.5',
  classifiers=[
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
  ],
)
