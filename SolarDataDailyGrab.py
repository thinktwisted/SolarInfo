from datetime import date, timedelta
import json, requests

def grabSolar(login, startDate):
    key = login[5]
    userID = login[6]
    sysID = login[7]

    # Request Data from API
    # Example URL: https://api.enphaseenergy.com/api/v2/systems/1756688/energy_lifetime?start_date=2020-04-02&end_date=2020-05-01&key=277ccbea0a60ab7a2f1b58fdc8bd2825&user_id=4d546b794d4451324d773d3d0a
    #energy = 'https://api.enphaseenergy.com/api/v2/systems/%s/energy_lifetime?start_date=%s&end_date=%s&key=%s&user_id=%s' % (sysID, startDate, endDate, key, userID)
    energy = 'https://api.enphaseenergy.com/api/v2/systems/%s/energy_lifetime?start_date=%s&end_date=%s&key=%s&user_id=%s' % (sysID, startDate, startDate, key, userID)
    solarData = requests.get(energy)

    # Put data into dictionary & return the production
    prodData = json.loads(solarData.text)
    prodTotal = sum(int(i) for i in prodData['production'])
    prodTotal = prodTotal/1000 # convert Wh to kWh
    return prodTotal

dateList = []
energyList = []
loginfile = 'SolarLoginInfo.txt'

# Get the log in information from the text file
login = []
with open(loginfile) as file_object:
    for line in file_object:
        if line == None:
            continue
        else:
            login.append(line.rstrip())
today = date.today()
yesterday = today - timedelta(days = 1)
date = yesterday.strftime("%Y-%m-%d")
energy = grabSolar(login, date)

csv = open('Weatherburn_Solar_Production.csv', 'a') # 'w' is write 'a' is append
#csv.write(str(date) + "," + str(energy) + '\n')
csv.write(str(energy) + '\n')
csv.close()
