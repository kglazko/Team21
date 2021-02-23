import http.client
import urllib.request
import urllib.parse
import urllib.error
import base64
import pandas as pd


headers = {
    # Request headers
    'Content-Type': 'application/json',
    'Ocp-Apim-Subscription-Key': '1e0504791eae4eeb9535ec7d4962aaec',
}


def analyze(text):
    params = urllib.parse.urlencode({
    })
    try:
        conn = http.client.HTTPSConnection('api.tisane.ai')
        conn.request("POST", "/parse?%s" % params,
                     '{"language": "en", \
                    "content": "' + text + '", \
                    "settings": {"parses": false}}',
                     headers)
        response = conn.getresponse()
        data = response.read()
        print(data)
        conn.close()
    except Exception as e:
        print("error: ", e)


# Using our own collected dataset
data = pd.read_csv("labeled_data.csv")

for i in range(10):
    tweet = data["tweet"][i]
    analyze(tweet)
    print("____________")
