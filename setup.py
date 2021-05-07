#!/usr/bin/python3

from distutils.core import setup
import setuptools  # noqa

from ulozto_downloader import __version__

setup(
    name='ulozto-downloader',
    version=__version__,
    license='MIT',
    description='Uloz.to quick multiple sessions downloader.',
    # faile README.md failed (utf8) when pip install on win10 :(
    long_description="Uloz.to quick multiple sessions downloader.",
    author='Jiří Setnička and Vlado Driver',
    author_email='setnicka@seznam.cz',
    url='https://github.com/setnicka/ulozto-downloader',
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
    scripts=['ulozto-downloader.py']
)
