#! /usr/bin/python

import sys, getopt, os, json, re
import urllib2

outputFile = "metadata.json"
octoBaseUrl= "https://vd-octopus01.dips.local/"
octoApiKey = "API-4KAS5YEUD5HVJMX4YJ6U8SWJMRW"
envFilter = ""
projectGroupId = "165"

def using():
  filename = os.path.realpath(__file__)
  
  print ()
  print ("Usage:")
  print (" ", filename, "[arguments]")
  print ()
  print ("Arguments:")
  print ("  -h | --help                  This help text")
  print ("  -o | --output-filename       Name of the resulting outputfile - default: " + outputFile)
  print ("  -b | --octopus-base-url      The base URL to octopus - default: " + octoBaseUrl)
  print ("  -k | --octopus-api-key       API key used to fetch data from octopus - default: " + octoApiKey)
  print ("  -k | --octopus-project-group Octopus project group ID used to deploy to env - default: " + projectGroupId)
  print ("  -e | --environment-filter    Filter environments that contain this in name - default: " + envFilter)
  
  sys.exit()
  

def handleCliArgs(argv):
  global octoBaseUrl, envFilter, octoApiKey, projectGroupId, outputFile

  try:
    opts, args = getopt.getopt(argv,":o:b:k:e:p:h",["help","output-filename=","octopus-base-url=","octopus-api-key=","octopus-project-group=","environment-filter="])
    
    for opt, arg in opts:
      if opt in ("-h", "--help"):
        using()
      elif opt in ("-o", "--output-filename"):
        outputFile = arg
      elif opt in ("-b", "--octopus-base-url"):
        octoBaseUrl = arg
      elif opt in ("-k", "--octopus-api-key"):
        octoApiKey = arg
      elif opt in ("-p", "--octopus-project-group"):
        projectGroupId = arg
      elif opt in ("-e", "--environment-filter"):
        envFilter = arg
  
  except getopt.GetoptError as e:
    print ()
    print ("ERROR: The script was not used as intended: ", e)
    using() 


def main(argv):
  handleCliArgs(argv)
  
  metadata = []
  
  environments = getOctoApiData('environments/all')
  projects = []
  
  for id in projectGroupId.split(","):
    projects = projects + getOctoApiData('projectgroups/ProjectGroups-' + id + '/projects?skip=0&take=2147483647')['Items']
  
  for environment in environments:
    if envFilter in environment['Name']:
      # Get generic environment data
      envId = environment['Id']
      environmentData = {
        'name': environment['Name'], 
        'id': envId, 
        'machines': [],
        'projects': [],
        'thirdparty': {}
      }
      
      for project in projects:  
        projectData = {
          'id': project['Id'],
          'name': project['Name'],
          'isDisabled': project['IsDisabled'],
          'projectGroupId': project['ProjectGroupId']
        }
        
        # Get latest deploy data and project ID
        # TODO: add option to provide a project filter (project group??) then fetch the
        #       last deploy pr environment/project combo
        deploys = getOctoApiData("/deployments?environments={0}&projects={1}&take=1".format(envId,project['Id']))
        if len(deploys['Items']) == 0: continue
        deploy = None
        for deployCandidate in deploys['Items']:
          if 'Variables' in deployCandidate['Links']:
            deploy = deployCandidate
            break
        if deploy == None: continue
        
        projectData['lastDeploy'] = deploy['Created']
        # TODO: what if multiple changes?
        if len(deploy['Changes']) > 0:
          projectData['version'] = deploy['Changes'][0]['Version']
        if not 'version' in projectData.keys() or projectData['version'] == "":
          projectData['version'] = "Not found"
          
        # Skip environments that dont have any variables set
        if 'Variables' in deploy['Links']:      
          variables = getOctoApiData(deploy['Links']['Variables'])
          
          # Get thirdparty data from variable set
          thirdparty = {}
          SetThirdPartyValueFromVariables('BIPublisher.HostName', thirdparty, variables)
          SetThirdPartyValueFromVariables('BIPublisher.Port', thirdparty, variables)
          SetThirdPartyValueFromVariables('BIPublisher.Scheme', thirdparty, variables)
          SetThirdPartyValueFromVariables('AMQP.HostName', thirdparty, variables)
          SetThirdPartyValueFromVariables('AMQP.VirtualHost', thirdparty, variables)
          SetThirdPartyValueFromVariables('MQTT.HostName', thirdparty, variables)
          SetThirdPartyValueFromVariables('MQTT.VirtualHost', thirdparty, variables)
          SetThirdPartyValueFromVariables('ZookeeperHostName', thirdparty, variables)
          projectData['thirdparty'] = thirdparty
          UpdateThirdpartyIfMainDeploy(environmentData, thirdparty, variables)
          
          # Get Arena Version
          # SetThirdPartyValueFromVariables('ArenaVersion', projectData['lastDeploy'], variables)
          # projectData['ArenaVersion'] = GetArenaVersionFromClientConfig(variables);
          projectData['ArenaVersion'] = GetArenaVersionFromClientConfig(variables)
          projectData['ClassicVersion'] = GetClassicVersionFromClientConfig(variables)
          projectData['Database'] = GetDatabaseFromClientConfig(variables)
          
        environmentData['projects'].append(projectData)
      
      # Get machine info
      machines = getOctoApiData("environments/" + envId + "/machines")
      
      # TODO: handle multiple pages for machines 
      # (only a problem if > 20 machines configured for env)
      if machines['NumberOfPages'] > 1:
        sys.stderr.write("Not all machines for " + envId + " was fetched")
      for machine in machines['Items']:
        uri = machine['Uri']
        machineData = {
          'name': machine['Name'],
          'uri': uri,
          'isDisabled': machine['IsDisabled'],
          'verifiableServiceEndpoints': []
        }
        
        if machine['IsDisabled'] or not uri:
          environmentData['machines'].append(machineData)
          continue
        
        machineData['apiUri'] = (uri[:uri.rindex(':')] + ":1337/api/").replace("https", "http")
        try:
          req = urllib2.Request(machineData['apiUri'] + "verifiableServiceEndpoints")
          machineData['verifiableServiceEndpoints'] = json.loads(urllib2.urlopen(req).read().decode("utf-8"))
        except:
          machineData['verifiableServiceEndpoints'] = []
            
        environmentData['machines'].append(machineData)
      
      # Append environment data to metadata
      metadata.append(environmentData)
      
  with open(os.path.dirname(os.path.abspath(__file__))+'\\'+outputFile, 'w') as outfile:
    json.dump(metadata, outfile, indent=2)


