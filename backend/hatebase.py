from hatebase import HatebaseAPI
import requests
import json


hatebase = HatebaseAPI({"key": "aAfXkBDxgeJWmHrZnmqwPyLMyic7YRC4"})
filters = {'is_about_nationality': '1', 'language': 'eng', 'country_id': 'US'}
format = "json"
json_response = hatebase.getSightings(filters=filters, format=format)
print(json_response)
