from django.shortcuts import render, redirect
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import login as auth_login
from django.contrib.auth import authenticate
from django.contrib import messages
from django.views import generic
from django.views.generic import DetailView, CreateView
import tekore as tk
import ipinfo
import environ
from datetime import datetime
from random import randint
from django.http import HttpResponse
import folium
import geocoder
from django.urls import reverse_lazy
from .apis.Spotify import Spotify
from .apis.Weather import fetchWeather
from .forms import CreateUserForm, EditProfileForm
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from base.models import Profile
env = environ.Env()
environ.Env.read_env()

conf = (env("SOCIAL_AUTH_SPOTIFY_KEY"), env(
    "SOCIAL_AUTH_SPOTIFY_SECRET"), env("REDIRECT"))
cred = tk.Credentials(*conf)
spotify = tk.Spotify()

auths = {}  # Ongoing authorisations: state -> UserAuth
users = {}  # User tokens: state -> token (use state as a user ID)

def callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')
    auth = auths.pop(state, None)

    if auth is None:
        return 'Invalid state!', 400

    token = auth.request_token(code, state)
    # # session['user'] = state
    users[state] = token

    response = redirect('/home')
    response.set_cookie('user_session', token)

    return response

def login(request):
    try:
        request.COOKIES['user_session']
        return redirect('/home', 307)
    except KeyError:
        scope = tk.scope.every
        auth = tk.UserAuth(cred, scope)
        auths[auth.state] = auth
        return redirect(auth.url, 307)


def logout(request):
    token = request.COOKIES['user_session']
    if token is not None:
        users.pop(token, None)

    response = redirect('/home')
    response.delete_cookie('user_session')
    return response

#@login_required(login_url='/userLogin')
def home(request):
	return render(request, "base/home.html")
"""
    # If user signed in
    try:
        token = request.COOKIES['user_session']

        city = None

        # User searched weather for a different city
        if request.method == 'POST':
            city = request.POST['city']

        # Current city
        else:
            # Grab IP address from request
            if env("STAGE") == 'DEV':
                ipAddress = '216.239.36.21' # Mountain View, CA
            else:
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ipAddress = x_forwarded_for.split(',')[0]
                else:
                    ipAddress = request.META.get('REMOTE_ADDR')

            # Fetch geolocation using IP
            handler = ipinfo.getHandler(env("IP_INFO_ACCESS_TOKEN"))
            details = handler.getDetails(ipAddress)
            city = details.city

        # Fetch weather for city
        weather = fetchWeather(city)

        # Fetch Spotify playlist using weather
        playlistIndex = 0
        with spotify.token_as(token):
            playlist = spotify.search(
                weather['weather'][0]['description'], ('playlist',))
            playlistIndex = randint(0, playlist[0].limit-1)
            spotify.playback_start_context(
                playlist[0].items[playlistIndex].uri)

        # Create data payload
        current_time = datetime.now()
        formatted_time = current_time.strftime("%A, %B %d %Y, %H:%M:%S %p")

        data = {
            "user": token,
            "city": str(city),
            "weather": {
                'city': city,
                'description': weather['weather'][0]['description'],
                'icon': weather['weather'][0]['icon'],
                'temperature': str(weather['main']['temp'])[:2] + ' °F',
                'country_code': weather['sys']['country'],
                'wind': 'Wind: ' + str(weather['wind']['speed']) + ' m/h',
                'humidity': 'Humidity: ' + str(weather['main']['humidity']) + '%',
                'time': formatted_time
            },
            "playlist": playlist[0].items[playlistIndex],
            "error": None
        }

        return render(request, "base/home.html", data)

    # If user not signed in
    except Exception as e:
        print(e)
        return render(request, "base/home.html", {
            "user": None,
            "error": e
        })
"""    
@login_required(login_url='/userLogin')
def profile(request):


    username = None
    if(request.user.is_authenticated):
    	username = request.user.username
    if env("STAGE") == 'DEV':
        ipAddress = '216.239.36.21' # Mountain View, CA
    else:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ipAddress = x_forwarded_for.split(',')[0]
        else:
            ipAddress = request.META.get('REMOTE_ADDR')
    location = geocoder.ipinfo(ipAddress)
    address = location.city + ", " + location.state + ", " + location.country
    context = {
    		'username' : username,
    		'address' : address
    		}
    
    return render(request, "base/profile.html",context)

@login_required(login_url='/userLogin')
def playlists(request):
	# If user signed in
	try:
		token = request.COOKIES['user_session']

		# Fetch Spotify playlist using weather
		with spotify.token_as(token):
			current_playlist_id = spotify.playback().context.uri
			current_playlist = spotify.playlist(current_playlist_id[current_playlist_id.rfind(":")+1:])
			playlists = spotify.playlists(spotify.current_user().id)
		
		data = {
			"user": token,
			"playlists": [(p.id, p.name) for p in playlists.items],
			"current_playlist_name": current_playlist.name, 
			"current_playlist_id": current_playlist.id,
			"tracks": [(t.track.id, t.track.name) for t in current_playlist.tracks.items]
		}

		return render(request, "base/playlists.html", data)

	# If user not signed in
	except Exception as ex:
		print(ex)
		return render(request, "base/playlists.html", {
			"user": None,
			"tracks": None
		})
		
