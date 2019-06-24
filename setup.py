import setuptools

setuptools.setup(
    name="pymotors",
    version="0.0.1",
    author="Robert R. Puccinelli",
    author_email="robert.puccinelli@outlook.com",
    description="Motor utilities for general use.",
    url="https://github.com/czbiohub/PyMotors",
    packages=setuptools.find_packages(exclude=["*.tests", "*.tests.*",
                                               "tests.*", "tests"]),
    install_requires=[
        'pyserial',
        'smbus2'
    ],
    test_suite="tests",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Your Classifiers :: Go Here",
    ],
)
