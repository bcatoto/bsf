# Black Sheep Foods

### Set Up
1. Make sure you have [Python 3.7](https://www.python.org/) and the [pip](https://pip.pypa.io/en/stable/) module installed. We also recommend using [pipenv](https://docs.pipenv.org/) to handle the virtual environment.
2. Navigate to the root folder of this repository and run `pipenv shell` to activate the virtual environment.
3. Run `pipenv install` to install all the required packages. Note: If there is a conflict because the virtual environment is running another version of Python other than 3.7, run `pipenv --python 3.7`. If you are using pipenv and any of the packages fail to install, install the packages separately with `pipenv install package_name`.
4. Make a copy of `.env-example`, rename it `.env`, and change the value of the assorted keys (e.g. `SPRINGER_NATURE_API_KEY`) to your own API keys.

Now you can run `pipenv run python scraper.py` to test the scraper. The first two terms `pipenv run` ensure that your .env variables are accessible to the interpreter.
