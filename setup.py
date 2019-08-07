#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="packet-networking",
    version="1.0",
    description="Tool used to setup the network files for an operating system.",
    author="Manny Mendez, Mike Mason",
    author_email="manny@packet.com, mason@packet.com",
    url="https://github.com/packethost/packet-networking/",
    packages=find_packages(),
    install_requires=[
        "click >=6.0,<7.0",
        "jinja2 >=2.9,<2.10",
        "lxml >=3.5,<3.6",
        "requests",
    ],
    tests_require=["pytest", "mock", "faker", "netaddr"],
    entry_points="""
        [console_scripts]
        packet-networking=packetnetworking.cli:cli
    """,
)
