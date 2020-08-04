from pymongo import MongoClient, UpdateOne, DeleteOne
from gensim.models import Word2Vec
from gensim.models.word2vec import FAST_VERSION
from gensim.models.phrases import Phrases, Phraser
from gensim.models import KeyedVectors
import regex
import os
import multiprocessing

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
PHRASERS_PATH = os.path.join(os.path.dirname(__file__), 'phrasers')
MODELS_PATH = os.path.join(os.path.dirname(__file__), 'models')
WV_PATH = os.path.join(os.path.dirname(__file__), 'wv')

COMMON_TERMS = ['-', '-', b'\xe2\x80\x93', b'\'s', b'\xe2\x80\x99s', 'from', 'as',
                'at', 'by', 'of', 'on', 'into', 'to', 'than', 'over', 'in', 'the',
                'a', 'an', '/', 'under', ':']
EXCLUDE_PUNCT = ['=', '.', ',', '(', ')', '<', '>', '\'', '“', '”', '≥', '≤', '<nUm>']

class Food2Vec:

    def __init__(self, tag):
        """
        Initializes collection

        :param tag: name of tag to filter articles for model training
        """
        self.tag = tag

    def _exclude_words(self, phrasegrams, words):
        """
        Given a list of words, excludes those from the keys of the phrase dictionary.
        (Written by mat2vec)
        """
        new_phrasergrams = {}
        words_re_list = []
        for word in words:
            we = regex.escape(word)
            words_re_list.append('^' + we + '$|^' + we + '_|_' + we + '$|_' + we + '_')
        word_reg = regex.compile(r''+'|'.join(words_re_list))
        for gram in phrasegrams:
            valid = True
            for sub_gram in gram:
                if word_reg.search(sub_gram.decode('unicode_escape', 'ignore')) is not None:
                    valid = False
                    break
                if not valid:
                    continue
            if valid:
                new_phrasergrams[gram] = phrasegrams[gram]
        return new_phrasergrams

    # Generating word grams.
    def _wordgrams(self, sent, depth, pc, th, d=0):
        """
        Builds word grams according to the specification.
        (Written by mat2vec)
        """
        if depth == 0:
            return sent, None
        else:
            phrases = Phrases(
                sent,
                common_terms=COMMON_TERMS,
                min_count=pc,
                threshold=th
            )

            grams = Phraser(phrases)
            grams.phrasegrams = self._exclude_words(grams.phrasegrams, EXCLUDE_PUNCT)
            d += 1
            if d < depth:
                return self._wordgrams(grams[sent], depth, pc, th, d)
            else:
                return grams[sent], grams

    def train_model(self, database_name='abstracts', collection_name='all', phraser_name=None, model_name=None, wv_name=None, depth=2, min_count=10, threshold=15.0):
        """
        Trains word2vec model based on dataset of tag

        :param database: defaults to 'classifier', database to get training data from
        :param collection_name: defaults to 'all', collection to get training data from
        :param phraser_name: defaults to tag, name of phraser file
        :param model_name: defaults to tag, name of Word2Vec model file
        :param wv_name: defaults to tag, name of word vectors file
        :param depth: defaults to 2, number of passes to perform for phrase generation
        :param min_count: defaults to 10, minimum number of occurrences for phrase to be considered
        :param threshold: defaults to 15.0, phrase importance threshold
        """
        # ensure that CPython version is being used
        assert FAST_VERSION > -1

        # initializes optional arguments to tag
        if phraser_name is None:
            phraser_name = self.tag
        if model_name is None:
            model_name = self.tag

        print(f'Collection: {database_name}.{collection_name}.')

        # queries relevant collection of MongoDB database
        print('Getting articles...')
        collection = MongoClient(DATABASE_URL)[database_name][collection_name]
        articles = list(collection.find(
            { 'tags': self.tag },
            { 'processed_abstract' : 1, '_id': 0 }
        ))
        print(f'Number of articles: {len(articles)}.')

        print('Getting sentences...')
        sentences = []
        for article in articles:
            abstract = article['processed_abstract'].split('\n')
            sentences += [sent.split(' ') for sent in abstract]

        # combines phrases in corpus
        print('Getting phrases...')
        sentences, phraser = self._wordgrams(
            sentences,
            depth=depth,
            pc=min_count,
            th=threshold
        )

        # saves phraser
        phraser.save(os.path.join(PHRASERS_PATH, f'{phraser_name}.pkl'))
        self._phraser = phraser

        # train word2vec model
        cores = multiprocessing.cpu_count()
        print('Training Word2Vec model...')
        model = Word2Vec(
            sentences,
            window=8,
            min_count=5,
            workers=cores,
            negative=15,
            iter=30
        )

        # saves word2vec model
        model.save(os.path.join(MODELS_PATH, model_name))
        model.wv.save(os.path.join(WV_PATH, wv_name))
        self._model = model
        self._wv = model.wv

        print('Model saved.')

    def continue_training(self, sentences, model_name=None, wv_name=None):
        self._model.train(
            sentences,
            total_examples=sentences.length,
            epochs=30
        )

        self._model.save(os.path.join(MODELS_PATH, model_name))
        self._model.wv.save(os.path.join(WV_PATH, wv_name))
        self._wv = self._model.wv

    def load_phraser(self, phraser_name=None):
        """
        Loads phraser from phrasers folder

        :param phraser_name: defaults to tag, the name of phraser file to load
        """
        # initializes optional arguments to tag
        if phraser_name is None:
            phraser_name = self.tag

        # loads phraser
        filename = os.path.join(PHRASERS_PATH, f'{phraser_name}.pkl')
        self._phraser = Phraser.load(filename)

    def load_model(self, model_name=None):
        """
        Loads Word2Vec model from models folder

        :param model_name: defaults to tag, the name of model file to load
        """
        # initializes optional arguments to tag
        if model_name is None:
            model_name = self.tag

        # loads model
        filename = os.path.join(MODELS_PATH, model_name)
        self._model = Word2Vec.load(filename)

    def load_wv(self, wv_name=None):
        """
        Loads word vectors from wv folder

        :param wv_name: defaults to tag, the name of word vectors file to load
        """
        # initializes optional arguments to tag
        if wv_name is None:
            wv_name = self.tag

        # loads word vectors
        filename = os.path.join(WV_PATH, wv_name)
        self._wv = KeyedVectors.load(filename, mmap='r')

    def most_similar(self, term, filter=False, vector_math=False, topn=1, closer='', farther='', stdout=True):
        """
        Returns terms most similar to query

        :param term: term to compare similarity to
        :param filter: defaults to False, bool flag for postprocessing via vector distance
        :param vector_math: defaults to False, bool flag for postprocessing via vector operations
        :param topn: defaults to 1, number of terms returned in order of similarity
        :param closer: term that results should be more closely related to (required if filter or vector_math is True)
        :param farther: term that results should be farther from (required if filter or vector_math is True)
        :param stdout: defaults to True, bool flag to indicate printing results
        """
        term = '_'.join(self._phraser[term.split(' ')])

        # note: could strengthen/reduce importance of other vectors with positive/negative connotation
        if stdout:
            print(f'Model: {self.tag}. Term: {term}.')

        try:
            similar = self._wv.most_similar(term, topn=topn)
        except KeyError:
            print(f'{term} not in vocabulary')
            print()
            return

        if stdout:
            print('Original results:')
            for result in similar:
                print(f'{result[0]}, {result[1]}')
            print()

        if vector_math:
            similar_math = self._wv.most_similar(
                positive=[term, closer],
                negative=[farther],
                topn=topn
            )

            if stdout:
                print('Vector math filter results:')
                for result in similar_math:
                    print(f'{result[0]}, {result[1]}')
                print()


        if filter:
            similar_filter = self._comparison_filter(similar, closer, farther)

            if stdout:
                if len(similar_filter) == 0:
                    print('No results for comparison filter')
                else:
                    print('Comparison filter results:')
                    for result in similar_filter:
                        print(result)
                print()

        return similar

    def analogy(self, term, same, opp, filter=False, topn=1, stdout=True):
        """
        Returns terms analogy based on given pair analogy
        Format: same is to opp as term is to analogy()
        Ex: cow is to beef as pig is to what?

        :param term: term to find analogy to
        :param same: term in given pair analogy that term is similar to
        :param opp: term in given pair analogy that analogy is looking for
        :param filter: defaults to False, bool flag indicating if output should be post-processed
        :param topn: defaults to 1, number of terms returned in order of similarity
        :param stdout: defaults to True, bool flag to indicate printing results
        """
        term = '_'.join(self._phraser[term.split(' ')])
        same = '_'.join(self._phraser[same.split(' ')])
        opp = '_'.join(self._phraser[opp.split(' ')])

        analogy = self._wv.most_similar(
            positive=[opp, term],
            negative=[same],
            topn=topn
        )

        if stdout:
            print(f'Model: {self.tag}. Term: {term}. Pair: {same} to {opp}.')
            for result in analogy:
                print(f'{result[0]}, {result[1]}')

        return analogy

    def _comparison_filter(self, results, closer, farther):
        """
        Filter the results by only including those more related to one term than another

        :param closer: term that is more important (i.e. 'plant')
        :param farther: term that we want to filter out (i.e. 'meat')
        """
        processed_results = [(x, y) for x, y in results if self._wv.similarity(x, closer) > self._wv.similarity(x, farther)]
        return processed_results
