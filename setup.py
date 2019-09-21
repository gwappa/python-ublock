
import setuptools
from ublock import VERSION_STR

setuptools.setup(
    name='ublock',
    version=VERSION_STR,
    description='a toolkit for the control of trial-based behavioral tasks',
    url='https://github.com/gwappa/python-ublock',
    author='Keisuke Sehara',
    author_email='keisuke.sehara@gmail.com',
    license='MIT',
    install_requires=[
        'pyqtgraph>=0.10',
        ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        ],
    packages=setuptools.find_packages(),
    entry_points={
        # nothing for the time being
    }
)
