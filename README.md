# Black Sheep Foods

## Set Up
1. Fork this repository to a location on your computer
2. Make sure you have [Python 3.7](https://www.python.org/) and the [pip](https://pip.pypa.io/en/stable/) module installed. We also recommend using [pipenv](https://docs.pipenv.org/) to handle the virtual environment. You can install pipenv by typing `pip install --update pipenv`
3. Navigate to the root folder of this repository and run `pipenv shell` to start the virtual environment. (To exit a virtual environment, use `deactivate`)
4. Run `pipenv install` to install all the required package (listed in Pipfile). Note: If there is a conflict because the virtual environment is running another version of Python other than 3.7, run `pipenv --python 3.7`. If you are using pipenv and any of the packages fail to install, install the packages separately with `pipenv install package_name`.
5. Make a copy of `.env-example`, rename it `.env`, and change the value of the assorted keys (e.g. `SPRINGER_NATURE_API_KEY`) to your own API keys.

Now you can run `pipenv run python` activate the Python interpreter. The first two terms `pipenv run` ensure that your environement variables are accessible to the interpreter. 

If you access issues with finding the location of your virtual environment, you can use `pipenv --py` to access its path and use it directly in code editors like VSCode and Atom.


## Using the Scripts
You have two options: 

Option 1 (debugging): edit main_script.py by commenting out functions and using `pipenv run python main_script.py` from the bsf directory
Option 2: see below

### Loader
Put the articles you want to load into the `paiper/loader/articles` folder. Run the following code in a Python interpreter to load the data into the MongoDB database:
```
from paiper.loader import load_articles
load_articles()
```

### Classifier
#### Train model
To train the Classifier on the data you loaded, run the following code and specify the MongoDB collection you want to train the model on:
```
from paiper.classifier import Classifier
classifier = Classifier()
classifier.train_model(collection)
```
This will also pickle the model and store it in the `paiper/classifier/models` folder if the `save_pickle` flag is set to true.

#### Load vectorizer and model
To load an existing, pickled model into the Classifier object, run the following code and specify the vectorizer + model you want to load:
```
from paiper.classifier import Classifier
classifier = Classifier()
classifier.load_vectorizer(vectorizer_name)
classifier.load_model(model_name)
```
To use the model for prediction, run the following code:
```
classifier.predict(abstracts)
```
Note that you must specify both a vectorizer and model, or else the predictions will not run.

### For collaborators
If packages have been changed upstream, you can update your local environment with `pipenv sync` and `pipenv clean`.
