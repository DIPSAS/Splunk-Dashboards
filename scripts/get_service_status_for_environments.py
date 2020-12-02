#! /usr/bin/python

import sys, getopt, os, json, traceback, ssl
import urllib2
from urllib2 import HTTPError
from urllib2 import URLError
import platform    # For getting the operating system name
import subprocess  # For executing a shell command
import socket      # Used to catch timeout from urllib2
import ssl         # Used to catch timeout from urllib2

metadataFile='metadata.json'
   
def using():
  filename = os.path.realpath(__file__)
  
  print ()
  print ("Usage:")
  print (' ', filename, '[arguments]')
  print ()
  print ('Arguments:')
  print ('  -m | --metadata  Path to endpoints.json - used to define status endpoint - default: ' + metadataFile)
  print ('  -h | --help       This help text')
  
  sys.exit()

  
def handleCliArgs(argv):
  global metadataFile

  try:
    opts, args = getopt.getopt(argv,":m:h",["help","metadata="])
    
    for opt, arg in opts:
      if opt in ("-h", "--help"):
        using()
      elif opt in ("-m", "--metadata"):
        metadataFile = arg 
  
  except getopt.GetoptError as e:
    print ()
    print ("ERROR: The script was not used as intended --", e)
    using() 


def main(argv):
  handleCliArgs(argv)
  
  with open(os.path.dirname(os.path.abspath(__file__))+"\\"+metadataFile, 'r') as f:
    metadata = json.load(f)
    
  for env in metadata:
    serviceStatus = SetInitialServiceStatus(env)
    try:
      for machine in env['machines']:
        try:
          getServiceStatusForMachine(env, machine)
        except HTTPError as err:
          serviceStatus['host'] = {
            'name': machine['name']
          }
          serviceStatus['ping'] = {'code': err.code}
          print (json.dumps(serviceStatus))
        except Exception as err:
          var = traceback.format_exc()
          serviceStatus['host'] = {
            'name': machine['name']
          }
          serviceStatus['error'] = "Failed to fetch service status for machine - {0}".format(var)
          print (json.dumps(serviceStatus))
      getThirdPartyServiceStatus(env)
    except Exception as err:
      var = traceback.format_exc()
      serviceStatus['error'] = 'Failed to fetch service status for environment - {0}'.format(var)
      print (json.dumps(serviceStatus))


def getServiceStatusForMachine(env, machine):
  serviceStatus = SetInitialServiceStatus(env)
  serviceStatus['host'] = { 
    'name': machine['name']
  }
  
  if machine["uri"]:
    hostName = machine["uri"][machine["uri"].find(':') + 3:machine["uri"].rfind(':')]
    reply = pingHost(hostName)
    serviceStatus['host']['ping'] = { 
      'hostname': hostName,
      'gotReply': str(reply)
    }
    print(json.dumps(serviceStatus))
    if not reply:
      return
      
  for service in machine['verifiableServiceEndpoints']:
    try:
      serviceStatus['serviceName'] = service['serviceName']
      serviceStatus.pop('ping', '')
      serviceStatus.pop('health', '')
      serviceStatus.pop('error', '')
      
      serviceBaseUrl = service['serviceBaseUrl']
      for endpoint in service['endpoints']:
        if endpoint['endpointAddress'].endswith('/status/ping'):
          url = serviceBaseUrl + endpoint['endpointAddress']
          getServiceStatusOfType('ping', url, serviceStatus)
        if endpoint['endpointAddress'].endswith('/status/health'):
          url = serviceBaseUrl + endpoint['endpointAddress']
          getServiceStatusOfType('health', url, serviceStatus)
    except HTTPError as err:
      serviceStatus['ping'] = {'code': err.code}
    except URLError as err:
      serviceStatus['error'] = "URL Error: " + str(err)
    except ssl.SSLError as err:
      serviceStatus['error'] = "SSL Error: " + str(err)
    except socket.timeout:
      serviceStatus['error'] = "Failed to fetch service status {0} - The read operation timed out".format(service['serviceName'])
    except Exception as err:
      var = traceback.format_exc()
      serviceStatus['error'] = "Failed to fetch service status {0} - {1}".format(service['serviceName'], var)
    print (json.dumps(serviceStatus))
    
  
