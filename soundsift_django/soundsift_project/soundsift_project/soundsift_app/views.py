from django.shortcuts import render, render_to_response
from django.template import loader, RequestContext, Template, Context
from django.http import HttpResponse
from django.core import serializers
from urllib import urlopen
import requests
import nltk
from heapq import heappush, heappop, heapify
import soundcloud
from ..settings import ECHONEST_API_KEY, ECHONEST_CONSUMER_KEY
from pyechonest import config, artist
import pyechonest
import os
root_directory = os.path.dirname(os.path.dirname(__file__))
config.ECHO_NEST_API_KEY = ECHONEST_API_KEY


client = soundcloud.Client(client_id="f504baf9fb464877d4e6d69ab6aed100")

def renderEntryPage(request):
    fil = open(root_directory + "/soundsift_app/web/main.html").read()
    template = Template(fil)
    #template = loader.get_template('/soundsift_app/web/main.html')
    return HttpResponse(template.render(RequestContext(request)))

#This takes in the Souncloud username and returns a dictionary with corresponding SC information about the users'
# artists that he follows
def processUsername(request):
    username_dict = request.POST.dict()
    username = username_dict["name"]
    #this includes the a list with elements as follows:
    # {artist_user_name : artist's user name,
    # description: user's description,
    # full_name: user's full_name}
    artist_list = []
    offset_value = 0
    artist_dict = {}
    while True:
        followings = client.get('users/' + username + '/followings', offset=offset_value)
        if len(followings) <= 0:
            break
        for artist in followings:
            description = artist.description
            if description and len(description) >= 50:
                description = artist.description[:50]
            elif description:
                description = artist.description
            else:
                description = None
            artist_list.append({"artist_user_name": artist.username,
                                  "description": description,
                                  "img_src": artist.avatar_url})
            artist_dict[artist.username] = (description, artist.avatar_url)
        offset_value += 50
    #normalized_list = normalize(artist_list)
    based_on_hotttnesss = True
    based_on_favorites = True
    if based_on_favorites:
        favorites = recentlyFavoritedArtists(username, 200, 20) #limit also set to 50
        intersection = set([art["artist_user_name"] for art in artist_list]) & set(favorites)
        relevant_artist_list = []
        for pop_artist in list(intersection):
            dic = {"artist_user_name": pop_artist,
                   "description": artist_dict[pop_artist][0],
                   "img_src": artist_dict[pop_artist][1]
            }
            relevant_artist_list.append(dic)
        if len(artist_list) < 10: #there needs to be enough artists that we can find news articles
            artist_list = relevant_artist_list
    #news_list = echonestInfoFetch(artist_list, 50)
    artist_list = normalize(artist_list)
    news_list = echonestInfoFetch(artist_list[:30], 20, based_on_hotttnesss) #EVENTUALLY ARTIST_LIST SHOULD NOT BE SUBLISTED, BUT IT OVERSEARCHES THE API ... will be normalized_list, and limit should be adjusted to whatever our max query bandwidth can be
    context_dict = {"news_list": news_list,
                    "username": username}
    fil = open(root_directory + "/soundsift_app/web/feed.html").read()
    template = Template(fil)
    context = RequestContext(request, context_dict)
    return HttpResponse(template.render(context))


#resultant dictionary is represented as follows:
# artist_name: this artist's name,
# news_title: the news' title
# news_content: the news' content
# news_url: the news' url
# img_src: the artist's sc img
def echonestInfoFetch(artist_list, limit, based_on_hotttnesss):
    resultant_list = []
    for artist_dict in artist_list:
        resultant_dictionary = {}
        try:
            artist_object = artist.Artist(artist_dict["artist_user_name"])
        except pyechonest.util.EchoNestAPIError:
            continue
        artist_name = str(artist_object)
        resultant_dictionary["artist_name"] = artist_name
        news_dict = None if len(artist_object.news) == 0 else artist_object.news[0]
        if not news_dict:
            continue
        resultant_dictionary["news_title"] = news_dict["name"]
        resultant_dictionary["news_content"] = cutoff_at_last_word(news_dict["summary"])
        resultant_dictionary["news_url"] = news_dict["url"]
        resultant_dictionary["img_src"] = artist_dict["img_src"]
        resultant_dictionary["hotttnesss"] = artist_object.get_hotttnesss()
        resultant_list.append(resultant_dictionary)
    if based_on_hotttnesss:
        resultant_list = hotttFilter(resultant_list, limit)
    return resultant_list

