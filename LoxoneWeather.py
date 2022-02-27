#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socketserver
import http.server
import urllib
import json
import sys
import datetime
import requests
import os

# HTTP Proxy Server for the Loxone Weather Service
# (Can be run on a Raspberry Pi)

# You need a private DNS server, which the Miniserver uses. That DNS server needs
# to forward `weather.loxone.com` to this server!

API_KEY = os.environ.get('API_KEY')

licenseExpiryDate = datetime.datetime(2049,12,31, 0, 0)
LOXONE_WEATHER_SERVICE_PORT = 6066

def downloadReport(longitude, latitude, asl):
    payload = {'appid': API_KEY, 'lang': 'cz', 'units': 'metric', 'lon': longitude, 'lat': latitude}
    r = requests.get('https://api.openweathermap.org/data/2.5/onecall', params=payload)
    if r.status_code == 200:
        ret = r.content
    else:
        print('Error %d', (r.status_code))
        ret = None
    return ret

# Generate an icon for Loxone based on the openweathermap weather codes
# <https://openweathermap.org/weather-conditions#Weather-Condition-Codes-2>

def loxoneWeatherIcon(weatherReportHourly):
    iconConvertor = {
        "200": 18,	#	Thunderstorm	thunderstorm with light rain
        "201": 18,	#	Thunderstorm	thunderstorm with rain
        "202": 18,	#	Thunderstorm	thunderstorm with heavy rain
        "210": 18,	#	Thunderstorm	light thunderstorm
        "211": 18,	#	Thunderstorm	thunderstorm
        "212": 19,	#	Thunderstorm	heavy thunderstorm
        "221": 18,	#	Thunderstorm	ragged thunderstorm
        "230": 18,	#	Thunderstorm	thunderstorm with light drizzle
        "231": 18,	#	Thunderstorm	thunderstorm with drizzle
        "232": 18,	#	Thunderstorm	thunderstorm with heavy drizzle
        "300": 13,	#	Drizzle	light intensity drizzle
        "301": 13,	#	Drizzle	drizzle
        "302": 13,	#	Drizzle	heavy intensity drizzle
        "310": 13,	#	Drizzle	light intensity drizzle rain
        "311": 13,	#	Drizzle	drizzle rain
        "312": 13,	#	Drizzle	heavy intensity drizzle rain
        "313": 16,	#	Drizzle	shower rain and drizzle
        "314": 17,	#	Drizzle	heavy shower rain and drizzle
        "321": 16,	#	Drizzle	shower drizzle
        "500": 10,	#	Rain	light rain
        "501": 11,	#	Rain	moderate rain
        "502": 12,	#	Rain	heavy intensity rain
        "503": 12,	#	Rain	very heavy rain
        "504": 12,	#	Rain	extreme rain
        "511": 15,	#	Rain	freezing rain
        "520": 16,	#	Rain	light intensity shower rain
        "521": 16,	#	Rain	shower rain
        "522": 17,	#	Rain	heavy intensity shower rain
        "531": 17,	#	Rain	ragged shower rain
        "600": 20,	#	Snow	light snow
        "601": 21,	#	Snow	Snow
        "602": 22,	#	Snow	Heavy snow
        "611": 26,	#	Snow	Sleet
        "612": 28,	#	Snow	Light shower sleet
        "613": 29,	#	Snow	Shower sleet
        "615": 25,	#	Snow	Light rain and snow
        "616": 27,	#	Snow	Rain and snow
        "620": 23,	#	Snow	Light shower snow
        "621": 24,	#	Snow	Shower snow
        "622": 24,	#	Snow	Heavy shower snow
        "701": 6,	#	Mist	mist
        "711": 6,	#	Smoke	Smoke
        "721": 6,	#	Haze	Haze
        "731": 7,	#	Dust	sand/ dust whirls
        "741": 7,	#	Fog	fog
        "751": 7,	#	Sand	sand
        "761": 7,	#	Dust	dust
        "762": 7,	#	Ash	volcanic ash
        "771": 7,	#	Squall	squalls
        "781": 7,	#	Tornado	tornado
        "800": 1,	#	Clear	clear sky
        "801": 2,	#	Clouds	few clouds: 11-25%
        "802": 3,	#	Clouds	scattered clouds: 25-50%
        "803": 4,	#	Clouds	broken clouds: 51-84%
        "804": 5,	#	Clouds	overcast clouds: 85-100%
    }
    iconID = iconConvertor.get(str(weatherReportHourly['weather'][0]['id']), 1)
    return iconID

