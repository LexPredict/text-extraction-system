from os import path

# Always prefer setuptools over distutils
from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))


setup(
    name='lexpredict-text-extraction-system',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='1.0.0',

    description='LexPredict Text Extraction System',
    long_description='''LexPredict Text Extraction System: a tool for extracting the document text and structure ' \
from any document type.''',

    # The project's main homepage.
    url='https://contraxsuite.com',

    # Author details
    author='ContraxSuite, LLC',
    author_email='support@contraxsuite.com',

    # Choose your license
    license='AGPL',

    # version ranges for supported Python distributions
    python_requires='~=3.6',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Information Technology',
        'Intended Audience :: Legal Industry',
        'Intended Audience :: Developers',

        # Pick your license as you wish (should match "license" above)
        # 'License :: OSI Approved :: MIT License',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'License :: Other/Proprietary License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.8',

        # Topics
        'Natural Language :: English',
        'Topic :: Office/Business',
        'Topic :: Text Processing :: Linguistic',

    ],

    # What does your project relate to?
    keywords='text extraction legal contract document analytics nlp ml machine learning natural language',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['*tests*']),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    # py_modules=['lexnlp'],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'amqp==5.0.1',
        'appdirs==1.4.3',
        'argcomplete==1.10.0',
        'attrs==20.2.0',
        'beautifulsoup4==4.8.0',
        'billiard==3.6.3.0',
        'CacheControl==0.12.6',
        'camelot-py==0.8.2',
        'celery==5.0.1',
        'certifi==2019.11.28',
        'cffi==1.14.4',
        'chardet==3.0.4',
        'click==7.1.2',
        'click-didyoumean==0.0.3',
        'click-repl==0.1.6',
        'colorama==0.4.3',
        'contextlib2==0.6.0',
        'cryptography==3.3.1',
        'dataclasses-json==0.5.2',
        'datefinder-lexpredict==0.6.2.1',
        'dateparser==0.7.2',
        'distlib==0.3.0',
        'distro==1.4.0',
        'docopt==0.6.2',
        'docx2txt==0.8',
        'EbookLib==0.17.1',
        'et-xmlfile==1.0.1',
        'extract-msg==0.23.1',
        'fastapi==0.61.1',
        'fasttext==0.9.2',
        'gensim==3.8.3',
        'h11==0.11.0',
        'html5lib==1.0.1',
        'idna==2.8',
        'IMAPClient==2.1.0',
        'iniconfig==1.1.1',
        'ipaddr==2.2.0',
        'jdcal==1.4.1',
        'jellyfish==0.6.1',
        'joblib==0.14.0',
        'kombu==5.0.2',
        'langid==1.1.6',
        'lexnlp==1.8.0',
        'lockfile==0.12.2',
        'lxml==4.5.2',
        'marshmallow==3.8.0',
        'marshmallow-enum==1.5.1',
        'msgpack==0.6.2',
        'mypy-extensions==0.4.3',
        'nltk==3.5',
        'num2words==0.5.10',
        'numpy==1.19.4',
        'olefile==0.46',
        'opencv-python==4.4.0.46',
        'openpyxl==3.0.5',
        'packaging==20.3',
        'pandas==1.1.5',
        'pdf2image==1.14.0',
        'pdfminer.six==20201018',
        'pep517==0.8.2',
        'pikepdf==1.19.3',
        'Pillow==8.0.0',
        'pluggy==0.13.1',
        'progress==1.5',
        'prompt-toolkit==3.0.8',
        'psutil==5.7.3',
        'py==1.9.0',
        'pybind11==2.6.1',
        'pycountry==20.7.3',
        'pycparser==2.20',
        'pycryptodome==3.9.8',
        'pydantic==1.6.1',
        'pyparsing==2.4.6',
        'PyPDF2==1.26.0',
        'pytest==6.1.1',
        'pytest-asyncio==0.14.0',
        'python-dateutil==2.8.1',
        'python-dotenv==0.14.0',
        'python-multipart==0.0.5',
        'python-pptx==0.6.18',
        'pytoml==0.1.21',
        'pytz==2020.1',
        'redis==3.5.3',
        'regex==2020.7.14',
        'reporters-db==2.0.3',
        'requests==2.22.0',
        'requests-celery-adapters==2.0.14',
        'retrying==1.3.3',
        'scikit-learn==0.23.1',
        'scipy==1.5.1',
        'six==1.12.0',
        'smart-open==4.0.1',
        'sortedcontainers==2.2.2',
        'soupsieve==2.0.1',
        'SpeechRecognition==3.8.1',
        'starlette==0.13.6',
        'stringcase==1.2.0',
        'tabula-py==2.2.0',
        'threadpoolctl==2.1.0',
        'toml==0.10.1',
        'tqdm==4.54.1',
        'typing-extensions==3.7.4.3',
        'typing-inspect==0.6.0',
        'tzlocal==1.5.1',
        'Unidecode==1.1.1',
        'urllib3==1.25.8',
        'us==2.0.2',
        'uvicorn==0.12.1',
        'vine==5.0.0',
        'wcwidth==0.2.5',
        'webdavclient3==3.14.5',
        'webencodings==0.5.1',
        'xlrd==1.2.0',
        'XlsxWriter==1.3.7',
    ],
    dependency_links=[
    ],

    # Install any data files from packages.
    # The data files must be specified via the distutils’ MANIFEST.in file.
    include_package_data=True,

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'dev': ['pytest>=2.8.5', 'mock', 'pytz>=2015.7'],
        'test': ['pytest>=2.8.5', 'mock', 'pytz>=2015.7'],
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    # package_data={
    #     'sample': ['package_data.dat'],
    # },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    # entry_points={
    #     'console_scripts': [
    #         'sample=sample:main',
    #     ],
    # },
)
