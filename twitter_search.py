import json
import tweepy
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def twitter_auth(auth_file='twitter_credentials.json'):
    with open(auth_file) as f:
        cr = json.load(f)
        auth = tweepy.OAuthHandler(cr['consumer_key'], cr['consumer_secret'])
        auth.set_access_token(cr['access_token'], cr['access_token_secret'])
        return auth


def search_one_domain(api, domain):
    tweets_max_count = 10000000  # Some arbitrary large number
    tweets_per_page = 100  # this is the max the API permits
    tweets = []

    # If results from a specific ID onwards are reqd, set since_id to that ID.
    # else default to no lower limit, go as far back as API allows
    since_id = None

    # If results only below a specific ID are, set max_id to that ID.
    # else default to no upper limit, start from the most recent tweet matching
    # the search query.
    max_id = -1

    tweets_count = 0
    logger.info("Searching tweets for domain: %s", domain)
    while tweets_count < tweets_max_count:
        try:
            if max_id <= 0:
                if since_id is None:
                    new_tweets = api.search(q=domain, count=tweets_per_page)
                else:
                    new_tweets = api.search(
                        q=domain, count=tweets_per_page, since_id=since_id)
            else:
                if since_id is None:
                    new_tweets = api.search(
                        q=domain, count=tweets_per_page, max_id=str(max_id - 1))
                else:
                    new_tweets = api.search(
                        q=domain,
                        count=tweets_per_page,
                        max_id=str(max_id - 1),
                        since_id=since_id)
            if len(new_tweets) == 0:
                logger.info('No more tweets found!')
                return tweets
            tweets += new_tweets
            tweets_count += len(new_tweets)
            logger.info('Downloading %s tweets ...', tweets_count)
            max_id = new_tweets[-1].id
        except tweepy.TweepError as e:
            # Just exit if any error
            logger.error(e)
            return tweets


def collect_tweets(api, domains):
    rows = []
    for domain in domains:
        for tweet in search_one_domain(api, domain):
            raw_id = tweet.id
            created_at = tweet.created_at
            json_str = tweet._json
            row = (domain, raw_id, created_at, json_str)
            rows.append(row)
    df = pd.DataFrame(
        rows, columns=['domain', 'raw_id', 'created_at', 'json_str'])
    return df


def sites_popularity(auth_file='twitter_credentials.json',
                     source_file='consensus.csv',
                     output='popularity.csv'):
    auth = twitter_auth(auth_file)
    api = tweepy.API(auth, wait_on_rate_limit=True)
    input_df = pd.read_csv(source_file)
    output_df = collect_tweets(api, input_df.Source.tolist())
    output_df.to_csv('popularity_tweets.csv', index=False)
    volume = output_df.groupby('domain').size().rename('volume').reset_index()
    df = pd.merge(
        input_df, volume, how='left', left_on='Source', right_on='domain')
    df.to_csv(output)
    return df