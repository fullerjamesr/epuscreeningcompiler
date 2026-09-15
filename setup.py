from setuptools import setup

setup(
    name='epuscreeningcompiler',
    version='0.0.1',
    packages=['epuscreeningcompiler'],
    install_requires=['jinja2'],
    package_data={'epuscreeningcompiler': ['fonts/*.ttf', 'templates/*.j2']},
    url='',
    license='AGPL-3.0',
    author='James Fuller',
    author_email='fullerjamesr@gmail.com',
    description='A tool to convert fast-screening EPU data collections into a useful collection of files',
    entry_points={
        'console_scripts': ['epuscreeningcompiler=epuscreeningcompiler.main:main']
    }
)
