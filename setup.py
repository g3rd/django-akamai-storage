from setuptools import setup, find_packages
from akamai_storage import __version__


setup(
    name="django-akamai-storage",
    description="Django storage engine that connects to Akamai NetStorage.",
    # long_description=open('README.md').read(),
    author='Chad Shryock',
    author_email='chad@g3rdmedia.com',
    license='MIT License (MIT)',
    url='https://github.com/g3rd/django-akamai-storage',
    download_url='https://github.com/g3rd/django-akamai-storage/zipball/master',
    version=__version__,
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(),
    install_requires=[
        "django-polymorphic>=0.5.6",
    ],
    requires = [
        "Django (>=1.7)",
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
