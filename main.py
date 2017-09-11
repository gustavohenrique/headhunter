import json
import sys
import csv
import os
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from quik import FileLoader


def get_data_from(user, cursor=''):
    if cursor and len(cursor) > 0:
        print('cursor: %s' % cursor)
        cursor = 'after: "%s"' % cursor

    query = '''
        query {
          user(login: "%s") {
            followers(first: 100 %s) {
              edges {
                node {
                  login
                  name
                  location
                  createdAt
                  updatedAt
                  company
                  avatarUrl
                  email
                  url
                }
                cursor
              }
              totalCount
              pageInfo {
                hasNextPage
                hasPreviousPage
                endCursor
              }
            }
          }
          rateLimit {
            limit
            cost
            remaining
            resetAt
          }
        }''' % (user, cursor)

    headers = {'Authorization': 'bearer %s' % os.getenv('GITHUB_API_TOKEN')}
    url = 'https://api.github.com/graphql'
    transport = RequestsHTTPTransport(url, headers=headers, use_json=True)
    client = Client(transport=transport)
    resp = client.execute(gql(query))
    followers = resp.get('user').get('followers')
    page_info = followers.get('pageInfo')
    return {
        'total_followers': followers.get('totalCount'),
        'followers': followers.get('edges'),
        'has_next_page': page_info.get('hasNextPage'),
    }


def get_followers_from(user):
    data = get_data_from(user)
    total = data.get('total_followers')
    followers = data.get('followers')
    cursor = followers[-1].get('cursor')
    has_next_page = data.get('has_next_page')
    i = 1
    print('Page %s... Ok. %s/%s' % (i, len(followers), total))
    while has_next_page and len(followers) <= total:
        data = get_data_from(user, cursor)
        i += 1
        print('Page %s... Ok. %s/%s' % (i, len(followers), total))
        followers += data.get('followers')
        has_next_page = data.get('has_next_page')
        cursor = followers[-1].get('cursor')

    return followers


def format_date(s):
    return s[0:10]


def fill(s):
    if s is None or len(s) == 0:
        return '?'
    return s.lower()


def is_in_brazil(location):
    places = ['aulo', 'brasil', 'brazil', 'janeiro', 'recife', 'pe', 'rj', 'rs', 'sp', 'rn', 'rio', 'mt', 'curitiba']
    for p in places:
        if location.find(p) > -1:
            return True
    return False

class Follower(object):
    pass


def to_obj(people):
    result = []
    for p in people:
        node = p.get('node')
        location = fill(node.get('location', '-'))
        if not is_in_brazil(location):
            continue
        f = Follower()
        f.name = fill(node.get('name', '?'))
        f.login = node.get('login', '')
        f.location = location
        f.created_at = format_date(node.get('createdAt'))
        f.updated_at = format_date(node.get('updatedAt'))
        f.company = fill(node.get('company', '-'))
        f.avatar_url = node.get('avatarUrl', '')
        f.email = fill(node.get('email', '-'))
        f.url = node.get('url', '')
        f.cursor = p.get('cursor')
        result.append(f)

    return result


if __name__ == '__main__':
    user = sys.argv[1]
    people = get_followers_from(user)
    followers = to_obj(people)
    lines = []
    for f in followers:
        lines.append([f.name, f.login, f.location, f.company, f.created_at, f.updated_at, f.email])

    with open('%s.csv' % user, 'w') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerows(lines)

    loader = FileLoader('./')
    template = loader.load_template('template.html')
    content = template.render({'followers': followers}, loader=loader)
    with open('%s.html' % user, 'w') as f:
        f.write(content)

