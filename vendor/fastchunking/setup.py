from setuptools import setup, Extension

setup(
    ext_modules=[
        Extension(
            "fastchunking._rabinkarprh",
            sources=["build/rabinkarprh.cpp", "lib/rabinkarp.cpp"],
            include_dirs=["lib"],
        )
    ]
)
