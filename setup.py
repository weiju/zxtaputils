import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

INSTALL_REQUIRES = []
setuptools.setup(
    name="zxtaputils",
    version="1.0.0",
    author="Wei-ju Wu",
    author_email="weiju.wu@gmail.com",
    description="TAP file related utilities for Sinclair ZX Spectrum",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/weiju/zxtaputils",
    packages=['zxtaputils'],
    install_requires = INSTALL_REQUIRES,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Education",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development",
        "Topic :: Utilities"
    ],
    keywords=[
        "sinclair", "zx", "spectrum", "tap", "development"
    ],
    scripts=['bin/bas2tap', 'bin/tapextract', 'bin/tapify', 'bin/tapinfo', 'bin/tapsplit', 'bin/tap2bas'])
