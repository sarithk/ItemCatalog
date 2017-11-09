#!/usr/bin/env python3
# Code for Item Catalog App
import random
import string
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from DatabaseSetup import Base, Category, Item, User
from flask import (Flask, render_template,
                   request, redirect, jsonify, url_for, flash)
from flask import session as login_session
# IMPORTS FOR Google sign in integration
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

# Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# User helper functions
def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserId(email):
    try:
        user = (session.query(User).filter_by(email=login_session['email']).
                one())
        return user.id
    except:
        return None


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


# Create a state token to prevent request forgery
# Store it in the session for later validation
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    print("In show login", state)
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# Google and FB login
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data.decode('utf8')
    app_id = json.loads(open('fb_client_secrets.json', 'r').
                        read())['web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = ('https://graph.facebook.com/v2.9/oauth/access_token?'
           'grant_type=fb_exchange_token&client_id=%s&client_secret=%s'
           '&fb_exchange_token=%s') % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result.decode('utf8'))
    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    ''' Due to the formatting for the result from the server token exchange we have
        to split the token first on commas and select the first index which
        gives us the key : value for the server access token then we split
        it on colons to pull out the actual token value and replace the
        remaining quotes with nothing so that it can be used directly in
        the graph api calls'''
    token = data['access_token']

    url = ('''https://graph.facebook.com/v2.8/me?access_token=%s
            &fields=name,id,email''' % token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result.decode('utf8'))
    print("FB data is from /me is", data)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = ('''https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0
             &height=200&width=200''' % token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result.decode('utf8'))
    print("FB picture data is", data)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserId(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 300px; height: 300px;border-radius: 150px;
                  -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '''

    flash("Now logged in as %s" % login_session['username'])
    return output


# Facebook disconnect
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = ('https://graph.facebook.com/%s/permissions?access_token=%s'
           % (facebook_id, access_token))
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    req = h.request(url, 'GET')[1]
    req_json = req.decode('utf8')
    result = json.loads(req_json)
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    print("stored access token", stored_access_token)
    stored_gplus_id = login_session.get('gplus_id')
    print("stored_gplus_id", stored_gplus_id)
    print("gplus_id ", gplus_id)
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected'
                                            ), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    print("In gconnect: answer json data: ", data)
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # Check if this user id exists in DB
    user_id = getUserId(login_session['email'])
    if not user_id:
        user_id = createUser(login_session=login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 300px; height: 300px;border-radius: 150px;
              -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '''
    flash("You are now logged in as %s" % login_session['username'])
    print("done!")
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print('Access Token is None')
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print('In gdisconnect access token is %s', access_token)
    print('In gdisconnect and login_session object is', login_session)
    print('User name is: ')
    print(login_session['username'])
    print('User id is: ')
    print(login_session['user_id'])
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print('result is ')
    print(result)
    print('In gdisconnect and login_session object is', login_session)
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('''Failed to revoke token for given
                                 user.''', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view catalog Information
@app.route('/catalog/JSON')
def catalogJSON():
    categories = session.query(Category).all()
    category_serialized = [c.serialize_category for c in categories]
    for c in category_serialized:
        items = session.query(Item).filter_by(cat_id=c.get("id")).all()
        items_serialized = [i.serialize for i in items]
        if items_serialized:
            c["Item"] = items_serialized
    return jsonify(Category=category_serialized)


# Show all items in catalog
# http://localhost:8000/catalog
@app.route('/')
@app.route('/catalog/')
def showCatalog():
    categories = session.query(Category).order_by(asc(Category.name))
    latestItems = (session.query(Item).order_by(desc(Item.creation_date))
                   .limit(10))
    if 'username' not in login_session:
        return render_template('publicCategories.html', categories=categories,
                               latest=latestItems)
    else:
        return render_template('categories.html', categories=categories,
                               latest=latestItems)


# Selecting a specific category shows all the items available for that category
# http://localhost:8000/catalog/Snowboarding/items
@app.route('/catalog/<string:categoryName>/items/')
def showCatalogItem(categoryName):
    categories = session.query(Category).order_by(asc(Category.name)).all()
    latestItems = (session.query(Item).order_by(desc(Item.creation_date))
                   .limit(10))
    catalog = session.query(Category).filter_by(name=categoryName).first()
    catItems = (session.query(Item).filter_by(category=catalog)
                .order_by(asc(Item.name)))
    itemCount = catItems.count()
    print("Count is", itemCount)
    if itemCount > 0:
        return (render_template('categories.html', categories=categories,
                latest=latestItems, items=catItems, length=itemCount))
    else:
        flash('No items exist in %s category'
              % (categoryName))
        return redirect(url_for('showCatalog'))


# Selecting a specific item shows specific information of that item
# http://localhost:8000/catalog/Snowboarding/Snowboard
@app.route('/catalog/<string:category>/<string:itemName>/')
def showCatalogItemDetail(category, itemName):
    category = session.query(Item).filter_by(name=category).first()
    itemForDetail = session.query(Item).filter_by(name=itemName).first()
    description = itemForDetail.description
    creator = getUserInfo(itemForDetail.user_id)
    if 'username' not in login_session or creator.id !=\
     login_session['user_id']:
        return (render_template('publicItemdetail.html', category=category,
                description=description, item=itemForDetail, creator=creator))
    else:
        return (render_template('itemdetailNew.html', category=category,
                description=description, item=itemForDetail, creator=creator))


# After logging in, user has the ability to add, update, or delete item info
# http://localhost:8000/ (logged in)
# http://localhost:8000/catalog/Snowboarding/Snowboard (logged in)
# http://localhost:8000/catalog/Snowboard/edit (logged in)
# http://localhost:8000/catalog/Snowboard/delete (logged in)
@app.route('/catalog/newCategory/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        print('No user logged in %s' % login_session)
        return redirect('/login')
    if request.method == 'POST':
        if request.form['submit']:
            category = session.query(Category).filter_by(
                name=request.form['catTitle']).first()
            user = (session.query(User).filter_by(id=login_session
                    ['user_id']).first())
            if not category:
                newCategory = (Category(name=request.form['catTitle'],
                               user=user))
                session.add(newCategory)
                session.commit()
                flash('New category %s successfully created'
                      % (newCategory.name))
                return redirect(url_for('showCatalog'))
    else:
            categories = session.query(Category).order_by(asc(Category.name))
            return render_template('addCategory.html', categories=categories)


# Create a new item
@app.route('/catalog/newItem/', methods=['GET', 'POST'])
def newCatalogItem():
    if 'username' not in login_session:
        print('No user logged in %s' % login_session)
        return redirect('/login')
    if request.method == 'POST':
        if request.form['submit']:
            category = session.query(Category).filter_by(
                name=request.form['category']).first()
            user = (session.query(User).filter_by(id=login_session
                    ['user_id']).first())
            newItem = Item(name=request.form['itemTitle'],
                           description=request.form['description'],
                           category=category, user=user)
            existingItem = (session.query(Item).filter_by(name=request.
                            form['itemTitle'], cat_id=category.id).first())
            if not existingItem:
                session.add(newItem)
                session.commit()
                flash('New item %s successfully created under category %s'
                      % (newItem.name, category.name))
                return redirect(url_for('showCatalog'))
            else:
                print("Existing item")
                flash('Item %s already exists under category %s'
                      % (existingItem.name, existingItem.category.name))
                return redirect(url_for('showCatalog'))
    else:
        categories = session.query(Category).order_by(asc(Category.name))
        return render_template('addItem.html', categories=categories)


# Edit an item
@app.route('/catalog/<string:itemName>/edit', methods=['GET', 'POST'])
def editCatalogItem(itemName):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).order_by(asc(Category.name))
    itemToEdit = session.query(Item).filter_by(name=itemName).first()
    if itemToEdit.user_id != login_session['user_id']:
        return '''<script>function myFunction(){alert('You are not authorized to edit details
               of this item.');}</script>\<body onload='myFunction()'>'''
    if request.method == 'POST':
        if request.form['submit']:
            category = (session.query(Category).filter_by(name=request.
                        form['category']).first())
            existingItem = (session.query(Item).filter_by(name=request.
                            form['itemTitle'], cat_id=category.id
                            ).first())
            if request.form['itemTitle']:
                itemToEdit.name = request.form['itemTitle']
            if request.form['description']:
                itemToEdit.description = request.form['description']
            if request.form['category']:
                changedCategory = (categories.filter_by(name=request.
                                   form['category']).first())
                itemToEdit.category = changedCategory
            if not existingItem:
                session.add(itemToEdit)
                session.commit()
                flash('Item %s Successfully Edited' % itemToEdit.name)
                return redirect(url_for('showCatalog'))
            else:
                session.rollback()
                flash('Item %s already exists under category %s' %
                      (itemToEdit.name, itemToEdit.category.name))
                return redirect(url_for('showCatalog'))
    else:
        return render_template('editItem.html', categories=categories,
                               item=itemToEdit)


# Delete an item
@app.route('/catalog/<string:itemName>/delete', methods=['GET', 'POST'])
def deleteCatalogItem(itemName):
    if 'username' not in login_session:
        return redirect('/login')
    itemToDelete = session.query(Item).filter_by(name=itemName).one()
    if itemToDelete.user_id != login_session['user_id']:
        return ('''<script>function myFunction(){alert('You are not authorized to delete this
                 item.');}</script>\<body onload = 'myFunction()'>''')
    if request.method == 'POST':
        if request.form['delete']:
            session.delete(itemToDelete)
            session.commit()
            flash('Item %s Successfully Deleted' % itemToDelete.name)
            return redirect(url_for('showCatalog'))
    else:
        return render_template('deleteItem.html', item=itemToDelete)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    print("in disconnect and login_session is", login_session, "and", session)
    if 'provider' in login_session:
        print("provider is in login session")
        if login_session['provider'] == 'google':
            print("provider is google - disconnect")
            gdisconnect()
        if login_session['provider'] == 'facebook':
            print("provider is facebook - disconnect")
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        print("provider is not in login session")
        flash("You were not logged in")
        return redirect(url_for('showCatalog'))

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
