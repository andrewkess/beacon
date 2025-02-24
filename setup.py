from setuptools import setup, find_packages

setup(
    name="beacon",
    version="0.1.0",
    packages=find_packages(),  # Automatically find packages in the directory.
    install_requires=[
        "requests",  # List any dependencies your helper requires.
    ],
    author="Andrew Kessinger",
    author_email="andrewkessinger@gmail.com",
    description="A collection of helper functions for Beacon Agent",
    url="https://github.com/andrewkess/beacon",  # Update with your GitHub URL.
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
