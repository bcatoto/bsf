# Black Sheep Foods
## Set Up
1. Fork this repository to a location on your computer
2. Make sure you have [Python 3.6](https://www.python.org/) and the [pip](https://pip.pypa.io/en/stable/) module installed. We also recommend using [pipenv](https://docs.pipenv.org/) to handle the virtual environment. You can install pipenv by typing `pip install --update pipenv`
3. Navigate to the root folder of this repository and run `pipenv shell` to start the virtual environment. (To exit a virtual environment, use `deactivate`)
4. Run `pipenv install` to install all the required packages (listed in Pipfile). Note: If there is a conflict because the virtual environment is running another version of Python other than 3.6, run `pipenv --python 3.6`. If you are using pipenv and any of the packages fail to install, install the packages separately with `pipenv install package_name`.
5. You will also need to run the following commands to download data:
```
cde data download
python -m spacy download en_core_web_sm 
```
6. Make a copy of `.env-example`, rename it `.env`, and change the value of the assorted keys (e.g. `SPRINGER_NATURE_API_KEY`) to your own API keys. You can find these API keys at the [Elsevier](https://dev.elsevier.com/), [Springer Nature](https://dev.springernature.com/), and [PubMed](https://www.ncbi.nlm.nih.gov/home/develop/api/) developer sites.

7. Now you can run `pipenv run python` to activate the Python interpreter. The terms `pipenv run` ensure that your environment variables are accessible to the interpreter. To run a script, use `pipenv run python filename` (described further below).


## Using the Scripts
For your convenience, all of the scripts can be accessed by running `main_script.py` with the appropriate command-line arguments from the bsf directory. Each component is described in more depth below. For more information, run `pipenv run python main_script.py --help`.


### Loader
Load specific article metadata (in .json format) to a MongoDB database. These articles should be flagged as relevant and irrelevant, as they are used to train **Classifier** (see below). 

1. Put the articles you want to load into the `paiper/loader/articles` folder. They must be in .json form (see repository for example)
2. To load the articles into a MongoDB collection, run `pipenv run python main_script.py -l` from the bsf directory. A MongoDB collection will be created (if it doesn't already exist) that matches the name of the json file. If multiple json files are in the articles folder, then each file's contents will be added to their respective collections.


### Classifier
Configure a binary classifier to reduce the number of irrelevant articles added to your MongoDB database (and improve results).


#### Train Model
Train a binary classifier to mark new articles as relevant or irrelevant based on the training data provided in **Loader**.
The `train_model()` method in the Classifier class takes a set of annotated article abstracts from MongoDB. It converts each abstract into a vector using either tf-idf or Doc2Vec (depending on the flag specified). For training, it uses logistic regression. 

1. Make sure you have completed the steps listed above in Loader. `classifier.py` must be able to access the articles in MongoDB in order to train.
2. Update the section under **Classifier** in `main_script.py` so that the name of the classifier matches the name of the relevant collection in MongoDB. For instance, if you have two collections in MongoDB titled "mark" and "robert", change the tags "matthew" and "gabby" listed in `main_script.py` accordingly. 
3. To begin training, run `pipenv run python main_script.py -c`.
4. By default, your models will be pickled and stored in the `paiper/classifier/models` folder. To change this, add the appropriate parameter `save_pickle=False` inside the call(s) to `train_model()` in `main_script.py`. You can also adjust other elements like the training/testing split and the random_state() from here.


#### Load vectorizer and model
By default, any call to `main_script.py` will load the vectorizers and models associated with a given tag (defaults are "matthew" and "gabby"). To change this, see #2 under **train model** above.

To use the model for prediction, add the line `classifier.predict(abstracts)` in `main_script.py` below the calls to load the vectorizers and models. The parameter "abstracts" should be a list of preprocessed abstracts to be marked as relevant and irrelevant. 

Note that you must specify both a vectorizer and model first, or else the predictions will not run.


### Scraper
There are three different classes for each database (Springer Nature, Elsevier, and PubMed) that are extensions of the Scraper class. Each class has a scrape function that queries a database and gathers the results. This function scrapes the data, processes the returned abstracts, determines their relevancy, and stores relevant abstracts in the MongoDB database. 

To scrape all databases for a specific keyword, run `pipenv run python main_script.py --query "query" --all` from the bsf directory. For instance, to scrape articles from all databases with the search "food science," type `pipenv run python main_script.py --query "food science" --all` (quotation marks required). 

You can also automate this process by running the scrapers for a series of independent searches. To do this, update `keywords.txt`, located in `paiper/scraper/keywords`. Then, run `pipenv run python main_script.py -k`.

See all of the command line flags for more options, such as restricting the search to specific databases or changing the MongoDB collection to store articles.

### Food2Vec
More coming soon!


### For collaborators
If packages have been changed upstream, you can update your local environment with `pipenv sync` and `pipenv clean`.


If you experience issues with finding the location of your virtual environment, you can use `pipenv --py` to access its path and use it directly in code editors like VSCode and Atom.


## Acknowledgements
This project was inspired by the work of Tshitoyan et al. in [Unsupervised word embeddings capture latent knowledge from materials science literature](https://github.com/materialsintelligence/mat2vec). We utilized their processor `process.py` on the paper abstracts to improve the classifier's accuracy.