def skipForward(request):
	print('skipForward')
	try:
		token = request.COOKIES['user_session']

		with spotify.token_as(token):
			spotify.playback_next()
		
		return HttpResponse(status=204)
	except Exception as e:
		print(e)
		return render(request, "base/home.html", {
			"user": None,
			"error": e
		})

def playSong(request):
	try:
		token = request.COOKIES['user_session']
		with spotify.token_as(token):
			spotify.playback_start_context(f"spotify:playlist:{request.GET['playlistID']}", request.GET['trackID'])
		return HttpResponse(status=204)
	except Exception as e:
		print(e)
		return render(request, "home.html", {
			"user": None,
			"error": e
		})

def togglePlayPause(request):
	print('togglePlayPause')
	try:
		token = request.COOKIES['user_session']

		with spotify.token_as(token):
			if (spotify.playback_currently_playing().is_playing):
				spotify.playback_pause()
			else:
				spotify.playback_resume()
		
		return HttpResponse(status=204)
	except Exception as e:
		print(e)
		return render(request, "base/home.html", {
			"user": None,
			"error": e
		})

def toggleFavorite(request):
	print('toggleFavorite')
	try:
		token = request.COOKIES['user_session']

		with spotify.token_as(token):
			song_id = spotify.playback_currently_playing().item.id
			if song_id in [t.track.id for t in spotify.saved_tracks(limit=50).items]:
				spotify.saved_tracks_delete([song_id])
			else:
				spotify.saved_tracks_add([song_id])
		
		return HttpResponse(status=204)
	except Exception as e:
		print(e)
		return render(request, "base/home.html", {
			"user": None,
			"error": e
		})

def togglePlaylist(request):
	print('togglePlaylist')
	try:
		token = request.COOKIES['user_session']

		with spotify.token_as(token):
			spotify.playback_previous()
		
		return HttpResponse(status=204)
	except Exception as e:
		print(e)
		return render(request, "base/home.html", {
			"user": None,
			"error": e
		})

def skipBackward(request):
	print('skipBackward')
	try:
		token = request.COOKIES['user_session']

		with spotify.token_as(token):
			spotify.playback_previous()
		
		return HttpResponse(status=204)
	except Exception as e:
		print(e)
		return render(request, "base/home.html", {
			"user": None,
			"error": e
		})
@login_required(login_url='/userLogin')
def location(request):
    # geolocation
    if env("STAGE") == 'DEV':
        ipAddress = '216.239.36.21' # Mountain View, CA
    else:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ipAddress = x_forwarded_for.split(',')[0]
        else:
            ipAddress = request.META.get('REMOTE_ADDR')
    
    location = geocoder.ip(ipAddress)
    coords = location.latlng
    country = location.country
    city = location.city
    state = location.state

    # map object
    m = folium.Map(width=1500, height=750, location=[19, -12], zoom_start=3)
    folium.Marker(coords, tooltip='More Information',
                  popup=(country + ", " + city + ", " + state)).add_to(m)
    # html representation
    m = m._repr_html_()
    context = {'m': m, }
    return render(request, 'base/location.html', context)

@login_required(login_url='/userLogin')
def friends(request):
    data = {
        'friends': [],
        'users': [],
    }
    return render(request, "base/friends.html", data)


def about(request):
    return render(request, "base/about.html")

def register(request):
	if request.user.is_authenticated:
		return redirect('/home')
	else:
		form = CreateUserForm()
		if request.method == 'POST':
			form = CreateUserForm(request.POST)
			if form.is_valid():
				form.save()
				user = form.cleaned_data.get('username')
				messages.success(request, 'Account Created: ' + user)

				return redirect('userLogin')
			

		context = {'form':form}
		return render(request, 'base/register.html', context)
    
    
def userLogin(request):
	if request.user.is_authenticated:
		return redirect('/home')
	else:
		if request.method == 'POST':
			username = request.POST.get('username')
			password =request.POST.get('password')

			user = authenticate(request, username=username, password=password)

			if user is not None:
				auth_login(request, user)
				return redirect('/home')
			else:
				messages.info(request, 'Username OR password is incorrect')

		context = {}
		return render(request, 'base/login.html', context)
		
		
def userLogout(request):
	auth_logout(request)
	return redirect('/userLogin')
	

class EditProfile(generic.UpdateView):
	form_class = EditProfileForm
	template_name = 'base/editprofile.html'
	success_url = '/home'
	
	def get_object(self):
		return self.request.user

	
class PasswordChange(PasswordChangeView):
	form_class = PasswordChangeForm
	template_name = 'base/changepass.html'
	success_url = '/home'

