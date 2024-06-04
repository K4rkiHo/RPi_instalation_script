import unittest
from API_server_3_10 import app

class TestFlaskAPI(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Přihlášení a získání JWT tokenu
        response = self.app.post('/api/login', json={'username': 'honza', 'password': 'heslo'})
        self.assertEqual(response.status_code, 200)
        self.token = response.json['access_token']

    # Testování cesty '/api/data/last_data'
    def test_get_last_weather_data(self):
        headers = {'Authorization': 'Bearer ' + self.token}
        response = self.app.get('/api/data/aggregated/today', headers=headers)
        self.assertEqual(response.status_code, 200)

    # Testování cesty '/api/data/aggregated/today'
    def test_get_aggregated_data_today(self):
        headers = {'Authorization': 'Bearer ' + self.token}
        response = self.app.get('/api/data/aggregated/today', headers=headers)
        self.assertEqual(response.status_code, 200)

    # Testování cesty '/api/login' - úspěšné přihlášení
    def test_login_success(self):
        response = self.app.post('/api/login', json={'username': 'honza', 'password': 'heslo'})
        self.assertEqual(response.status_code, 200)

    # Testování cesty '/api/login' - neúspěšné přihlášení
    def test_login_failure(self):
        response = self.app.post('/api/login', json={'username': 'invalid_username', 'password': 'invalid_password'})
        self.assertEqual(response.status_code, 401)

    # Testování cesty '/api/register' - úspěšná registrace
    def test_register_success(self):
        response = self.app.post('/api/register', json={'username': 'testtesttest', 'password': 'testtesttest', 'code': 'jei4Rail'})
        self.assertEqual(response.status_code, 201)

    # Testování cesty '/api/register' - neúspěšná registrace (uživatel již existuje)
    def test_register_failure_existing_user(self):
        response = self.app.post('/api/register', json={'username': 'new_user', 'password': 'password', 'code': 'jei4Rail'})
        self.assertEqual(response.status_code, 400)

    # Testování cesty '/api/is_valid'
    def test_is_valid(self):
        response = self.app.get('/api/is_valid')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['valid_token'], 1)
        
if __name__ == '__main__':
    unittest.main()
