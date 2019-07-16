import setuptools

setuptools.setup(
    name="pymotors",
    version="1.1.0",
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
        "CZ Biohub :: Bioengineering",
    ],
)
