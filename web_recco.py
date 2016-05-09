import re
import os
import itertools
import pickle
import numpy as np
import pandas as pd
from collections import Counter
from scipy.sparse import csr_matrix
from scipy.linalg import norm

hueco = re.compile(r'V([(easy)\d\+\-]*)')
yds = re.compile(r'5\.([\d]+[\+\-abcd]*)')
state_pattern = re.compile(r'(?:A[KLRZ]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY])')


def grade_scorer(grade, ideal):
    return 1 - abs(ideal - grade)


def sanitize(dirty_query, vocab):
    """ Preprocess query string """
    query = dirty_query.strip().lower()
    unigrams = query.split(' ')
    bigrams = [ b[0]+' '+b[1] for l in [query] for b in zip(l.split(' ')[:-1], l.split(' ')[1:]) ]
    tokens = [ t for t in (unigrams + bigrams) if t in vocab ]
    return tokens


def convert_grade_query(dirty_query, grade_map, grade_patterns):
    """ Turn grades like 5.11+ and V4-5 to float values [0,1] """
    gds = []
    for pattern in grade_patterns:
        if pattern.search(dirty_query):
            grade_string = pattern.search(dirty_query).group(0)
            if grade_string in grade_map.keys():
                gds.append(grade_map[grade_string])
    if len(gds) > 0:
        # average if more than one grade is provided
        ideal = np.array(gds).mean()
        return ideal
    else:
        return None


def measure_similarity(m, n):
    """ vectors are L2 normalized
    the dot product between them is related to the angle between any two vectors
    this can be interpreted as the similarity of language
    source: http://karpathy.github.io/2014/07/02/visualizing-top-tweeps-with-t-sne-in-Javascript/
    """
    similarity = (m[0] * n[0].T)[0,0]
    return similarity


def sparse_query_builder(tokens, vocab, idf_lookup):

    counts = dict(Counter(tokens))
    
    text_vector = np.zeros((1, len(vocab)))
    for word, Tf in counts.items():
        # multiply term frequency by inverse document frequency
        tfidf_score = float(Tf) * idf_lookup[word]
        # add score to this word's position in the array
        text_vector[0,vocab.index(word)] = tfidf_score
    # L2 normalize
    text_vector = text_vector / norm(text_vector, 2)
    # cast as sparse
    sparse_query = csr_matrix(text_vector)
    
    return sparse_query


def detect_geography(tokens, state_pattern):
    """ returns list of state abbreviations from dirty_query """
    states = []
    for tk in tokens:
        if state_pattern.search(tk):
            states.append(tk)
    return states


def filter_geography(climb, state_index, states):
    """ return boolean column of climbs in those states """
    include = ~climb.any(1)
    for state in states:
        include = include | state_index[state]
    return include


def give_recco(dirty_query, vocab, climb, idf_lookup, state_index, grade_map, top=20):

    raw_tokens = dirty_query.strip().split(' ')
    tokens = sanitize(dirty_query, vocab)
    print tokens
    states = detect_geography(raw_tokens, state_pattern)
    print states
    ideal = convert_grade_query(dirty_query, grade_map, grade_patterns = [hueco, yds])
    print ideal
    print

    # subset to any states specified
    if len(states) > 0:
        climb = climb[filter_geography(climb, state_index, states)].copy()
    
    # score and filter by grade
    if ideal is None:
        climb.loc[:,'grade_score'] = [1.0] * len(climb.index)
    else:
        scaled = climb['grade']
        climb.loc[:,'grade_score'] = map(grade_scorer, scaled, itertools.repeat(ideal, len(scaled)))
        climb = climb[climb['grade_score'] > 0.5].copy()
    
    # score and filter by text similarity
    if len(tokens) == 0:
        climb.loc[:,'text_score'] = [1.0] * len(climb.index)
    else:
        # score and filter by text
        sparse_query = sparse_query_builder(tokens, vocab, idf_lookup)
        climb.loc[:,'text_score'] = map(lambda sps: measure_similarity(sparse_query, sps), climb['combined_sparse_tfidf'])
        climb = climb[climb['text_score'] > 0.0].copy()

    # recommendation
    score_components = [
        'scaledStaraverage','scaledStarvotes','grade_score','text_score'
    ]
    recco = climb[score_components].copy()

    # magic weights because obviously
    recco['text_score'] = recco['text_score'] * 25
    recco['grade_score'] = recco['grade_score'] * 12
    recco['scaledStaraverage'] = recco['scaledStaraverage'] * 10
    recco['scaledStarvotes'] = recco['scaledStarvotes'] * 5

    # total score and sort
    recco['best'] = recco.sum(1)
    recco = recco.sort_values('best', ascending=False)

    top = min(top, len(recco.index))
    return climb.loc[recco.index[:top]]