def getThirdPartyServiceStatus(env):
  thirdpartyVariables = env['thirdparty']
  
  thirdpartyChecks = { }
  try:
    thirdpartyChecks['BIPublisherScheduleService'] = {
      'hostName': thirdpartyVariables['BIPublisher.HostName'].split('.')[0],
      'pingEndpoint': 'http://'+thirdpartyVariables['BIPublisher.HostName']+':'+thirdpartyVariables['BIPublisher.Port']+'/xmlpserver/services/v2/ScheduleService'
    }
  except:
    pass
  try:
    thirdpartyChecks['BIPublisherReportService'] = {
      'hostName': thirdpartyVariables['BIPublisher.HostName'].split('.')[0],
      'pingEndpoint': 'http://'+thirdpartyVariables['BIPublisher.HostName']+':'+thirdpartyVariables['BIPublisher.Port']+'/xmlpserver/services/v2/ReportService'
    }
  except:
    pass
  try:
    thirdpartyChecks['BIPublisherSecurityService'] = {
      'hostName': thirdpartyVariables['BIPublisher.HostName'].split('.')[0],
      'pingEndpoint': 'http://'+thirdpartyVariables['BIPublisher.HostName']+':'+thirdpartyVariables['BIPublisher.Port']+'/xmlpserver/services/v2/SecurityService'
    }
  except:
    pass
  try:
    thirdpartyChecks['BIPublisherCatalogService'] = {
      'hostName': thirdpartyVariables['BIPublisher.HostName'].split('.')[0],
      'pingEndpoint': 'http://'+thirdpartyVariables['BIPublisher.HostName']+':'+thirdpartyVariables['BIPublisher.Port']+'/xmlpserver/services/v2/CatalogService'
    }
  except:
    pass
  try:
    thirdpartyChecks['RabbitMqAMQP'] = {
      'hostName': thirdpartyVariables['AMQP.HostName'].split('.')[0],
      'pingEndpoint': 'https://'+thirdpartyVariables['AMQP.HostName']+':15672/api/vhosts/'+thirdpartyVariables['AMQP.VirtualHost'],
      'userName': 'guest',
      'password': 'guest'
    }
  except:
    pass
  try:
    thirdpartyChecks['RabbitMqMQTT'] = {
      'hostName': thirdpartyVariables['MQTT.HostName'].split('.')[0],
      'pingEndpoint': 'https://'+thirdpartyVariables['MQTT.HostName']+':15672/api/vhosts/'+thirdpartyVariables['MQTT.VirtualHost']+'',
      'userName': 'guest',
      'password': 'guest'
    }
  except:
    pass
    
  for name, thirdpartyCheck in thirdpartyChecks.items():
    try:
      url = thirdpartyCheck['pingEndpoint']
      serviceStatus = SetInitialServiceStatus(env)
      serviceStatus['serviceName'] = name
      if ('hostName' in thirdpartyCheck):
        serviceStatus['host'] = {
          'name': thirdpartyCheck['hostName']
        }
      serviceStatus['ping'] = { 'url': url }
      
      if ('userName' in thirdpartyCheck) and ('password' in thirdpartyCheck):
        p = urllib2.HTTPPasswordMgrWithDefaultRealm()
        p.add_password(None, url, thirdpartyCheck['userName'], thirdpartyCheck['password'])
        handler = urllib2.HTTPBasicAuthHandler(p)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)
      ping = urllib2.urlopen(url, timeout = 30)
      code = ping.getcode()
      contents = ping.read().decode('utf-8')
      serviceStatus['ping']['code'] = code
      try:
        serviceStatus['ping']['responce'] = json.loads(contents)
      except ValueError as e:
        serviceStatus['ping']['responce'] = contents
    except HTTPError as err:
      serviceStatus['ping']['code'] = err.code
    except URLError as err:
      serviceStatus['error'] = "URL Error: " + str(err)
    except Exception as err:
      var = traceback.format_exc()
      serviceStatus['error'] = 'Failed to fetch service status for thirdparty - {0}'.format(var)
      
    print (json.dumps(serviceStatus))
  
  
def pingHost(host):
  param = '-n' if platform.system().lower()=='windows' else '-c'
  command = ['ping', param, '1', host]
  return subprocess.call(command, stdout=open(os.devnull, 'wb')) == 0
    

def getServiceStatusOfType(type, url, serviceStatus):
  serviceStatus[type]={'url': url}
  health = urllib2.urlopen(url, timeout=30)
  code = health.getcode()
  contents = health.read().decode('utf-8')
  serviceStatus[type]['code'] = code
  try:
    serviceStatus[type]['responce'] = json.loads(contents)
  except ValueError as e:
    serviceStatus[type]['responce'] = contents


def SetInitialServiceStatus(env):
  serviceStatus = {
    'environment': {
      'name': env['name']
    }
  }
  if len(env['projects']) > 0:
    arenaProject = env['projects'][0]
    classicVersion = 0
    database = ""
    for project in env['projects']: 
      if VersionNewer(project['ArenaVersion'], arenaProject['ArenaVersion']): 
          arenaProject = project
    if 'ClassicVersion' in arenaProject:
        classicVersion = arenaProject['ClassicVersion']
    if 'Database' in arenaProject:
        database = arenaProject['Database']
    serviceStatus = {
      'environment': {
        'name': env['name'],
        'lastDeploy': arenaProject['lastDeploy'],
        'arenaVersion': arenaProject['ArenaVersion'],
        'classicVersion': classicVersion,
        'database': database,
        'project': arenaProject['name']
      }
    }
  
  return serviceStatus
  

def VersionNewer(version1, version2):
  version1Array = version1.split('.')
  version2Array = version2.split('.')
  longestVersion = 0
  
  if (len(version1Array) > len(version2Array)):
    longestVersion = len(version1Array)
  else:
    longestVersion = len(version2Array)
    
  for i in range(longestVersion):
    if len(version1Array) <= i:
      return False
    if len(version2Array) <= i:
      return True
    if version1Array[i] > version2Array[i]:
      return True
      
  return False


if __name__ == '__main__':
   main(sys.argv[1:])