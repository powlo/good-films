import os
import unittest
from unittest import mock
import guardian_api

class MockAPI(object):
    
    def json(self):
        return {
            'response': {
                'results': [
                    {'webTitle': 'a film review'}
                ]
            }
        }

@mock.patch('guardian_api.requests.get')
class TestGuardianAPI(unittest.TestCase):

    def test_simple(self, mock_get):
        mock_get.return_value.json.return_value = {
            'response': {
                'results': [
                    {'webTitle': 'a film review'}
                ]
            }
        }
        films = guardian_api.get_films()
        self.assertEqual(1, len(films))
        self.assertEqual({'title': 'a film'}, films[0])
