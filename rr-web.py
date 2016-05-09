# -*- coding: utf-8 -*-

import pickle
import re
import os
import numpy as np
import pandas as pd
from flask import Flask, request, session, g, redirect, render_template, url_for

from web_recco import give_recco

app = Flask(__name__)
app.config.update(dict(
    DLOC=os.path.join(app.root_path,'data/'),
    DEBUG=False,
    SECRET_KEY='cookie'
))

# load objects into memory
vocab = pd.read_csv(app.config['DLOC']+'vocab.txt', header=None)[0].tolist()
climb = pickle.load(open(app.config['DLOC']+'climb', 'rb'))
idf_lookup = pickle.load(open(app.config['DLOC']+'idf', 'rb'))
state_index = pickle.load(open(app.config['DLOC']+'state_index', 'rb'))
grade_map = pickle.load(open(app.config['DLOC']+'grade_map', 'rb'))

# @app.route('/i/<loc>')
# def lookup(loc):
#     row=climb.loc[loc]
#     return render_template('query.html', row=row)

@app.route('/', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        dirty_query = request.form['query']
        recco = give_recco(dirty_query, vocab, climb, idf_lookup, state_index, grade_map)
        # replace float('NaN') with None
        recco = recco.where((pd.notnull(recco)), None)
        return render_template('query.html', recco=recco)
    else:
        return render_template('search.html')

if __name__ == '__main__':
    app.run()