def cutoff_at_last_word(paragraph):
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if len(paragraph) < 399 or paragraph[399] not in alphabet:
        return paragraph[:400]
    else:
        counter = 399
        while counter > 0:
            if paragraph[counter] not in alphabet:
                break
            counter -= 1
        return paragraph[:counter + 1]
#this takes in a list of the artist's info (including the news content/title of most recent article as well)
# and returns a list of the top LIMIT most popular artists as determined by "hotttness" level
def hotttFilter(resultant_list, limit):
    #flips the order of the prio queue so those with the highest hotttness are brought to the front
    queue = []
    limit = limit if len(resultant_list) > limit else len(resultant_list)
    for artist_dict in resultant_list:
        heappush(queue, (-artist_dict["hotttnesss"], artist_dict))
    count = 0
    most_popular_list = []
    while count < limit:
        item  = heappop(queue)
        most_popular_list.append(item[1])
        count += 1
    return most_popular_list

def favoriteKey(username):
     offset_limit = 0
     while True:
        favorite_tracks = client.get('users/' + username + '/favorites', offset=offset_limit)

# This takes in the soundcloud user's username and returns a list of the past LIMIT artists who produced tracks that the user has
# liked and who is in the user's FOLLOWED_ARTISTS
# eventually should implement a prio queue which tracks the counts and only has a max length of some limit
def recentlyFavoritedArtists(username, song_limit, artist_limit):
    offset_limit = 50 if song_limit > 50 else song_limit
    queue = PrioQueueWithLimit()
    while True:
        favorite_tracks = client.get('users/' + username + '/favorites', offset=offset_limit)
        song_limit = len(favorite_tracks) if len(favorite_tracks) < song_limit else song_limit
        for favorite_track in favorite_tracks:
            artist_name = favorite_track.user["username"]
            queue.push(artist_name)
        if offset_limit == song_limit:
            break
        offset_limit = offset_limit + 0 if song_limit - offset_limit > 50 else song_limit
    return queue.return_top(artist_limit)


"""
	will take in a list of dictionaries
	[
		{name: "brendan",
		description: "hey this guy brendan really knows whats up"
		},
		{name: "sam",
		desciption: "no question, also knows whats up" }
		{"name": "DILLONFRANCIS", "description": "dillon francis is a baller"}
	]
"""


def normalize(artist_store):
    artists = list()
    for artist in artist_store:
        stripped_name = strip_symbols(artist["artist_user_name"].lower())
        stripped_name = stripped_name.replace("music", "")
        if len(stripped_name.split()) != 1:
            artists.append({"artist_user_name": stripped_name,
                            "description": artist["description"],
                            "img_src": artist["img_src"]})
            continue
        if artist["description"] != None:
            parse_desc = strip_symbols(artist["description"].lower()).split()
        else:
            artists.append({"artist_user_name": stripped_name,
                            "description": artist["description"],
                            "img_src": artist["img_src"]})
            continue
        previous_word = ""
        new = False
        for word in parse_desc:
            if previous_word + word == stripped_name:
                if len(previous_word) > 0:
                    previous_word = previous_word + " "
                artists.append({"artist_user_name": previous_word + word,
                            "description": artist["description"],
                            "img_src": artist["img_src"]})
                print(previous_word + " " + word)
                new = True
                break
            else:
                previous_word = word
        if not new:
            artists.append({"artist_user_name": stripped_name,
                            "description": artist["description"],
                            "img_src": artist["img_src"]})

    return artists


def strip_symbols(word):
    alphabet = "abcdefghijklmnopqrstuvwxyz1234567890 "
    new_word = ""
    for letter in word:
        if letter in alphabet:
            new_word += letter
    return new_word


# Create your views here.
class PrioQueueWithLimit():
    def __init__(self):
        self.queue = [] #stores a tuple with (count first, name of artist)
        self.queue_names = {}
        self.count = 0
    def push(self, artist_name):
        if artist_name in self.queue_names:
            index = self.queue.index((self.queue_names[artist_name], artist_name))
            popped_item = self.queue[index]
            self.queue = self.queue[:index] + self.queue[index + 1:] #remove item from heap
            heapify(self.queue)
            heappush(self.queue, (popped_item[0] - 1, artist_name))
            self.queue_names[artist_name] -= 1
        else:
            heappush(self.queue, (-1, artist_name))
            self.queue_names[artist_name] = -1
            self.count += 1
    def pop(self):
        return heappop(self.queue)
    def return_top(self, limit):
        counter = 0
        return_list = []
        while counter < limit and counter < self.count:
            return_list.append(heappop(self.queue)[1])
            counter += 1
        return return_list
    def is_in(self, item):
        return item in self.queue

