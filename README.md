# Black Sheep Foods
## Set Up
1. Fork this repository to your computer
2. Make sure you have [Python 3.6](https://www.python.org/) and the [pip](https://pip.pypa.io/en/stable/) module installed. We also recommend using [pipenv](https://docs.pipenv.org/) to handle the virtual environment. You can install pipenv by typing `pip install --update pipenv`. Alternatively, you can complete steps 3-4 by installing from `requirements.txt`
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
For your convenience, all of the scripts can be accessed by running `main_script.py` from the bsf directory with the appropriate command-line arguments. Each component is described below. For more information, run `pipenv run python main_script.py --help`.

Since a useful model requires at least 1 million abstracts as training data, this project can be segmented into three parts:
1. Classifying abstracts as relevant and irrelevant (**Loader** and **Classifier**)
2. Scraping papers and storing only those deemed relevant (**Scraper**)
3. Training a Word2Vec model to generate predictions (**Food2Vec**)


### Loader
Load specific article metadata (in .json format) to a MongoDB database. These articles should be flagged as relevant and irrelevant, as they are used to train **Classifier** (see below). We recommend using at least 100 relevant and 100 irrelevant articles for best results.

1. Upload at least one JSON file into the `paiper/loader/articles` folder. It should have a `name` field with the name of the dataset and an `articles` field with a list of articles. The `name` field will be the name of the MongoDB collection the data is stored in. The articles object should have an `id` field that uniquely identifies the article (DOIs or PubMedIDs are good IDs), a `title` field that is the name of the article, an `abstract` field with the abstract of the article, and a `relevant` field denotes if the article is relevant or not to your Word2Vec training set. See the repository for an example.
2. To load the articles into a MongoDB collection, run `pipenv run python main_script.py -l` from the bsf directory. A MongoDB collection will be created (if it doesn't already exist) that matches the name of the json file. If multiple json files are in the articles folder, then each file's contents will be added to their respective collections. You can modify this behavior by applying command line flags as specified by the help command.


### Classifier
Configure a binary classifier to reduce the number of irrelevant articles added to your MongoDB database (and improve results).

The Classifier class uses a TF-IDF vectorizer to vectorize the abstracts and a logistic regression model to predict whether an abstract is relevant. The constructor takes one argument, `tag`, which will be the label of all the articles deemed relevant by the Classifier.


#### Train Model
Train a binary classifier to mark new articles as relevant or irrelevant based on the training data provided in **Loader**.

1. Make sure you have completed the steps listed above in Loader. `classifier.py` must be able to access your MongoDB database in order to train.
2. Update the section under **Classifier** in `main_script.py` so that the name of the classifier matches the name of the relevant collection in MongoDB. For instance, if you have two collections in MongoDB titled "mark" and "robert", change the tags "matthew" and "gabby" listed in `main_script.py` accordingly.
3. To begin training, run `pipenv run python main_script.py -c`. This calls the `train_model()` function as described below:

The `train_model()` function will train the classifier model and save the resulting vectorizer and model in the `paiper/classifier/vectorizers` and `paiper/classifier/models` folders, respectively. The function scan take six optional arguments:

*  `database_name`: Defaults to 'classifier', the name of the database to get the articles from
*  `collection_name`: Defaults to the value of `tag`, the collection to get the articles from
*   `vectorizer_name`: Defaults to the value of `tag`, the name of the saved vectorizer file
*   `model_name`: Defaults to the value of `tag`, the name of the saved model file
*   `training_size`: Defaults to 0.8, the percentage of articles to go in the training set, remainder will go to the testing set
*   `random_state`: Defaults to 5, the state of the random number generator for the training/testing set splitter


#### Load vectorizer and model
By default, `main_script.py` will load the vectorizers and models associated with a given tag (defaults are "matthew" and "gabby"). To change this behavior, directly edit the corresponding function calls to `load_vectorizer()` and `load_model()` in the script.

If you already have a vectorizer and model, upload them to the appropriate folders in `paiper/classifier`. Then, run the `load_vectorizer()` and `load_model()` functions in `main_script.py` to load the files into the Classifier object.

The `load_vectorizer()` function can take an optional argument, `vectorizer_name`, which is the name of the file in the vectorizers folder to load. It defaults to the value of `tag`.

The `load_model()` function can take an optional argument, `model_name`, which is the name of the file in the models folder to load. It defaults to the value of `tag`.


### Scraper
Each database we scrape from (Springer Nature, Elsevier, and PubMed) has its own class, which are extensions of **Scraper**. Each database class has a function `scrape()` that queries a database and gathers the results. This function scrapes the data, processes the returned abstracts, determines their relevancy, and stores relevant abstracts in the MongoDB database.

To scrape all databases for a specific keyword, run `pipenv run python main_script.py --query "query" --all` from the bsf directory. For instance, to scrape articles from all databases with the search "food science," type `pipenv run python main_script.py --query "food science" --all` (quotation marks required).

You can also run the scrapers on a series of queries by specifying the keywords in a text file. Simply create a text file of your keywords in `paiper/scraper/keywords`. Then, run `pipenv run python main_script.py --keywords keywords.txt`, where `keywords.txt` is replaced by the name of your file.

See all of the command line flags for more options, such as restricting the search to specific databases or changing the MongoDB collection to store articles.

### Food2Vec
The Food2Vec class uses gensim's [Phrases](https://radimrehurek.com/gensim/models/phrases.html) model to extract phrases from the corpus and gensim's [Word2Vec](https://radimrehurek.com/gensim/models/word2vec.html) model to form word embeddings from the data. The Food2Vec constructor takes one positional argument, `tag`, which is the label the corresponding Classifier classified the relevant articles when storing it in the MongoDB database.

The `train_model()` function trains a Word2Vec model and saves the resulting phraser and model in `paiper/food2vec/phrasers` and `paiper/food2vec/models` respectively. The function takes eight optional arguments, which you can add directly in the corresponding function calls in `main_script.py` if you choose:

*  `database_name`: Defaults to 'abstracts', the name of the MongoDB database to get the articles from
*  `collection_name`: Defaults to the value of `all`, the MongoDB collection to get the articles from
*   `phrases`: Defaults to True, a Bool flag to extract phrases from corpus
*   `phraser_name`: Defaults to the value of `tag`, the name of the saved phraser file
*   `model_name`: Defaults to the value of `tag`, the name of the saved Word2Vec model file
*   `depth`: Defaults to 2, the number of passes to perform for phrase generation
*   `min_count`: Defaults to 10, the minimum number of occurrences for phrase to be considered
*   `threshold`: Defaults to 15.0, phrase importance threshold

If you already have a phraser file and a model file, upload them to the appropriate folders in `paiper/food2vec`. Then, update the `load_phraser()` and `load_model()` function calls in `main_script.py` as described below.

The `load_phraser()` function can take an optional argument, `phraser_name`, which is the name of the file in the phrasers folder to load. It defaults to the value of `tag`.

The `load_model()` function can take an optional argument, `model_name`, which is the name of the file in the models folder to load. It defaults to the value of `tag`.

To train the models and print results related to similarity/analogy, run `pipenv run python main_script.py -f -t`. If you want to load pretrained models, instead run `pipenv run python main_script.py -f`


The `most_similar()` function prints a list of words most similar to the queried word based on the corpus the Word2Vec model is trained on. The function takes two arguments:

*   `term`: The query term for which the most similar terms will be returned
*   `topn`: Defaults to 1, the number of most similar terms to return


The `analogy()` function prints a list of words that complete a given analogy based on the corpus the Word2Vec model is trained on. The format of the analogy as follows:

> `same` is to `opp` as `term` is to `analogy()`
>
> Example: cow is to beef as pig is to what?

The function takes three positional arguments and one optional argument:

*   `term`: The term to find the corresponding analogy to
*   `same`: The term in the given analogy that corresponds to the `term`
*   `opp`: The term in the given analogy that corresponds to the resulting term
*   `topn`: Defaults to 1, the number of most similar terms to return

Both `most_similar()` and `analogy()` will automatically be called whenever main_script.py is run with the `-f` flag specified.


### For collaborators
If packages have been changed upstream, you can update your local environment with `pipenv sync` and `pipenv clean`.


If you experience issues with finding the location of your virtual environment, you can use `pipenv --py` to access its path and use it directly in code editors like VSCode and Atom.

To change your pipenv python version, change the python version specified in the Pipfile and run the following commands:
```
pipenv shell
pipenv --rm
pipenv lock
pipenv install
```

## Acknowledgements
This project was inspired by the work of Tshitoyan et al. in [Unsupervised word embeddings capture latent knowledge from materials science literature](https://github.com/materialsintelligence/mat2vec). We utilized their processor `process.py` on the paper abstracts to improve the classifier's accuracy. Our preprocessing pipeline was also designed based on their suggestions. 
