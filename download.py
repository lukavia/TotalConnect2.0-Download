#!/usr/bin/env python3

import os.path
import datetime
import configparser
import requests

#import string, os, sys, httplib
import xml.etree.ElementTree as ET

config = configparser.ConfigParser()
config.read("config.ini")

#https://rs.alarmnet.com/TC21api/tc2.asmx?
def call(action, body):
    url = "https://rs.alarmnet.com/TC21API/TC2.asmx"

    payload = """
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <soapenv:Header/>
    <soapenv:Body>
        <tns:{0} xmlns:tns="https://services.alarmnet.com/TC2/">
            {1}
        </tns:{0}>
    </soapenv:Body>
    </soapenv:Envelope>""".format(action, body)

    # headers
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'https://services.alarmnet.com/TC2/' + action
    }
    # POST request
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.text


def LoginAndGetSessionDetailsEx(username, password):
    response = call('LoginAndGetSessionDetailsEx', 
        """
        <tns:userName>{}</tns:userName>
        <tns:password>{}</tns:password>
        <tns:ApplicationID>16808</tns:ApplicationID>
        <tns:ApplicationVersion>3.30.1.24</tns:ApplicationVersion>
        <tns:LocaleCode></tns:LocaleCode>
        """.format(username, password)
    )
    tree = ET.fromstring(response)
    sessionHash = tree.find('.//{https://services.alarmnet.com/TC2/}SessionID').text
    locationId = tree.find('.//{https://services.alarmnet.com/TC2/}LocationId').text
    return sessionHash, locationId

def GetPartnerVideoURL(sessionHash, locationId, deviceEventId):
    response = call('GetPartnerVideoURL',
        """
        <tns:SessionId>{}</tns:SessionId>
        <tns:locationId>{}</tns:locationId>
        <tns:deviceEventId>{}</tns:deviceEventId>
        """.format(sessionHash, locationId, deviceEventId)
    )

    tree = ET.fromstring(response)
    activityUrl = tree.find('.//{https://services.alarmnet.com/TC2/}activityUrl').text
    return activityUrl

def GetAllEvents(sessionHash, locationId):
    global downloadDir
    EventRecordId = 0
    hasmore = 'true'
    while hasmore == 'true':
        response = call('GetAllEvents',
            """
            <tns:SessionId>{}</tns:SessionId>
            <tns:FilterClass>1</tns:FilterClass>
            <tns:LocationId>{}</tns:LocationId>
            <tns:LastEventIdReceived>{}</tns:LastEventIdReceived>
            """.format(sessionHash, locationId, EventRecordId)
        )
        tree = ET.fromstring(response)

        for event in tree.findall('.//{https://services.alarmnet.com/TC2/}EventRecord'):
            EventRecordId = event.find('{https://services.alarmnet.com/TC2/}EventRecordId').text
            RecDateTimeGMT = event.find('{https://services.alarmnet.com/TC2/}RecDateTimeGMT').text
            creation_time = datetime.datetime.strptime(RecDateTimeGMT,'%Y-%m-%d %I:%M:%S %p').replace(tzinfo=datetime.timezone.utc)
            file = downloadDir + '/'  + datetime.datetime.fromtimestamp(creation_time.timestamp()).strftime('%Y-%m-%d/%H:%M - ') + event.find('{https://services.alarmnet.com/TC2/}Event').text + ' ' + EventRecordId

            if not os.path.isfile(file + '.mp4'):
                if (event.find('{https://services.alarmnet.com/TC2/}EventType').text in ('80003','80007','80008')):
                    activityUrl = GetPartnerVideoURL(sessionHash, locationId, EventRecordId)
                    print('Downloading {}'.format(file + '.mp4'))
                    r = requests.get(activityUrl, allow_redirects=True)
                    os.makedirs(os.path.dirname(file), exist_ok=True)
                    open(file + '.mp4', 'wb').write(r.content)
                    os.utime(file + '.mp4', (creation_time.timestamp(), creation_time.timestamp()))
                    ET.ElementTree(event).write(file + '.xml')
        hasmore = tree.find('.//{https://services.alarmnet.com/TC2/}HasMore').text

username = config["Authentication"]['username']
password = config["Authentication"]['password']
downloadDir = config["Download"]["path"]

sessionHash, locationId = LoginAndGetSessionDetailsEx(username, password)

GetAllEvents(sessionHash, locationId)
