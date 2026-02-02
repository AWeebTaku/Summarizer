from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="text-summarizer-aweebtaku",
    version="1.2.4",
    author="Aditya Chaurasiya",
    author_email="adityachaurasiya57527@gmail.com",
    description="A text summarization tool using GloVe embeddings and PageRank algorithm",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AWeebTaku/Summarizer",
    packages=["text_summarizer", "text_summarizer.data"],
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "text-summarizer-aweebtaku=text_summarizer.cli:main",
            "text-summarizer-gui=text_summarizer.ui:main",
            "text-summarizer-shortcuts=text_summarizer.create_shortcuts:create_shortcuts",
        ],
    },
    include_package_data=True,
)