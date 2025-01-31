from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import sent_tokenize
from gensim.models import Phrases
from gensim.models.word2vec import Word2Vec
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import pandas as pd
from lib2to3.pgen2 import parse
from scipy import spatial
import spacy
from ConversationalService import  SpellCheck as sp
from ConversationalService import NegationDetection as ng
from tqdm import tqdm
from ConversationalService.TwitterSentimentAnalyzer import TwitterSentimentAnalyzer
import time
import math
#from pandas.io.sas.sas_constants import index
#from pandas.io.tests.parser import index_col
import sys
#reload(sys)
#sys.setdefaultencoding('utf8')
import pickle
dataset=pd.read_excel("ConversationalService/ConversationLogs.xlsx",parse_cols = "A,D")
#nlp=spacy.load('en',disable=['parser'])
nlp=spacy.load('en_core_web_sm')
pkl_filename="BankingClassifierLR.pkl"

pkl_filename="ConversationalService/BankingConversationalLogsTFIDF.pkl"
with open(pkl_filename, 'rb') as file:
    tfidf = pickle.load(file)


with open(pkl_filename, 'rb') as file:
    IntentClassifer = pickle.load(file)

pkl_filename="ConversationalService/IntentClassifierTFIDF.pkl"
with open(pkl_filename, 'rb') as file:
    IntentClassiferBanking = pickle.load(file)

def Data_Cleaner(sentence_text):
    lemmatize = True
    stem = False
    remove_stopwords = True

    stops = set(stopwords.words("english"))
    words = sentence_text.lower().split()
    # Optional stemmer
    if stem:
        stemmer = PorterStemmer()
        words = [stemmer.stem(w) for w in words]

    if lemmatize:
        lemmatizer = WordNetLemmatizer()
        words = [lemmatizer.lemmatize(w) for w in words]

    # Optionally remove stop words (false by default)
    if remove_stopwords:
        words = [w for w in words if not w in stops]

    return words


def display_closestwords_tsnescatterplot(model, word):
    arr = np.empty((0, 300), dtype='f')
    word_labels = [word]

    # get close words
    close_words = model.similar_by_word(word)

    # add the vector for each of the closest words to the array
    arr = np.append(arr, np.array([model[word]]), axis=0)
    for wrd_score in close_words:
        wrd_vector = model[wrd_score[0]]
        word_labels.append(wrd_score[0])
        arr = np.append(arr, np.array([wrd_vector]), axis=0)

    # find tsne coords for 2 dimensions
    tsne = TSNE(n_components=2, random_state=0)
    np.set_printoptions(suppress=True)
    Y = tsne.fit_transform(arr)

    x_coords = Y[:, 0]
    y_coords = Y[:, 1]
    # display scatter plot
    plt.scatter(x_coords, y_coords)

    for label, x, y in zip(word_labels, x_coords, y_coords):
        plt.annotate(label, xy=(x, y), xytext=(0, 0), textcoords='offset points')
    plt.xlim(x_coords.min() + 0.00005, x_coords.max() + 0.00005)
    plt.ylim(y_coords.min() + 0.00005, y_coords.max() + 0.00005)
    plt.show()

model=Word2Vec.load("ConversationalService/Twitter_Sentiment_model_W2V")
#model=Word2Vec.load("ConversationalService/updatedInsurance_word2vec_v3_18650_tri1")
#display_closestwords_tsnescatterplot(model, 'pay')

#vector building

def ClassifierOnload():
    vec = np.zeros(model.wv.syn0.shape[1]).reshape((1, model.wv.syn0.shape[1]))
    train_vecs_w2v = vec
    for utterence in list(dataset['Query']):
        print(utterence)
        words = Data_Cleaner(str(utterence))
        count = 0
        for word in words:
            try:
                print(word)
                vec += model.wv[word]
                count += 1
            except KeyError:
                continue
            if count != 0:
                vec /= count
        train_vecs_w2v = np.append(train_vecs_w2v, vec, axis=0)

    train_vecs_w2v = train_vecs_w2v[1:]
    train_intent = (dataset['Intent']).to_frame()
    train_vecs_w2v = pd.DataFrame(train_vecs_w2v)

    final_vector_frame = pd.concat([train_intent, train_vecs_w2v], axis=1, ignore_index=True)
    final_vector_frame.to_excel("ConversationalService/final_vector_frame.xlsx")

    datatable = pd.read_excel("ConversationalService/final_vector_frame.xlsx")

    datatable.loc[:, 1:]

    # for i in range(0,datatable.__len__()-1):
    #     vec = np.zeros(200).reshape((1, 200))
    #     i=0
    #     for x in (datatable.loc[i,1:]):
    #         i+=1
    #         print i
    #         vec+=(datatable.loc[i,1:])[x]

    for i in range(0, datatable.__len__() - 1):
        vec = np.sum(np.array(datatable.loc[i, 1:]))

    utterence = "I want to open recurring deposit account"

    query_vector = vectorize_query(utterence)
    resultTable = pd.DataFrame(columns=['Score'])
    for i in range(0, datatable.__len__()):
        vec = (np.array(datatable.loc[i, 1:]))
        score = spatial.distance.cosine(query_vector, vec)
        resultTable.loc[len(resultTable)] = score

    score_card = pd.concat([resultTable, datatable], axis=1, ignore_index=True)
    score_card.to_excel("ConversationalService/score_card.xlsx")
    score_card.loc[score_card[0].idxmin()]

    intent_detected = (score_card.loc[score_card[0].idxmin()])[1]

    return



