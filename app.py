#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import sys
import dateutil.parser
import babel
from flask import Flask, jsonify, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import asc
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from forms import *
from datetime import datetime
from models import Venue, Artist, Show
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----#
# Setup relationship between models 
# - We must make creation for artist, shows, and venues via form, so use two O2M relationship between Show and Artist to increase querying performance
# - Venues -(n)-> Show -(n)-> Artist 
#----#

## Use M2M relationship between Venues and Artist and use Shows as join table

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
            format="EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
            format="EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    # Use two loop to get all the case available
    try:
        # Return a tuple
        cities_list = Venue.query.with_entities(Venue.city).distinct().all()
        states_list = Venue.query.with_entities(Venue.state).distinct().all()

        print(len(cities_list))
        print(len(states_list))

        # Retrieving all values as a flat list
        cities = [value for (value,) in cities_list]
        states = [value for (value,) in states_list]

        # Buffer to get all values 
        for city in cities:
            # make empty venues_data
            for state in states:
                venuesList = Venue.query.filter_by(city = city, state = state).order_by(Venue.id).all()
                print(f'city: {city}, state: {state}, count: {len(venuesList)}')
                if (len(venuesList) > 0):
                    # Prepare data for venues
                    venues_data = []
                    for venue_item in venuesList:
                        upcomming_show = Show.query.join(Venue).filter(Venue.name == venue_item.name, Show.start_time > datetime.now()).count()
                        venues_data.append({
                            "id": venue_item.id,
                            "name": venue_item.name,
                            "num_upcoming_shows": upcomming_show
                        })
                    data.append({
                        "city": city,
                        "state": state,
                        "venues": venues_data
                    })
        print(f'Data get: {data}')
        return render_template('pages/venues.html', areas=data)
    except:
        flash('An error occurred. Cannot display venues')
        return redirect(url_for('index'))


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_item = request.form.get('search_term')
    search_item_pattern = f'%{search_item}%'
    print(f'Get value from search:{search_item}')
    # Find item
    data = []
    try:
        search_result_list = Venue.query.filter(Venue.name.ilike(search_item_pattern)).all()
        print(f'Get given list: {search_result_list}')

        # Make list result
        for venue_item in search_result_list:
            upcomming_show = Show.query.join(Venue).filter(Venue.name == venue_item.name, Show.start_time > datetime.now()).count()
            data.append({
                "id": venue_item.id,
                "name": venue_item.name,
                "num_upcoming_shows": upcomming_show
            })
            
        # Generate the response 
        response = {
            "count": len(data),
            "data": data
        }

        return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))
    except:
        flash('An error occured while searching')
        return redirect(url_for('venues'))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    try:
        venue_lists_data = []
        venues = Venue.query.all()
        for venue in venues:
            # Prepare data for each venue
            venue_data = {}
            # Find all show that have this venue
            upcoming_shows = []
            past_shows = []
            shows_list = Show.query.join(Venue).filter(Venue.name == venue.name).all()
            for show in shows_list:
                show_start_time = show.start_time
                show_data = {
                    "artist_id": show.artist_id,
                    "artist_name": show.artist.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": show_start_time.strftime("%Y-%m-%dT%H:%M:%SZ")       
                }
                if (show_start_time > datetime.now()):
                    upcoming_shows.append(show_data)
                else:
                    past_shows.append(show_data)
            # Prepare the response message
            venue_data["id"] = venue.id
            venue_data["name"] = venue.name
            venue_data["genres"] = venue.genres.strip("{}").split(",")
            venue_data["address"] = venue.address
            venue_data["city"] = venue.city
            venue_data["state"] = venue.state 
            venue_data["phone"] = venue.phone
            venue_data["website"] = venue.website
            venue_data["facebook_link"] = venue.facebook_link
            venue_data["seeking_talent"] = venue.seeking_talent
            venue_data["image_link"] = venue.image_link
            venue_data["past_shows"] = past_shows
            venue_data["upcomming_shows"] = upcoming_shows
            venue_data["past_shows_count"] = len(past_shows)
            venue_data["upcoming_shows_count"] = len(upcoming_shows)
            if (venue.seeking_talent == True):
                venue_data["seeking_description"] = venue.seeking_description
            venue_lists_data.append(venue_data)
        # print(venue_lists_data)
        data = list(filter(lambda d: d['id'] == venue_id, venue_lists_data))[0]
        return render_template('pages/show_venue.html', venue=data)
    except:
        flash('An error occurred. Cannot show the venues')
        return redirect(url_for('index'))   


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    try:
        # get form data 
        form = VenueForm()
        if form.validate():
            new_name = form.name.data
            new_name_count = Venue.query.filter_by(name = new_name).count()
            print(f'[DBG] count: {new_name_count}')
            # Check for existed record
            if (new_name_count == 0):
                venue = Venue(
                    name=form.name.data,
                    city=form.city.data,
                    state=form.state.data,
                    address=form.address.data,
                    phone=form.phone.data,
                    genres=form.genres.data,
                    facebook_link=form.facebook_link.data,
                    image_link=form.image_link.data,
                    website=form.website_link.data,
                    seeking_talent=form.seeking_talent.data,
                    # If we don't tick into seeking_talent, the web won't record the seeking_description 
                    seeking_description= form.seeking_description.data if (form.seeking_talent.data) else None
                )
                # commit session to database
                db.session.add(venue)
                db.session.commit()
                # flash success
                flash('Venue ' + request.form['name'] + ' was successfully listed!')
            else: 
                flash('Venue ' + request.form['name'] + ' was existed')
        else:
            errorMessage = "Errors in the following fields: "
            for error in form.errors:
                errorMessage += error + " "
            flash(errorMessage)
    except:
        # catches errors
        db.session.rollback()
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    finally:
        # closes session
        db.session.close()
    return render_template('pages/home.html')


