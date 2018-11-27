#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "jz3011"
DB_PASSWORD = "27abo199"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")



@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#

# Home page
@app.route('/')
def index():

  return render_template("index.html")

# search for battle history

@app.route('/search')
def search():

  cursor = g.conn.execute("SELECT login FROM user_profile")
  names = []
  for result in cursor:
    names.append(result['login'])  # can also be accessed using result[0]
  cursor.close()
  context = dict(data = names)

  return render_template("search.html",**context)

@app.route('/history',methods=['GET', 'POST'])
def history():
  cursor1 = g.conn.execute("SELECT login FROM user_profile")
  names = []
  for result in cursor1:
    names.append(result['login'])  # can also be accessed using result[0]
  cursor1.close()
  if request.method == 'POST':
    username = request.form.get('username')
    cursor2 = g.conn.execute("SELECT user_login, user_score, enemy_login, enemy_score, winner,battle_id FROM battle_history WHERE user_login='{}'".format(username))
    data = []

    for result in cursor2:
      data.append({"user_score":result['user_score'],
                   "user_login":result['user_login'],
                   "enemy_login":result['enemy_login'],
                   "enemy_score":result['enemy_score'],
                   "winner":result['winner'],
                   "battle_id":result['battle_id']})
    cursor2.close()
    return render_template("history.html",data = data) 
  context = dict(data = names)
  return render_template("search.html",**context)

# popular repos ordering by star

@app.route('/popular')
def popular():
  cursor = g.conn.execute("""WITH temp as (SELECT * FROM user_own_repo LEFT JOIN user_profile ON (user_own_repo.user_id=user_profile.id))
                          select rank,m.repo_id,name,login,avatar_url,language,num_folk,num_star, CASE WHEN issues IS NULL THEN 0 ELSE issues END,  CASE WHEN pull_requests IS NULL THEN 0 ELSE pull_requests END
                          from
                          (SELECT ROW_NUMBER() OVER (order by num_star DESC) as rank, repo.id as repo_id, login, avatar_url, repo.name as name, language, num_folk, num_star  
                          FROM repo 
                          LEFT JOIN temp ON repo.id=temp.repo_id
                          order by num_star DESC) as m
                          LEFT JOIN (select temp1.repo_id as repo_id, issues, pull_requests from (select repo_id, count (*) as pull_requests from pull_request group by repo_id) as b left join (select * from repo left join (select repo_id, count (*) as issues from  issue group by repo_id) as a on repo.id=a.repo_id) as temp1 on b.repo_id=temp1.repo_id) as k
                          ON m.repo_id=k.repo_id""")
  rank = []
  for result in cursor:
    rank.append({"rank":result['rank'],
                 "repo_id":result['repo_id'],
                 "repo_name":result['name'],
                 "user":result['login'],
                 "avatar_url":result['avatar_url'],
                 "language": result['language'],
                 "folk": result['num_folk'],
                 "star":result['num_star'],
                 "issues":result['issues'],
                 "pull_requests":result['pull_requests']})
  cursor.close()
  return render_template("popular.html",rank=rank)

@app.route('/results')
def playerPreview():
  return render_template("results.html")

# Battle

@app.route('/battle')
def battle():
  cursor = g.conn.execute("SELECT login FROM user_profile")
  names = []
  for result in cursor:
    names.append(result['login'])  # can also be accessed using result[0]
  cursor.close()

  context = dict(data = names)

  return render_template("battle.html", **context)

# Get One player's information
@app.route('/getPlayers', methods=['GET', 'POST']) #allow both GET and POST requests
def getPlayers():
    if request.method == 'POST':  #this block is only entered when the form is submitted
        playerOne = request.form.get('playerOne')
        playerTwo = request.form.get('playerTwo')

        cursor1 = g.conn.execute("SELECT following, followers, num_pub_repos , avatar_url FROM user_profile where login = '{}'".format(playerOne))
        cursor2 = g.conn.execute("SELECT following, followers, num_pub_repos , avatar_url FROM user_profile where login = '{}'".format(playerTwo))
        for result in cursor1:
          playerOneFollowing= result['following']
          playerOneFollowers= result['followers']
          playerOneRepos= result['num_pub_repos']
          playerOneAvatar= result['avatar_url']
        for result in cursor2:
          playerTwoFollowing= result['following']
          playerTwoFollowers= result['followers']
          playerTwoRepos= result['num_pub_repos']
          playerTwoAvatar= result['avatar_url']
        cursor1.close()
        cursor2.close()

        playerOneScore= playerOneFollowing + 10*playerOneFollowers + 30*playerOneRepos
        playerTwoScore= playerTwoFollowing + 10*playerTwoFollowers + 30*playerTwoRepos

        if playerOneScore >playerTwoScore:
          gameResult = 'Winner is ' + playerOne
          winner = playerOne
        elif playerOneScore < playerTwoScore:
          gameResult = 'Winner is ' + playerTwo
          winner = playerTwo
        else:
          gameResult = 'Tie'
          winner = 'Tie'

        cursor3 = g.conn.execute("SELECT COUNT(*) as total_num FROM battle_history ");
        for result in cursor3:
          battle_id = int(result['total_num'])
        cursor3.close()
        g.conn.execute("INSERT INTO battle_history VALUES ({},{},'{}','{}','{}',{})".format(playerOneScore,playerTwoScore,playerOne,playerTwo,winner,battle_id+1));

        data = {"playerOne":playerOne, "playerTwo":playerTwo,
                "playerOneAvatar":playerOneAvatar, "playerTwoAvatar": playerTwoAvatar, 
                "playerOneFollowing":playerOneFollowing, "playerTwoFollowing":playerTwoFollowing,
                "playerOneFollowers":playerOneFollowers, "playerTwoFollowers":playerTwoFollowers,
                "playerOneRepos":playerOneRepos,"playerTwoRepos":playerTwoRepos,
                "result":gameResult, "total":battle_id}
        return render_template("results.html", data = data  )

    return render_template("battle.html", **context)

# Add a new User
@app.route('/add', methods=['POST'])
def add():
  login = request.form['login']
  name = request.form['name']
  repos = request.form['repos']
  followers = request.form['followers']
  followings = request.form['followings']
  avatar_url = request.form['avatar_url']
  cursor1 = g.conn.execute("SELECT max(id) as max_id FROM user_profile ");
  for result in cursor1:
    user_id = int(result['max_id'])
  cursor1.close()
  g.conn.execute("INSERT INTO user_profile VALUES ({},'{}','{}',{},{},{},'{}')".format(user_id+1,login,name,repos,followers,followings, avatar_url));
  return redirect('/battle')

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
