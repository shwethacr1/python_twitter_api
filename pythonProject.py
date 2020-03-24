##-----------Assignment 2------------------
# Importing necessary packages
from __future__ import print_function
from functools import partial
from sys import maxsize as maxint
import sys
import time
import json
import twitter
from pprint import pprint
import operator
import networkx
import matplotlib.pyplot as plt

# The keys and tokens to access the twitter API
CONSUMER_KEY = 'Q0LrDwlsAsaVqWRpU5hZtLLqi'
CONSUMER_SECRET = 'sGPN8SZRc2MoxHlDPzs86w859Gls4jNRxykRlELEo8FuE6Sls1'
OAUTH_TOKEN = '1232161413508009984-Pgs3CanAjYXEAPPR49cyyMKlNsq2M8'
OAUTH_TOKEN_SECRET = 'LZzBfnJrnYTthFd1aqHziuisndUHExiEYplFgGgSpyn2u'

# Using OAuth method
auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                           CONSUMER_KEY, CONSUMER_SECRET)

# Accessing the Twitter API
twitter_api = twitter.Twitter(auth=auth)


# Function from cookbook to make a Twitter request
def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw):
    # Defining a nested helper function that handles common HTTPErrors. Return an updated
    # value for wait_period if the problem is a 500 level error. Block until the
    # rate limit is reset if it's a rate limiting issue (429 error). Returns None
    # for 401 and 404 errors, which requires special handling by the caller.
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):

        # Checks if the wait period of request is greater than 1 hr otherwise print the message
        if wait_period > 3600:  # Seconds
            print('Too many retries. Quitting.', file=sys.stderr)
            raise e

        # Following are the different errors that could be encountered during program execution and their corresponding error message
        if e.e.code == 401:
            print('Encountered 401 Error (Not Authorized)', file=sys.stderr)
            return None
        elif e.e.code == 404:
            print('Encountered 404 Error (Not Found)', file=sys.stderr)
            return None
        elif e.e.code == 429:
            print('Encountered 429 Error (Rate Limit Exceeded)', file=sys.stderr)
            if sleep_when_rate_limited:
                print("Retrying in 15 minutes....", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(60 * 15 + 5)
                print('....Awake now and trying again.', file=sys.stderr)
                return 2
            else:
                raise e
        elif e.e.code in (500, 502, 503, 504):
            print('Encountered {0} Error. Retrying in {1} seconds'.format(e.e.code, wait_period), file=sys.stderr)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e

    wait_period = 2
    error_count = 0

    # try and catch which will catch exception such as URLError, BadStatusLine or HTTP error
    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError as e:
            error_count = 0
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return


# Function from cookbook to fetch friends and followers for particular id
def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=maxint, followers_limit=maxint):
    assert (screen_name != None) != (user_id != None), "Must have screen_name or user_id, but not both"

    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids,
                              count=5000)

    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids,
                                count=5000)

    friends_ids, followers_ids = [], []

    for twitter_api_func, limit, ids, label in [
        [get_friends_ids, friends_limit, friends_ids, "friends"],
        [get_followers_ids, followers_limit, followers_ids, "followers"]
    ]:

        if limit == 0: continue

        cursor = -1
        while cursor != 0:

            if screen_name:
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else:
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']

            print('Fetched {0} total {1} ids for {2}'.format(len(ids), label, (user_id or screen_name)), file
                  =sys.stderr)

            if len(ids) >= limit or response is None:
                break

    return friends_ids[:friends_limit], followers_ids[:followers_limit]


# Fetching followers and friends of user 'KulkarrniSandip'
friends_ids, followers_ids = get_friends_followers_ids(twitter_api,
                                                       screen_name="KulkarrniSandip",
                                                       friends_limit=200,
                                                       followers_limit=200)

# Displaying the result of get_friends_followers_ids by showing list of friends and followers
print(friends_ids)
print(followers_ids)

# getting the reciprocal by using the set operation intersection and storing it in reciprocal list
reciprocal = list(set(friends_ids) & set(followers_ids))
print("\n Reciprocal List is :", reciprocal)


