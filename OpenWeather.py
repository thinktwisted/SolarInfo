#! python3
# Open Weather API Script to get the daily weather
# Run at 2PM every day to get peek at weather
# API Doc: https://openweathermap.org/current
import requests, json

loginfile = 'OpenWeatherAPI.txt'

# Get the log in information from the text file
login = []
with open(loginfile) as file_object:
    for line in file_object:
        if line == None:
            continue
        else:
            login.append(line.rstrip())
APPID = login[0]
# LOCATION = 'lon:-83.09,lat:40.18'
ZIP = 43065

# Download the JSON data from OpenWeatherMap.org's API.
#url ='https://api.openweathermap.org/data/2.5/forecast/daily?q=%s&cnt=3&APPID=%s' % (LOCATION, APPID)
url = 'https://api.openweathermap.org/data/2.5/weather?zip=%s&appid=%s' % (ZIP, APPID)

weatherData = requests.get(url)
weatherData.raise_for_status() # Checks for Exceptions

# Uncomment to see the raw JSON text:
#print(weatherData.text) 
weatherData = json.loads(weatherData.text)
print(weatherData)
weather = {}
weather['temp'] = round((weatherData['main']['temp_max']-273.15)*9/5+32,1) #convert to F
weather['humidity'] = weatherData['main']['humidity']
weather['sky'] = weatherData['weather'][0]['description']
weather['clouds'] = weatherData['clouds']['all'] # percent cloudly
weather['wind'] = weatherData['wind']['speed']
print(weather)

csv = open('Weatherburn_Solar_Production.csv', 'a') # 'w' is write 'a' is append
for key, value in weather.items():
    if key in ['wind']:
        csv.write(str(value) + '\n')
    else:
        csv.write(str(value) + ",")
csv.close()
