#!python3
# A script to grab back dated data from the enphase API
from datetime import timedelta, date
from time import sleep
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

def daterange(date1, date2):
    for n in range(int ((date2 - date1).days)+1):
        yield date1 + timedelta(n)

start_dt = date(2020, 2, 1)
end_dt = date(2020, 6, 29)
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

for dt in daterange(start_dt, end_dt):
    dateList.append(dt.strftime("%Y-%m-%d"))

for date in dateList:
    print('Requesting date: ' + str(date), end = " ")
    energy = grabSolar(login, date)
    print('Returned value: ' + str(energy))
    energyList.append(energy)
    sleep(8)

csv = open('Weatherburn_Solar_Production.csv', 'w')
for i in range(len(dateList)):
    print(str(dateList[i]) + "," + str(energyList[i]))
    csv.write(str(dateList[i]) + "," + str(energyList[i]) + '\n')

csv.close()
