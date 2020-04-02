# Contributions
Any and all contributions to Spotirec are greatly appreciated.

## Issues
If you encounter a bug, or want a new feature in Spotirec, then please create an [issue](https://github.com/Badgie/spotirec/issues) using one of the templates. Before you make an issue, please ensure that your bug report or feature request is not already reported or requested.

## Pull requests
If you wish to directly contribute to Spotirec with a pull request, then please follow the below guide for set up (if need be) and then create a pull request.

### Things to consider
A few things to keep in mind when developing on Spotirec.

- If you include any print statements, be sure to use the `logger` object (unless you create a function to e.g. print genres).
    - Ensure that you use the correct logging levels, and to include meaningful verbose and debug prints.
- Include a meaningful docstring for each function, and meaningful inline comments for complex lines or line segments.
- If you include or change any functionality, be sure to update the README accordingly.
- Remember to reference the issue you are fixing, if any.
- Ensure that your changes did not break anything.
- You should remember to test any code you have included - see [tests](#tests)
- Ensure that your code style follows the standard - see [code style](#code-style)

### Prerequisites
Please ensure that the changes you wish to contribute are present in an issue. If they are not, then please first create an issue and wait for it to be approved. If what you are fixing or creating is very minor, this might not be necessary.

### Setup
First, fork the repo to your own account. Then create a new branch, e.g. `cool-feature` or `annoying-bug`, from the `dev` branch.

```
# clone the repo
$ git clone https://github.com/your-name/spotirec.git

# cd into spotirec
$ cd /path/to/spotirec

# set up virtual environment - ensure your current python version is the newest
$ python -m venv venv

# source your new virtual environment
$ source /path/to/venv/bin/activate

# install dependencies
(venv) $ pip install -r requirements.txt
```
You should now be set up and be good to go. Do a test run to make sure.
```
(venv) $ python spotirec.py
```

### Code style
Spotirec generally follows the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide, with a few exceptions

- Maximum line length is 100 characters, rather than 79
- There should not be a whitespace before `,` (E203)
- There should not be a line break before a binary operator (W503)
- The variable name `l` is allowed solely for the argparse argument, other than that E741 is followed, i.e. `l`, `O`, and `I` may not be used as variable names

To ensure your code is up to these standards, use `flake8`

```
# install
(venv) $ pip install flake8

# run
(venv) $ flake8
```

The configuration for `flake8` can be found in `tox.ini`

### Tests
The test suite can be run with

```
(venv) $ python test.py
```

If you want more output you can edit the test runner object in `./tests/lib/__init__.py`. Set `verbosity=5` for verbose output, and `tb_locals=True` for local variable prints on failures and errors. Remember to change these back before making a PR.

The test suite is located in `./tests/`. Each Spotirec file has its own test file. If you create a new file, ensure that it follows the same structure as the current ones.

If you include any static test data that is very large or otherwise better suited in a file, put the file in `./tests/fixtures/`

#### Coverage
You can use the `coverage` module to ensure that all your code is tested to some extent

```
(venv) $ pip install coverage
```

To run the tests and log coverage, run

```
(venv) $ coverage run -m unittest
```

You can then check the coverage with

```
# superficial output in terminal
coverage report

# generate html report with in-depth information for each file (located in ./htmlcov/
coverage html
```

The configuration for `coverage` can be found in `.coveragerc`
