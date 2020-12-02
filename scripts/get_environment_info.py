#! /usr/bin/python

import sys, getopt, os, json, traceback, ssl
import urllib2
from urllib2 import HTTPError
from urllib2 import URLError
import platform    # For getting the operating system name
import subprocess  # For executing a shell command

metadataFile='metadata.json'
   
def using():
  filename = os.path.realpath(__file__)
  
  print ()
  print ('Usage:')
  print (' ', filename, '[arguments]')
  print ()
  print ('Arguments:')
  print ('  -m | --metadata  Path to endpoints.json - used to define status endpoint - default: ' + metadataFile)
  print ('  -h | --help       This help text')
  
  sys.exit()

  
def handleCliArgs(argv):
  global metadataFile

  try:
    opts, args = getopt.getopt(argv,':m:h',['metadata','help'])
    
    for opt, arg in opts:
      if opt in ('-h', '--help'):
        using()
      elif opt in ('-m', '--metadata'):
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
    environmentInfo = {
      'environment': {
        'name': env['name'],
        'projects': []
      }
    }
    
    for project in env['projects']:
      if not project['isDisabled']:
        environmentInfo['environment']['projects'].append(project)

    print(json.dumps(environmentInfo))
  

if __name__ == '__main__':
   main(sys.argv[1:])