#!/usr/bin/python3

from distutils.core import setup
import setuptools  # noqa

from ulozto_downloader import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
  name='ulozto-downloader',
  version=__version__,
  license='MIT',
  description='Uloz.to quick multiple sessions downloader.',
  long_description=long_description,
  long_description_content_type="text/markdown",
  author='Jiří Setnička',
  author_email='setnicka@seznam.cz',
  url='https://github.com/setnicka/ulozto-downloader',
  install_requires=[
            'requests',
            'Pillow',
            'ansicolors',
            'numpy',
            # Currently it is forbidden to upload packages to PyPI which depends on URL requirements... :(
            # 'tflite_runtime @ https://github.com/google-coral/pycoral/releases/download/release-frogfish/tflite_runtime-2.5.0-cp36-cp36m-linux_x86_64.whl ; python_version == "3.6" and platform_system == "Linux" and platform_machine == "x86_64"',
            # 'tflite_runtime @ https://github.com/google-coral/pycoral/releases/download/release-frogfish/tflite_runtime-2.5.0-cp37-cp37m-linux_x86_64.whl ; python_version == "3.7" and platform_system == "Linux" and platform_machine == "x86_64"',
            # 'tflite_runtime @ https://github.com/google-coral/pycoral/releases/download/release-frogfish/tflite_runtime-2.5.0-cp38-cp38-linux_x86_64.whl ; python_version == "3.8" and platform_system == "Linux" and platform_machine == "x86_64"',
            # 'tflite_runtime @ https://github.com/google-coral/pycoral/releases/download/release-frogfish/tflite_runtime-2.5.0-cp36-cp36m-win_amd64.whl ; python_version == "3.6" and platform_system == "Windows"',
            # 'tflite_runtime @ https://github.com/google-coral/pycoral/releases/download/release-frogfish/tflite_runtime-2.5.0-cp37-cp37m-win_amd64.whl ; python_version == "3.7" and platform_system == "Windows"',
            # 'tflite_runtime @ https://github.com/google-coral/pycoral/releases/download/release-frogfish/tflite_runtime-2.5.0-cp38-cp38-win_amd64.whl ; python_version == "3.8" and platform_system == "Windows"'
  ],
  python_requires='>=3.6',
  packages=setuptools.find_packages(),
  classifiers=[
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
  ],
  scripts=['ulozto-downloader']
)