def getOctoApiData(endpoint):
  if endpoint.startswith("/api/"):
    endpoint = endpoint[5:]
  if endpoint.startswith("api/"):
    endpoint = endpoint[4:]
    
  octo_headers = {'X-Octopus-ApiKey': octoApiKey}
  req = urllib2.Request(octoBaseUrl + "/api/" + endpoint, headers=octo_headers)
  return json.loads(urllib2.urlopen(req).read().decode("utf-8"))  


def SetThirdPartyValueFromVariables(value, thirdparty, variables):
  for variable in variables['Variables']:
    if variable['Name'] == value:
      thirdparty[value] = variable['Value']
      return
      
      
def UpdateThirdpartyIfMainDeploy(environmentData, thirdparty, variables):
  for variable in variables['Variables']:
    if variable['Name'] == 'Client.SelectedDeliveryConfigurations':
      reg = re.search(r"client:arena-\d+(\.\d+)+", variable['Value'])
      if reg is not None:
        environmentData['thirdparty'] = thirdparty
    if variable['Name'] == 'Service.SelectedDeliveryConfigurations':
      reg = re.search(r"service:arena-\d+(\.\d+)+", variable['Value'])
      if reg is not None:
        environmentData['thirdparty'] = thirdparty
      
      
def GetArenaVersionFromClientConfig(variables):
  for variable in variables['Variables']:
    if variable['Name'] == 'Client.SelectedDeliveryConfigurations':
      reg = re.search(r"client:arena-\d+(\.\d+)+", variable['Value'])
      if reg is not None:
        return reg.group()[13:]
    if variable['Name'] == 'Service.SelectedDeliveryConfigurations':
      reg = re.search(r"service:arena-\d+(\.\d+)+", variable['Value'])
      if reg is not None:
        return reg.group()[14:]
  for variable in variables['Variables']:
    if variable['Name'] == 'ArenaVersion':
      return variable['Value']
  
  return ""
  
  
def GetClassicVersionFromClientConfig(variables):
  for variable in variables['Variables']:
    if variable['Name'] == 'Client.SelectedDeliveryConfigurations':
      reg = re.search(r"client:classic-\d+(\.\d+)+", variable['Value'])
      if reg is not None:
        return reg.group()[15:]
  return ""
  
  
def GetDatabaseFromClientConfig(variables):
  host = ""
  sid = ""
  for variable in variables['Variables']:
    if variable['Name'] == 'Database.HostName':
      host = variable['Value']
    if variable['Name'] == 'Database.SID':
      sid = variable['Value']
    if sid != "" and host != "":
      return host + '/' + sid
  return ""
    

if __name__ == "__main__":
   main(sys.argv[1:])