# Function from cookbook to fetch the user profile data of a user, we will get number of followers from this function
def get_user_profile(twitter_api, screen_names=None, user_ids=None):
    assert (screen_names != None) != (user_ids != None), "Must have screen_names or user_ids, but not both"

    items_to_info = {}

    items = screen_names or user_ids

    while len(items) > 0:

        items_str = ','.join([str(item) for item in items[:100]])
        items = items[100:]

        if screen_names:
            response = make_twitter_request(twitter_api.users.lookup,
                                            screen_name=items_str)
        else:
            response = make_twitter_request(twitter_api.users.lookup,
                                            user_id=items_str)

        for user_info in response:
            if screen_names:
                items_to_info[user_info['screen_name']] = user_info
            else:
                items_to_info[user_info['id']] = user_info

    return items_to_info


# Displaying the user profile of reciprocal friends
pprint(get_user_profile(twitter_api, user_ids=reciprocal[0:5]))


# Following function fetches the distance-1, distance-2 friends and so on till depth 2 by passing screen_name
def crawl_followers_screen_name(twitter_api, screen_name, limit=100, depth=50):
    # Fetching reciprocal and fetching its profile
    friends_ids, followers_ids = get_friends_followers_ids(twitter_api, screen_name, friends_limit=5000,
                                                           followers_limit=5000)
    reciprocal = set(friends_ids) & set(followers_ids)
    response = get_user_profile(twitter_api, screen_names=None, user_ids=list(
        reciprocal))  # make_twitter_request(twitter_api.users.lookup, user_id=reciprocal)
    count_dict = {}
    for user, val in response.items():
        count_dict[user] = val['followers_count']

    # Sorting the dictionary so that we can get top 5 followers
    count_dict = dict(reversed(sorted(count_dict.items(), key=operator.itemgetter(1))))
    return (count_dict)

screen_name = "KulkarrniSandip"

# Following function fetches the distance-1, distance-2 friends and so on till depth 2 by passing screen_name
def crawl_followers_id(twitter_api, id, limit=100, depth=50):
    # Fetching reciprocal and fetching its profile
    friends_ids, followers_ids = get_friends_followers_ids(twitter_api, user_id=id, friends_limit=5000,
                                                           followers_limit=5000)
    reciprocal = set(friends_ids) & set(followers_ids)
    response = get_user_profile(twitter_api, screen_names=None, user_ids=list(reciprocal))
    count_dict = {}
    for user, val in response.items():
        count_dict[user] = val['followers_count']

    # Sorting the dictionary so that we can get top 5 followers
    count_dict = dict(reversed(sorted(count_dict.items(), key=operator.itemgetter(1))))
    return (count_dict)



# dictionary to store result of crawl_followers_screen_name
result_dict = {}

# Fetching crawl_followers_screen_name result in result dictionary
result_dict.update(crawl_followers_screen_name(twitter_api, screen_name, limit=100, depth=50))

# getting top 5 with max number of followers
while len(result_dict) > 5:
    result_dict.popitem()

# Plotting the graph for starting node and other top 5 nodes
G = networkx.Graph()
G.add_node(screen_name)
for i in list(result_dict):
    G.add_node(i)
    G.add_edge(screen_name, i)

# Getting the user_ids from the dictionary
ids = result_dict.keys()
ids_list = list(ids)

# These lists will store the result of crawling
crawl_result_list1 = {}
crawl_result_list2 = {}

# Printing the output dictionary
print(result_dict)

# Fetching next 100 nodes
for x in range(30):
    i = ids_list[x]
    crawl_result_list1 = crawl_followers_id(twitter_api, i, depth=50, limit=100)
    crawl_result_list2 = crawl_result_list1

    while len(crawl_result_list2) > 5:
        crawl_result_list2.popitem()

    # Plotting the graph for the next nodes
    for k in list(crawl_result_list2):
        G.add_node(k)
        G.add_edge(i, k)

    # getting more nodes
    for k in (list(crawl_result_list2.keys())):
        ids_list.append(k)

# print the users and total number of the next nodes
print(ids_list)
print(len(ids_list))

# Displaying the graph
networkx.draw(G, with_labels=True)
plt.draw()
plt.show()

# Writing final output to a file
f = open("output.txt", "w")
f.write("A social network is created\n")
f.write("Number of nodes is: " + str(networkx.number_of_nodes(G)))
f.write("\nNumber of edges is: " + str(networkx.number_of_edges(G)))
f.write("\nAverage Distance is: " + str(networkx.average_shortest_path_length(G)))
f.write("\nAverage Diameter is: " + str(networkx.diameter(G)))
# python_twitter_api
