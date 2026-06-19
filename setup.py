from setuptools import setup, find_packages

setup(
    name="TelegramGifts",
    version="0.1.0",
    author="Your Name",
    description="An offline Python library to fetch Telegram Gifts details, prices, and assets without any tokens or accounts.",
    long_description=open("README.md", encoding="utf-8").read() if open("README.md").read() else "",
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/TelegramGifts",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.1",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