@app.route('/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try: 
        Venue.query.filter_by(id = venue_id).delete()
        db.session.commit()
        flash('Detele venue successfully')
        db.session.close()
        return jsonify({'success': True}), 200
    except:
        db.session.rollback()
        db.session.close()
        flash('Error(s) occurred when detele venue')
        return jsonify({'success': False}), 404   

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = []
    try:
        artist_list = Artist.query.with_entities(Artist.id, Artist.name).order_by(asc(Artist.id)).all()
        # It returns a list so that we needn't flat that
        for artist in artist_list:
            data.append({
                "id": artist.id,
                "name": artist.name
            })
    except:
        flash('An error occurred. Cannot display artists')
        return redirect(url_for('index'))
    return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_item = request.form.get('search_term')
    search_item_pattern = f'%{search_item}%'
    print(f'Get value from search:{search_item}')
    data = []
    try:
        search_result_list = Artist.query.filter(Artist.name.ilike(search_item_pattern)).all()
        print(f'Get given artist: {search_result_list}')

        # Make result
        for artist in search_result_list:
            upcomming_show = Show.query.join(Artist).filter(Artist.name == artist.name, Show.start_time > datetime.now()).count()
            data.append({
                "id": artist.id,
                "name": artist.name,
                "num_upcoming_shows": upcomming_show
            })
        
        # Generate the response
        response = {
            "count": len(data),
            "data": data
        }

        return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))
    except:
        flash('An error occured while searching')
        return redirect(url_for('venues'))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    try:
        artist_lists_data = []
        artists = Artist.query.all()
        for artist in artists:
            # Prepare data for each artist
            artist_data = {}
            upcoming_shows = []
            past_shows = []
            shows_list = Show.query.join(Artist).filter(Artist.name == artist.name).all()
            for show in shows_list:
                show_start_time = show.start_time
                show_data = {
                    "artist_id": show.artist_id,
                    "artist_name": show.artist.name,
                    "artist_image_link": show.artist.image_link,
                    "start_time": show_start_time.strftime("%Y-%m-%dT%H:%M:%SZ")       
                }
                if (show_start_time > datetime.now()):
                    upcoming_shows.append(show_data)
                else:
                    past_shows.append(show_data)
            # Prepare the response message
            artist_data["id"] = artist.id
            artist_data["name"] = artist.name
            artist_data["genres"] = artist.genres.strip("{}").split(",")
            artist_data["city"] = artist.city
            artist_data["state"] = artist.state
            artist_data["phone"] = artist.phone
            artist_data["website"] = artist.website
            artist_data["facebook_link"] = artist.facebook_link
            artist_data["seeking_venue"] = artist.seeking_venue
            artist_data["image_link"] = artist.image_link
            artist_data["past_shows"] = past_shows
            artist_data["upcomming_shows"] = upcoming_shows
            artist_data["past_shows_count"] = len(past_shows)
            artist_data["upcoming_shows_count"] = len(upcoming_shows)
            if (artist.seeking_venue == True):
                artist_data["seeking_description"] = artist.seeking_description
            artist_lists_data.append(artist_data)
        print(artist_lists_data)
        data = list(filter(lambda d: d['id'] == artist_id, artist_lists_data))[0]
        return render_template('pages/show_artist.html', artist=data)
    except: 
        flash('An error occurred. Cannot show the artist')
        return redirect(url_for('index'))   


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    try: 
        form = ArtistForm()
        # Get the artist entity
        artist_ent = Artist.query.filter_by(id = artist_id).first()
        # Check for valid entity
        if (artist_ent is not None):
            artist = {}
            artist["id"] = artist_ent.id
            artist["name"] = artist_ent.name
            artist["genres"] = artist_ent.genres.strip("{}").split(",")
            artist["city"] = artist_ent.city
            artist["state"] = artist_ent.state
            artist["phone"] = artist_ent.phone
            artist["website"] = artist_ent.website
            artist["facebook_link"] = artist_ent.facebook_link
            artist["seeking_venue"] = artist_ent.seeking_venue
            artist["image_link"] = artist_ent.image_link
            if (artist_ent.seeking_venue == True): 
                artist["seeking_description"] = artist_ent.seeking_description
            return render_template('forms/edit_artist.html', form=form, artist=artist)
        else:
            flash(f'The artist id {artist_id} is invalid')
            return redirect(url_for('index'))
    except:
        flash('An error occurred. Cannot get the artist')
        return redirect(url_for('index'))  

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    try:
        artist_to_update = Artist.query.filter_by(id = artist_id).first()
        if (artist_to_update is not None):
            old_name = artist_to_update.name
            form = ArtistForm()
            if form.validate():
                artist_to_update.name=form.name.data
                artist_to_update.city=form.city.data
                artist_to_update.state=form.state.data
                artist_to_update.phone=form.phone.data
                artist_to_update.genres=form.genres.data
                artist_to_update.facebook_link=form.facebook_link.data
                artist_to_update.image_link=form.image_link.data
                artist_to_update.website=form.website_link.data
                artist_to_update.seeking_venue=form.seeking_venue.data
                # If we don't tick into seeking_talent, the web won't record the seeking_description 
                artist_to_update.seeking_description= form.seeking_venue.data if (form.seeking_venue.data) else None
                # Commit the change
                db.session.commit() 
                flash(f'Update artist {old_name} Success!')
            else: 
                errorMessage = "Errors in the following fields: "
                for error in form.errors:
                    errorMessage += error + " "
                flash(errorMessage)
        else:
        # Return the homepage
            flash('The artist id is invalid')
            return redirect(url_for('index'))
    except:
        # catches errors
        db.session.rollback()
        flash(f'An error occurred. Artist {old_name} could not be updated.')
    finally:
        # closes session
        db.session.close()
    return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    try:
        form = VenueForm()
        # Get the venue entity
        venue_ent = Venue.query.filter_by(id = venue_id).first()
        # Check for valid entity
        if (venue_ent is not None): 
            venue = {}
            venue["id"] = venue_ent.id
            venue["name"] = venue_ent.name
            venue["genres"] = venue_ent.genres.strip("{}").split(",")
            venue["address"] = venue_ent.address
            venue["city"] = venue_ent.city
            venue["state"] = venue_ent.state
            venue["phone"] = venue_ent.phone
            venue["website"] = venue_ent.website
            venue["facebook_link"] = venue_ent.facebook_link
            venue["seeking_talent"] = venue_ent.seeking_talent
            venue["image_link"] = venue_ent.image_link
            if (venue_ent.seeking_talent == True): 
                venue["seeking_description"] = venue_ent.seeking_description
            return render_template('forms/edit_venue.html', form=form, venue=venue)
        else:
            flash(f'The venues id {venue_id} is invalid')
            return redirect(url_for('index'))
    except:
        flash('An error occurred. Cannot get the venue')
        return redirect(url_for('index'))  

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    try:
        # Check for valid id
        venue_to_update = Venue.query.filter_by(id = venue_id).first()
        if (venue_to_update is not None):
            old_name = venue_to_update.name
            form = VenueForm()
            if form.validate():
                venue_to_update.name=form.name.data
                venue_to_update.city=form.city.data
                venue_to_update.state=form.state.data
                venue_to_update.address=form.address.data
                venue_to_update.phone=form.phone.data
                venue_to_update.genres=form.genres.data
                venue_to_update.facebook_link=form.facebook_link.data
                venue_to_update.image_link=form.image_link.data
                venue_to_update.website=form.website_link.data
                venue_to_update.seeking_talent=form.seeking_talent.data
                # If we don't tick into seeking_talent, the web won't record the seeking_description 
                venue_to_update.seeking_description= form.seeking_description.data if (form.seeking_talent.data) else None
                # Commit the change
                db.session.commit() 
                flash(f'Update venue {old_name} Success!')
            else: 
                errorMessage = "Errors in the following fields: "
                for error in form.errors:
                    errorMessage += error + " "
                flash(errorMessage)
        else:
            # Return the homepage
            flash('The venue id is invalid')
            return redirect(url_for('index'))
    except:
        # catches errors
        db.session.rollback()
        flash(f'An error occurred. Venue {old_name} could not be updated.')
    finally:
        # closes session
        db.session.close()
    # venue record with ID <venue_id> using the new attributes
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    try:
        # Get form data 
        form = ArtistForm()
        if form.validate():
            new_name = form.name.data
            new_name_count = Artist.query.filter_by(name = new_name).count()
            print(f'Found {new_name_count} artist existed')
            if (new_name_count == 0):
                artist = Artist(
                    name = new_name,
                    city = form.city.data,
                    state = form.state.data,
                    phone = form.phone.data,
                    genres = form.genres.data,
                    facebook_link = form.facebook_link.data,
                    image_link = form.image_link.data,
                    website = form.website_link.data,
                    seeking_venue = form.seeking_venue.data,
                    seeking_description = form.seeking_description.data if (form.seeking_venue.data) else None
                )
                # commit session to database
                db.session.add(artist)
                db.session.commit()
                # on successful db insert, flash success
                flash('Artist ' + request.form['name'] + ' was successfully listed!')
            else:
                flash ('Artist ' + request.form['name'] + ' was existed')
        else:
            errorMessage = "Errors in the following fields: "
            for error in form.errors:
                errorMessage += error + " "
            flash(errorMessage)
    except:
        # Catches errors
        db.session.rollback()
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    finally:
        # closes session
        db.session.close()
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    data = []
    try:
        shows_list = Show.query.all()
        print(shows_list)
        for show in shows_list:
            data.append({
                "venue_id": show.venue_id,
                "venue_name": show.venue.name,
                "artist_id": show.artist_id,
                "artist_name": show.artist.name,
                "artist_image_link": show.artist.image_link,
                "start_time": show.start_time.strftime("%Y-%m-%dT%H:%M:%SZ")       
            })
        return render_template('pages/shows.html', shows=data)
    except:
        flash('An error occurred. Cannot display shows')
        return redirect(url_for('index'))

@app.route('/shows/create', methods=['GET'])
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    # TODO: insert form data as a new Show record in the db, instead
    try:
        form = ShowForm()
        if (form.validate()):
            show = Show(
                artist_id = form.artist_id.data,
                venue_id = form.venue_id.data
            )
            # commit session to database
            db.session.add(show)
            db.session.commit()
            flash('Show was successfully listed!')
        else:
            errorMessage = "Errors in the following fields: "
            for error in form.errors:
                errorMessage += error + " "
            flash(errorMessage)
    except:
        # catches errors
        db.session.rollback()
        flash('An error occurred. Show could not be listed.')
    finally:
        # closes session
        db.session.close()
    return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
        return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
        return render_template('errors/500.html'), 500


if not app.debug:
        file_handler = FileHandler('error.log')
        file_handler.setFormatter(
                Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
        )
        app.logger.setLevel(logging.INFO)
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run(debug = True)

# Or specify port manually:
'''
if __name__ == '__main__':
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port)
'''
