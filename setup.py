#!/usr/bin/env python3

from distutils.core import setup
import setuptools  # noqa

from uldlib import __version__

with open("README.md", "r", encoding='utf8') as fh:
    long_description = fh.read()

setup(
    name='ulozto-downloader',
    version=__version__,
    license='MIT',
    description='Uloz.to quick multiple sessions downloader.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Jiří Setnička and Vlado Driver',
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
        'uvicorn',
        'fastapi',
        'starlette',
        'psutil'
    ],
    extras_require={
        "auto-captcha": ["tflite-runtime"],
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
