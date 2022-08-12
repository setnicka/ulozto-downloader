#!/usr/bin/env python3

from distutils.core import setup
import setuptools  # noqa

from uldlib import __version__

with open("README.md", "r", encoding='utf8') as fh:
    long_description = fh.read()

setup(
    name='uld',
    version=__version__,
    license='MIT',
    description='Uloz.to quick multiple sessions downloader. This is fork of original https://github.com/setnicka/ulozto-downloader for pre-release pull-requests',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Jiří Setnička, vladodriver and many others..',
    author_email='setnicka@seznam.cz',
    url='https://github.com/setnicka/ulozto-downloader',
    package_data={'': ['model.tflite']},
    install_requires=[
        'requests',
        'Pillow',
        'ansicolors',
        'numpy',
        'pysocks',
        'stem',
        "appdirs"
    ],
    extras_require={
        "auto-captcha": ["tflite-runtime"],
        "auto-captcha": ['tensorflow ; platform_system=="Windows"']
    },
    python_requires='>=3.7',
    packages=setuptools.find_packages(),
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    entry_points={
        'console_scripts': [
            'ulozto-downloader = uldlib.cmd:run',
            'uld = uldlib.cmd:run',
        ]
    }
)
