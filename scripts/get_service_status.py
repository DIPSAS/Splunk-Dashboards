#! /usr/bin/python

import sys, getopt, os, json, urllib

scheme="https"
hostname="localhost"
port=""
endpointsPath="endpoints.json"

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
   
def using():
  filename = os.path.realpath(__file__)
  
  print ()
  print ("Usage:")
  print (" ", filename, "[arguments]")
  print ()
  print ("Arguments:")
  print ("  -s | --scheme     The scheme used by the base URL (default: https)")
  print ("  -H | --hostname   Hostname used for the base URL (default: localhost)")
  print ("  -p | --port       The port number used by the base URL (default: no port number used)")
  print ("  -e | --endpoints  Path to endpoints.json - used to define status endpoint (default: ./endpoints.json)")
  print ("  -h | --help       This help text")
  
  sys.exit()

  
def handleCliArgs(argv):
  global scheme
  global hostname
  global port
  global endpointsPath

  try:
    opts, args = getopt.getopt(argv,":s:H:p:e:h",["scheme","hostname","port","endpoints","help"])
    
    for opt, arg in opts:
      if opt == '-h':
        using()
      elif opt in ("-s", "--scheme"):
        scheme = arg
      elif opt in ("-H", "--hostname"):
        hostname = arg
      elif opt in ("-p", "--port"):
        port = arg
      elif opt in ("-e", "--endpoints"):
        endpointsPath = arg 
  
  except getopt.GetoptError as e:
    print ()
    print ("ERROR: The script was not used as intended --", e)
    using() 


def main(argv):
  handleCliArgs(argv)
  
  with open(os.path.join(__location__, endpointsPath), 'r') as f:
    endpoints = json.load(f)
    
  serviceBaseUrl="{0}://{1}".format(scheme, hostname)
  if port != "":
    serviceBaseUrl = serviceBaseUrl + ":" + port
  
  serviceStatuses = []
  for service in endpoints:
    serviceStatus = {"serviceName":service["ServiceName"]}
    for endpoint in service["Endpoints"]:
      if endpoint["EndpointAddress"].endswith("/status/ping"):
        serviceStatus["ping"]={}
        url = serviceBaseUrl + endpoint["EndpointAddress"]
        serviceStatus["ping"]["url"] = url
        ping = urllib.urlopen(url)
        code = ping.getcode()
        contents = ping.read().decode("utf-8")
        serviceStatus["ping"]["statuscode"] = code
        try:
          serviceStatus["ping"]["responce"] = json.loads(contents)
        except ValueError as e:
          serviceStatus["ping"]["responce"] = contents
      if endpoint["EndpointAddress"].endswith("/status/health"):
        serviceStatus["health"]={}
        url = serviceBaseUrl + endpoint["EndpointAddress"]
        serviceStatus["health"]["url"] = url
        health = urllib.urlopen(serviceBaseUrl + endpoint["EndpointAddress"])
        code = health.getcode()
        contents = health.read().decode("utf-8")
        serviceStatus["health"]["statuscode"] = code
        try:
          serviceStatus["health"]["responce"] = json.loads(contents)
        except ValueError as e:
          serviceStatus["health"]["responce"] = contents
    print(json.dumps(serviceStatus))
    serviceStatuses.append(serviceStatus)

if __name__ == "__main__":
   main(sys.argv[1:])