def getPrecipitation(hourly):
    return hourly.get('rain', hourly.get('snow', {})).get('1h', 0)

# Loxone is using www.meteoblue.com for their weather data, it's the same format!
def generateCSV(weatherReport, asl):
    csv = ""
    csv += "<mb_metadata>\n"
    csv += "id;name;longitude;latitude;height (m.asl.);country;timezone;utc-timedifference;sunrise;sunset;\n"
    csv += "local date;weekday;local time;temperature(C);feeledTemperature(C);windspeed(km/h);winddirection(degr);wind gust(km/h);low clouds(%);medium clouds(%);high clouds(%);precipitation(mm);probability of Precip(%);snowFraction;sea level pressure(hPa);relative humidity(%);CAPE;picto-code;radiation (W/m2);\n"
    csv += "</mb_metadata><valid_until>{:{dfmt}}</valid_until>\n".format(licenseExpiryDate, dfmt='%Y-%m-%d')
    # CAPE = Convective available potential energy <https://en.wikipedia.org/wiki/Convective_available_potential_energy>
    csv += "<station>\n"
    longitude = weatherReport['lon']
    # if longitude < 0:
    #     longitude = -longitude
    #     eastwest = 'W'
    # else:
    #     eastwest = 'E'
    latitude = weatherReport['lat']
    # if latitude < 0:
    #     latitude = -latitude
    #     northsouth = 'S'
    # else:
    #     northsouth = 'N'

    sunriseTime = '{:{sunrise}}'.format(datetime.datetime.fromtimestamp(weatherReport['daily'][0]['sunrise']), sunrise='%H:%M')
    sunsetTime = '{:{sunset}}'.format(datetime.datetime.fromtimestamp(weatherReport['daily'][0]['sunset']), sunset='%H:%M')
    # csv += ";Hostivice;{lon:.2f}°{eastwest};{lat:.2f}°{northsouth} ;{asl};;CEST;UTC{utcTimedifference:+.1f};{sunrise};{sunset};\n".format(lon=longitude,eastwest=eastwest,lat=latitude,northsouth=northsouth,asl=asl,utcTimedifference=weatherReport['timezone_offset'],sunrise=sunriseTime,sunset=sunsetTime)
    csv += ";Hostivice;{lon};{lat};{asl};;CEST;UTC{utcTimedifference:+.2f};{sunrise};{sunset};\n".format(lon=longitude,lat=latitude,asl=asl,utcTimedifference=weatherReport['timezone_offset']/3600,sunrise=sunriseTime,sunset=sunsetTime)
    for hourly in weatherReport['hourly']:
        time = datetime.datetime.fromtimestamp(hourly['dt'])
        iconID = loxoneWeatherIcon(hourly)
        csv += '{:{localDate};{weekday};{localTime}};'.format(time, localDate='%d.%m.%Y', weekday='%a', localTime='%H')
        csv += '{:5.1f};'.format(hourly['temp'])
        csv += '{:5.1f};'.format(hourly['feels_like'])
        csv += '{:3.0f};'.format(hourly['wind_speed'])
        csv += '{:3.0f};'.format(hourly['wind_deg'])
        csv += '{:3.0f};'.format(hourly['wind_gust'])
        csv += '{:3.0f};'.format(0.0)
        csv += '{:3.0f};'.format(hourly['clouds']*100)
        csv += '{:3.0f};'.format(0.0)
        csv += '{:5.1f};'.format(getPrecipitation(hourly))
        csv += '{:3.0f};'.format(100 if getPrecipitation(hourly) != 0 else 0)
        csv += '{:3.1f};'.format(0.0)
        csv += '{:4.0f};'.format(hourly['pressure'])
        csv += '{:3.0f};'.format(hourly['humidity']*100)
        csv += '{:6d};'.format(0)
        csv += '{:d};'.format(iconID)
        csv += '{:4.0f};'.format(hourly['uvi']*100)
        csv += '\n'
    csv += "</station>\n"
    return csv

