# Contributions
Any and all contributions to Spotirec are greatly appreciated.

## Issues
If you encounter a bug, or want a new feature in Spotirec, then please create an [issue](https://github.com/Badgie/spotirec/issues) using one of the templates. Before you make an issue, please ensure that your bug report or feature request is not already reported or requested.

## Pull requests
If you wish to directly contribute to Spotirec with a pull request, then please follow the below guide for set up (if need be) and then create a pull request.

### Prerequisites
Please ensure that the changes you wish to contribute are present in an issue. If they are not, then please first create an issue and wait for it to be approved.

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

### Things to consider
A few things to keep in mind when developing on Spotirec.

- If you include any print statements, be sure to use the `logger` object (unless you create a function to e.g. print genres).
    - Ensure that you use the correct logging levels, and to include meaningful verbose and debug prints.
- Include a meaningful docstring for each function, and meaningful inline comments for complex lines or line segments.
- If you include or change any functionality, be sure to update the README accordingly.