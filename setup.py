from setuptools import setup

with open('README.md', 'r') as docs:
    long_description = docs.read()

setup(
    name='spotirec',
    version='1.3.1',
    author='Jonas Krogh',
    author_email='jonaskhansen@gmail.com',
    license='GPL3',
    url='https://github.com/Badgie/spotirec',
    download_url='https://github.com/Badgie/spotirec/archive/1.3.1.tar.gz',
    description='A tool for creating recommended playlists for Spotify',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords=['spotify', 'recommendation', 'music'],
    python_requires='>=3.6',
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