def generateXML(weatherReport, asl):
    xml = '<?xml version="1.0"?>'
    xml += '<metdata_feature_collection p="m" valid_until="{:{dfmt}}">'.format(licenseExpiryDate, dfmt='%Y-%m-%d')

    # for hourly in weatherReport['hourly']['data']:
    for hourly in weatherReport['hourly']:
        time = datetime.datetime.fromtimestamp(hourly['dt'])
        iconID = loxoneWeatherIcon(hourly)
        xml += '<metdata>'
        xml += '<timepoint>{:%Y-%m-%dT%H:%M:%S}</timepoint>'.format(time)
        xml += '<TT>{:.1f}</TT>'.format(hourly['temp']) # Temperature (C)
        xml += '<FF>{:.1f}</FF>'.format(hourly['wind_speed']*1000/3600) # Wind Speed (m/s)
        windBearing = hourly['wind_deg']-180
        if windBearing < 0:
            windBearing += 360
        xml += '<DD>{:.0f}</DD>'.format(windBearing) # Wind Speed (Direction)
        xml += '<RR1H>{:5.1f}</RR1H>'.format(getPrecipitation(hourly)) # Rainfall (mm)
        xml += '<PP0>{:.0f}</PP0>'.format(hourly['pressure']) # Pressure (hPa)
        xml += '<RH>{:.0f}</RH>'.format(hourly['humidity']*100) # Humidity (%)
        xml += '<HI>{:.1f}</HI>'.format(hourly['feels_like']) # Perceived Temperature (C)
        xml += '<RAD>{:4.0f}</RAD>'.format(hourly['uvi']*100) # Solar Irradiation (0-20% (<60), 20-40% (<100), 40-100%)
        xml += '<WW>2</WW>' # Icon
        xml += '<FFX>{:.1f}</FFX>'.format(hourly['wind_gust']*1000/3600) # Wind Speed (m/s)
        xml += '<LC>{:.0f}</LC>'.format(0) # low clouds
        xml += '<MC>{:.0f}</MC>'.format(hourly['clouds']*100) # medium clouds
        xml += '<HC>{:.0f}</HC>'.format(0) # high clouds
        xml += '<RAD4C>{:.0f}</RAD4C>'.format(hourly['uvi']) # UV Index
        xml += '</metdata>'
    xml += '</metdata_feature_collection>\n'
    return xml

class Proxy(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path,query = self.path.split('?')
        query = urllib.parse.parse_qs(query)
        self.server_version = 'Apache/2.4.7 (Ubuntu)'
        self.sys_version = ''
        self.protocol_version = 'HTTP/1.1'
        if path == '/forecast/':
            self.send_response(200)
            self.send_header('Vary', 'Accept-Encoding')
            self.send_header('Connection', 'close')
            self.send_header('Transfer-Encoding', 'chunked')
            if 'asl' in query:
                asl = query['asl'][0]#int(query['asl'][0])
            else:
                asl = 0
            long,lat = query['coord'][0].split(',')
            if os.path.isfile('weather.json'):
                jsonReport = json.loads(open('weather.json').read())
            else:
                jsonReport = json.loads(downloadReport(float(long), float(lat), asl))
            if 'format' in query and int(query['format'][0]) == 1:
                reply = generateCSV(jsonReport, asl)
                self.send_header('Content-Type', 'text/plain')
            else:
                reply = generateXML(jsonReport, asl)
                self.send_header('Content-Type', 'text/xml')
            self.end_headers()
            self.wfile.write(bytes("%x\r\n%s\r\n" % (len(reply), reply),"utf-8"))
            self.wfile.write(bytes("0\r\n\r\n","utf-8"))
        else:
            print(path)
            print(urllib.parse.parse_qs(query))
            self.send_response(404)
            self.end_headers()

socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.ForkingTCPServer(('', LOXONE_WEATHER_SERVICE_PORT), Proxy)
httpd.serve_forever()
# jsonReport = json.loads(downloadReport(float(14.248515), float(50.078871), 0))
# reply = generateCSV(jsonReport, 0)
# print(reply)