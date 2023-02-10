from setuptools import setup

setup(
    name="WILLOW",
    packages=[],
    entry_points={
        "console_scripts": [
            "willow = WeepingWillow.CLI:main",
            "gui_willow = WeepingWillow.GUI:main",
        ]
    },
    version=open("WeepingWillow/version.txt", "r").readline()
)