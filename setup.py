# setup.py
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="overseer-meowxiik",  # Replace with your own username
    version='1.1.0',
    author="meowxiik",
    author_email="meowxiik@gmail.com",
    description="An app to control your behavior",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/richard-hajek/environment-overseer",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
