#!/usr/bin/env pyrhon3
from distutils.core import setup
import setuptools  # noqa

from uldlib import __version__

setup(
    name='uld',
    version=__version__,
    license='MIT',
    description='Uloz.to quick multiple sessions downloader.',
    long_description="Uloz.to quick multiple sessions downloader.",
    author='Jiří Setnička and Vlado Driver',
    author_email='vladodriver@gmail.com',
    url='https://gitlab.com/vladodriver/uld',
    package_data={'': ['model.tflite']},
    install_requires=[
        'requests',
        'Pillow',
        'ansicolors',
        'numpy',
        'pysocks',
        'stem',
    ],
    python_requires='>=3.8',
    packages=setuptools.find_packages(),
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    scripts=['uld.py'],
)
