from setuptools import setup

setup(
    name='spotirec',
    version='1.3',
    author='Jonas Krogh',
    author_email='jonaskhansen@gmail.com',
    license='GPL3',
    url='https://github.com/Badgie/spotirec',
    download_url='https://github.com/Badgie/spotirec/archive/v1.3.tar.gz',
    keywords=['spotify', 'recommendation', 'music'],
    packages=['spotirec'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['bottle', 'requests', 'Pillow'],
    entry_points={
        'console_scripts': [
            'spotirec = spotirec.main:run'
        ]
    }
)
