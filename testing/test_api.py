import requests
import json

# Probar crear una mesa
url = 'https://sistema-ima.sistemataup.online/api/mesas/crear'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN_HERE'  # Necesitas un token válido
}
data = {
    'numero': 1,
    'capacidad': 4
}

try:
    response = requests.post(url, headers=headers, json=data)
    print(f'Status Code: {response.status_code}')
    print(f'Response: {response.text}')
except Exception as e:
    print(f'Error: {e}')