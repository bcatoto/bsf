from paiper.processor import MaterialsTextProcessor
from pymongo import MongoClient, UpdateOne, DeleteOne
from gensim.models import Word2Vec
from gensim.models.word2vec import FAST_VERSION as FastVersion
from gensim.models.phrases import Phrases, Phraser
from progress.bar import ChargingBar
import regex
import os
import multiprocessing

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
MODELS_PATH = os.path.join(os.path.dirname(__file__), 'models')
PHRASERS_PATH = os.path.join(os.path.dirname(__file__), 'phrasers')

COMMON_TERMS = ['-', '-', b'\xe2\x80\x93', b'\'s', b'\xe2\x80\x99s', 'from', 'as',
                'at', 'by', 'of', 'on', 'into', 'to', 'than', 'over', 'in', 'the',
                'a', 'an', '/', 'under', ':']
EXCLUDE_PUNCT = ['=', '.', ',', '(', ')', '<', '>', '\'', '“', '”', '≥', '≤', '<nUm>']

class Food2Vec:

    def __init__(self, tag, collection = 'all'):
        """
        Initializes collection
        :param tag: name of tag to filter articles for model training
        :param collection: defaults to 'all', collection to get abstracts from
        """
        self.tag = tag
        self._collection = MongoClient(DATABASE_URL).abstracts[collection]
        print(f'Collection: {collection}. Tag: {tag}.')

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

    def train_model(self, phrases=True, depth=2, min_count=10, threshold=15.0):
        """
        Trains word2vec model based on dataset of tag
        :param phrases: defaults to True, Bool flag to extract phrases from corpus
        :param depth: defaults to 2, number of passes to perform for phrase generation
        :param min_count: defaults to 10, minimum number of occurrences for phrase to be considered
        :param threshold: defaults to 15.0, phrase importance threshold
        """
        # ensure that C version is being used
        assert FastVersion > -1

        # gets only processed abstracts from database
        print('Getting articles...')
        articles = list(self._collection.find(
            { 'tags': self.tag },
            { 'processed_abstract' : 1, '_id': 0 }
        ))
        print(f'Number of articles: {len(articles)}.')
        
        sentences = []
        for article in articles:
            abstract = article['processed_abstract'].split('\n')
            sentences += [sent.split(' ') for sent in abstract]

        # combines phrases in corpus
        if phrases:
            print('Getting phrases...')
            sentences, phraser = self._wordgrams(
                sentences,
                depth=depth,
                pc=min_count,
                th=threshold
            )

            # saves phraser
            phraser.save(os.path.join(PHRASERS_PATH, f'{self.tag}.pkl'))
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
        model.save(os.path.join(MODELS_PATH, self.tag))
        self._model = model

        print('Model saved.')

    def load_model(self):
        """
        Loads the specific word2vec model associated with tag
        """
        filename = os.path.join(MODELS_PATH, self.tag)
        self._model = Word2Vec.load(filename)

    def load_phraser(self):
        filename = os.path.join(PHRASERS_PATH, f'{self.tag}.pkl')
        self._phraser = Phraser.load(filename)

    def most_similar(self, term, topn=1):
        """
        Returns terms most similar to query
        :param term: term to compare similarity to
        :topn: default to 1, number of terms returned in order of most similar
        """
        term_phrase = ' '.join(self._phraser[term.split(' ')])
        similar = self._model.wv.most_similar(term_phrase, topn=topn)

        print(f'Model: {self.tag}, Term: {term_phrase}')
        for result in similar:
            print(f'\t{result[0]}, {result[1]}')

    def analogy(self, term, same, opposite, topn=1):
        """
        Returns terms analogy based on given pair analogy
        :param term: term to find analogy to
        :param same: term in given pair analogy that term is similar to
        :param opposite: term in given pair analogy that analogy is looking for
        :topn: default to 1, number of terms returned in order of most similar
        """
        term_phrase = ' '.join(self._phraser[term.split(' ')])
        same_phrase = ' '.join(self._phraser[same.split(' ')])
        opp_phrase = ' '.join(self._phraser[opposite.split(' ')])

        analogy = self._model.wv.most_similar(
            positive=[opp_phrase, term_phrase],
            negative=[same_phrase],
            topn=topn
        )

        print(f'Model: {self.tag}, Term: {term_phrase}, Pair: {same_phrase} to {opp_phrase}')
        for result in analogy:
            print(f'\t{result[0]}, {result[1]}')
