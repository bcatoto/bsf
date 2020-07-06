from paiper.processor import MaterialsTextProcessor
from pymongo import MongoClient, UpdateOne, DeleteOne
from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence
from progress.bar import ChargingBar
import spacy
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

def main():
    # CONVERTS ALL PROCESSED ABSTRACTS IN DATABASE SO THEY ARE SEGMENTED BY
    # SENTENCES
    collection = MongoClient(DATABASE_URL).abstracts.all
    processor = MaterialsTextProcessor()
    nlp = spacy.load('en_core_web_sm')

    print('Getting abstracts...')
    articles = list(collection.find({}, { 'abstract': 1 }))

    bar = ChargingBar(f'Updating abstracts:', max=len(articles), suffix='%(index)d of %(max)d')

    requests = []
    delete = []
    for article in articles:
        doc = nlp(article['abstract'])

        sents = []
        for sent in doc.sents:
            try:
                tokens, materials = self.processor.process(sent.text)
            except OverflowError:
                requests.append(DeleteOne({ '_id': article['_id'] }))
                continue

            processed_sent = ' '.join(tokens)
            sents.append(processed_sent)

        processed_abstract = '\n'.join(sents)

        # modifies existing document to include tag
        requests.append(UpdateOne(
            { '_id' : article['_id'] },
            { '$set': { 'processed_abstract': processed_abstract } }
        ))
        bar.next()
    bar.finished()

    print(f'Updating collection...')
    if requests:
        mongo = self._collection.bulk_write(requests)
        print(f'Modified: {mongo.modified_count}.')

    # articles = list(collection.find({ 'tags': 'matthew' }))
    #
    # abstracts = []
    # print('Getting articles...')
    # for article in articles:
    #     abstracts.append(article['processed_abstract'])
    #
    # sentences = '\n'.join(abstracts)
    #
    # # writes out corpus to text file
    # print('Printing corpus...')
    # outFile = open('corpus.txt', mode='w', encoding='ISO-8859-1')
    # outFile.write(sentences)
    # outFile.close()
    #
    # sentences = LineSentence(sentences)
    #
    # model = Word2Vec(
    #     sentences,
    #     window=8,
    #     min_count=5,
    #     workers=16,
    #     negative=15,
    #     iter=30
    # )
    # model.save("word2vec.model")


if __name__ == '__main__':
    main()
