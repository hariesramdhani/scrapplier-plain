from setuptools import setup, find_packages

setup(
    name='scrapplier',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        # List your package dependencies here
        "pandas",
        "undetected-chromedriver",
    ],
    author='Haries Ramdhani',
    author_email='hydrolizedmaltose@gmail.com',
    description='A python package to scrape school and products information from the supplier website',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/hariesramdhani/scrapplier',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9.6',
)