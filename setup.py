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
        'torpy',
    ],
    python_requires='>=3.6',
    packages=setuptools.find_packages(),
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    scripts=['ulozto-downloader'],
)