def vectorize_query(utterence):
    vec = np.zeros(model.wv.syn0.shape[1]).reshape((1, model.wv.syn0.shape[1]))
    words = Data_Cleaner(utterence)
    count = 0
    for word in words:
        try:
            vec += model.wv[word]
            count += 1
        except KeyError:
            continue
        if count != 0:
            vec /= count

    return vec


def vectorize_query1(utterence):
    vec = np.zeros(model.wv.syn0.shape[1]).reshape((1, model.wv.syn0.shape[1]))
    words = Data_Cleaner(utterence)
    count = 0
    for word in words:
        try:
            vec += model.wv[word]*tfidf[word]
            count += 1
        except KeyError:
            continue
        if count != 0:
            vec /= count

    return vec


def get_Intent_from_Classifier(utterence):
    x=vectorize_query1(utterence)
    intent_detected=((IntentClassiferBanking.classes_)[np.argmax(IntentClassiferBanking.predict_proba(x))])
    score=str(np.max(IntentClassiferBanking.predict_proba(x)))
    return intent_detected,score


def get_Intent(utterence):
    utterence=(' '.join([sp.correction(x) for x in utterence.lower().split()]))
    print(utterence)
    query_vector = vectorize_query(utterence)
    datatable = pd.read_excel("ConversationalService/final_vector_frame.xlsx")

    datatable.loc[:, 1:]

    resultTable = pd.DataFrame(columns=['Score'])
    for i in (range(0, (datatable.__len__()))):
        vec = (np.array(datatable.loc[i, 1:]))
        score = 1-spatial.distance.cosine(query_vector, vec)
        resultTable.loc[len(resultTable)] = score

    score_card = pd.concat([resultTable, datatable], axis=1, ignore_index=True)
    #score_card.to_excel("score_card.xlsx")
    score_card.loc[score_card[0].idxmax()]

    intent_detected= (score_card.loc[score_card[0].idxmax()])[1]
    score=(score_card.loc[score_card[0].idxmax()])[0]
    return intent_detected,score

def getEntity(Sentence):
    doc = nlp(u''+Sentence)
    entity=dict()
    for ent in doc.ents:
        print(ent.text, ent.start_char, ent.end_char, ent.label_)
        entity[ent.text]=ent.label_
    return entity

def NLPcall(utterence):
    start=time.time()
    intent_detected, score=get_Intent_from_Classifier(utterence)
    end = time.time()
    print("Time elasped for intent classification:"+str(end-start))
    entity=getEntity(utterence)
    result, negation=ng.negate_sequence(utterence)
    tw=TwitterSentimentAnalyzer()
    print(utterence+" : ")
    print(" Intent :"+intent_detected)
    print(" Score :"+str(score))
    print(" Entity :"+str(entity))
    print(" Negation :"+str(negation))
    print("Sentiment:")
    sentiment,sentimentscore=(tw.getSentimentBinaryOutput(utterence))
    return intent_detected,score,entity,negation,sentiment,sentimentscore



def tsne_plot(model):
    "Creates and TSNE model and plots it"
    labels = []
    tokens = []

    for word in model.wv.vocab:
        tokens.append(model[word])
        labels.append(word)

    tsne_model = TSNE(perplexity=40, n_components=2, init='pca', n_iter=2500, random_state=23)
    new_values = tsne_model.fit_transform(tokens)

    x = []
    y = []
    for value in new_values:
        x.append(value[0])
        y.append(value[1])

    plt.figure(figsize=(16, 16))
    for i in range(len(x)):
        plt.scatter(x[i], y[i])
        plt.annotate(labels[i],
                     xy=(x[i], y[i]),
                     xytext=(5, 2),
                     textcoords='offset points',
                     ha='right',
                     va='bottom')
    plt.show()


def negate_sequence(text):
    negation = False
    delims = "?.,!:;"
    result = []
    words = text.split()
    prev = None
    pprev = None
    for word in words:
        stripped = word.strip(delims).lower()
        negated = "not_" + stripped if negation else stripped
        result.append(negated)
        if prev:
            bigram = prev + " " + negated
            result.append(bigram)
            if pprev:
                trigram = pprev + " " + bigram
                result.append(trigram)
            pprev = prev
        prev = negated
        if any(neg in word for neg in ["not", "n't", "no"]):
            negation = not negation
        if any(c in word for c in delims):
            negation = False
    print(negation)
    return result,negation