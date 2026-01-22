import requests

url = "https://domainr.p.rapidapi.com/v2/status"

querystring = {"mashape-key":"01762df410msh7bb27a1bad3a60bp19ab41jsnc3d3436f99eb","domain":"sdlkjfslkdfjlsdfjk239483.com"}

headers = {
	"x-rapidapi-key": "69356af50emshc2438832e3ed237p1a55a3jsne35348fbcd4c",
	"x-rapidapi-host": "domainr.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())



