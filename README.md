# Black Sheep Foods

### Set Up
1. Fork this repository to a location on your computer
2. Make sure you have [Python 3.7](https://www.python.org/) and the [pip](https://pip.pypa.io/en/stable/) module installed. We also recommend using [pipenv](https://docs.pipenv.org/) to handle the virtual environment. You can install pipenv by typing `pip install --update pipenv`
3. Navigate to the root folder of this repository and run `pipenv shell` to start the virtual environment. (To exit a virtual environment, use `deactivate`)
4. Run `pipenv install` to install all the required package (listed in Pipfile). Note: If there is a conflict because the virtual environment is running another version of Python other than 3.7, run `pipenv --python 3.7`. If you are using pipenv and any of the packages fail to install, install the packages separately with `pipenv install package_name`.
5. Make a copy of `.env-example`, rename it `.env`, and change the value of the assorted keys (e.g. `SPRINGER_NATURE_API_KEY`) to your own API keys.

Now you can run `pipenv run python scraper.py` to test the scraper. The first two terms `pipenv run` ensure that your .env variables are accessible to the interpreter. 

If you access issues with finding the location of your virtual environment, you can use `pipenv --py` to access its path and use it directly in code editors like VSCode and Atom. 

### For collaborators
If packages have been changed upstream, you can update your local environment with `pipenv sync`.