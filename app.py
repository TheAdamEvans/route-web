# -*- coding: utf-8 -*-

import os
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, send_from_directory

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'climbon.db'),
    DEBUG=False,
    SECRET_KEY='cookie'
))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/show')
def show_entries():
    db = get_db()
    head_query = "select * from climb where origin_href = '"+session['href']+"' and href = '"+session['href']+"'order by best desc"
    cur = db.execute(head_query)
    headz = cur.fetchall()

    recco_query = "select * from climb where origin_href = '"+session['href']+"' and href != '"+session['href']+"'order by best desc"
    cur = db.execute(recco_query)
    entries = cur.fetchall()

    return render_template('show_entries.html', entries=entries, headz=headz)


@app.route('/', methods=['GET', 'POST'])
def search():
    error = None
    if request.method == 'POST':
        if True:
            session['href'] = request.form['href']
            flash('looking for ' + session['href'])
            return redirect(url_for('show_entries'))
    return render_template('search.html', error=error)

@app.route('/r/<href>')
def direct_link_to_route(href=None):
    db = get_db()
    head_query = "\
    select * from climb \
    where origin_href = '"+href+"' \
    and href = '"+href+"'\
    order by best desc\
    "
    cur = db.execute(head_query)
    headz = cur.fetchall()

    recco_query = "select * from climb where origin_href = '"+href+"' and href != '"+href+"'order by best desc"
    cur = db.execute(recco_query)
    entries = cur.fetchall()

    return render_template('show_entries.html', entries=entries, headz=headz)


if __name__ == '__main__':
    app.run()