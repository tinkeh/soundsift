from django.test import TestCase
from views import echonestInfoFetch, hotttFilter
# Create your tests here.
import soundcloud
import pyechonest
import heapq
from heapq import heappush, heappop
from pyechonest import config
from pyechonest import artist
client = soundcloud.Client(client_id="f504baf9fb464877d4e6d69ab6aed100")
config.ECHO_NEST_API_KEY ="QWGHNEBW6H7IDIUB1"
def test_set(username):
    artist_list = []
    offset_value = 0
    while True:
        followings = client.get('users/' + username + '/followings', offset=offset_value)
        if len(followings) <= 0:
            break
        counter = 0
        for artist in followings:
            description = artist.description
            if description and len(description) >= 50:
                description = artist.description[:50]
            elif description:
                description = artist.description
            else:
                description = None
            artist_list.append({"artist_user_name": artist.username,
                                "description": artist.description,
                                "img_src": artist.avatar_url})
            counter += 1
        offset_value += 50
        break #just for testing purposes
    return artist_list

def test_set_artist(username):
    artist_list = []
    offset_value = 0
    while True:
        followings = client.get('users/' + username + '/followings', offset=offset_value)
        if len(followings) <= 0:
            break
        counter = 0
        for artist in followings:
            if counter > 5:
                break
            artist_list.append({"artist_user_name": artist.username})
            counter += 1
        offset_value += 50
    return artist_list

def echonestInfoFetch_reduced(artist_list):
    resultant_list = []
    print "artist list's length: " + str(len(artist_list))
    for artist_dict in artist_list:
        resultant_dictionary = {}
        try:
            artist_object = artist.Artist(artist_dict["artist_user_name"])
        except pyechonest.util.EchoNestAPIError:
            continue
        artist_name = str(artist_object)
        print "current artist's name: " + artist_name
        resultant_dictionary["artist_name"] = artist_name
        news_dict = None if len(artist_object.news) == 0 else artist_object.news[0]
        if not news_dict:
            print artist_name + " does not have any news articles"
            continue
        resultant_dictionary["news_title"] = news_dict["name"]
        resultant_dictionary["hotttnesss"] = artist_object.get_hotttnesss()
        print artist_name + "'s hotttnesss is:  " + str(resultant_dictionary["hotttnesss"])
        resultant_list.append(resultant_dictionary)
    return resultant_list


#solely for testing purposes
def hotttFilter_reduced(resultant_list):
    #flips the order of the prio queue so those with the highest hotttness are brought to the front
    queue = []
    print "\n\n\nlist before queue:"
    for result in resultant_list:
        print result
    for artist_dict in resultant_list:
        heappush(queue, (artist_dict["hotttnesss"], artist_dict))
    print "\n\n\n\n current queue:"
    print queue
    count = 0
    most_popular_list = []
    length = len(queue)
    while count < length:
        item  = heappop(queue)
        most_popular_list.append(item)
        count += 1
    return most_popular_list

def run_test():
    st = test_set("x-flx-x")
    new_set = echonestInfoFetch(st)
    final_set = hotttFilter(new_set)
    for item in final_set:
        print item
