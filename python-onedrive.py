import os
import msal
import glob
import json
import time
import requests

def handleToken(client_id, client_secret, scopes):
    
    absPath = os.path.dirname(os.path.abspath(__file__))
    cachePath = f"{absPath}\\\\cache/tokenCache.json"

    if not os.path.isfile(cachePath):
        print("No Token File found, making one and logging in...")
        os.makedirs(os.path.dirname(cachePath), exist_ok=True)
        with open(cachePath, 'w', encoding="utf-8") as cache:
            tokenDictionary = GetAcccessToken(client_id, client_secret, scopes)
            tokenData = {
                'accessToken': {
                    'token': tokenDictionary['access_token'],
                    'expire': round(time.time()) + int(tokenDictionary['expires_in']),
                    'otherTokenData': tokenDictionary
                }
            }
            json.dump(tokenData, cache, indent=2)
            return [tokenDictionary['access_token']]
    else:
        with open(cachePath, 'r+', encoding="utf-8") as cache:
            cacheData = json.loads(cache.read())
            if int(cacheData['accessToken']['expire']) < int(time.time()):
                print("Cache token expired, generating a new one...")
                tokenDictionary = GetAcccessToken(client_id, client_secret, scopes)
                tokenData = {
                    'accessToken': {
                        'token': tokenDictionary['access_token'],
                        'expire': round(time.time()) + int(tokenDictionary['expires_in']),
                        'otherTokenData': tokenDictionary
                    }
                }
                cache.seek(0)
                cache.truncate()
                json.dump(tokenData, cache, indent=2)
                return [tokenDictionary['access_token']]
        
            else:
                print("Using the Cached token...")
                return [cacheData['accessToken']['token']]

def GetAcccessToken(client_id, client_secret, scopes):

    client = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
    )

    authorization_url = client.get_authorization_request_url(scopes)
    print(f"\nAuthorization Url: {str(authorization_url)}")
    authorization_code = input("Copy the above link, and enter the code from URL: ")
    access_token = client.acquire_token_by_authorization_code(
        code=authorization_code,
        scopes=scopes
    )
    return access_token


def createFolder(folderName, accessToken, remoteFolderPath, BASE_ENDPOINT):
    folder_url = BASE_ENDPOINT + '/me/drive/root:/' + remoteFolderPath + ':/children'
    folderReq = requests.post(
        url = folder_url,
        headers = {
            'Authorization': f'Bearer {accessToken}',
        },
        json = {
            "name": folderName,
            "folder": { },
            "@microsoft.graph.conflictBehavior": "rename"
        }
    ).json()

    if not 'createdBy' in folderReq:
        print(f"Unable to create folder in drive location {remoteFolderPath}")
        print(folderReq)
        exit()
    
    return folderReq['id']


def upload(filePath, accessToken, folder_id, BASE_ENDPOINT):

    fileName = str(os.path.basename(filePath))
    # url = BASE_ENDPOINT + f'/me/drive/items/root:/{remoteFolderPath}/{fileName}:/createUploadSession'
    url = BASE_ENDPOINT + f'/me/drive/items/{folder_id}:/{fileName}:/createUploadSession'
    
    # Creating Upload Session
    uploadSession = requests.post(
        url = url,
        headers = {
            'Authorization': f'Bearer {accessToken}',
        },
    )
    if 'uploadUrl' not in uploadSession.json():
        print(uploadSession.content.decode())
        print("Error creating Upload Session")
        exit()

    uploadUrl = uploadSession.json()['uploadUrl']

    # Preparing Data to upload
    totalFileSize = os.path.getsize(filePath)
    chunkSize = 327680 * 300 # 91 MB
    totalChunks = totalFileSize // chunkSize
    leftoverChunk = totalFileSize - (totalChunks * chunkSize)
    counter = 0

    start_time = time.time()
    with open(filePath, 'rb') as data:
        while True:
            chunkData = data.read(chunkSize)
            startIndex = counter * chunkSize
            endIndex = startIndex + chunkSize

            if not chunkData:
                break
            if counter == totalChunks:
                endIndex = startIndex + leftoverChunk
            
            uploadHeaders = {
                'Content-Length': f'{chunkSize}',
                'Content-Range': f'bytes {startIndex}-{endIndex-1}/{totalFileSize}'
            }

            # Uploading Data
            uploadReq = requests.put(
                uploadUrl,
                headers = uploadHeaders,
                data = chunkData
            )

            if 'createdBy' in uploadReq.json():
                print('File Uploaded Successfully.')
            else:
                # print(f"Upload Progress: {uploadReq.json()['nextExpectedRanges']}")
                counter += 1
    print(f"File Size: {str(totalFileSize/1048576)} MB, Upload Time: {round(int(time.time() - start_time))}")
    return 

def cancelUpload(uploadUrl):
    requests.delete(uploadUrl)
    return


CLIENT_SECRET = 'SAQ8Q~z.m5tFNjZDfXi1XaTPSmMPeb0tl00v-aGE'
CLIENT_ID = '9104ea49-9689-4f3c-8819-da1b156b9edf'
SCOPES = ['User.Read', 'Files.ReadWrite.All']
files = []

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
remoteFolderPath = 'temp' # No '/' at the end or beginning of the path. Must include proper path from root (excluded)

accessToken = handleToken(CLIENT_ID, CLIENT_SECRET, SCOPES)[0]
# accessToken = input("Enter AccessToken: ")

# print(f'Access_Token: {accessToken}')

path = str(input("\n\nEnter File Path to upload: "))

if os.path.isfile(path):
    files.append(path)
elif os.path.isdir(path):
    for file in glob.glob(f'{path}/*.*'):
        files.append(file)
else:
    print(f"Unknown Directory Provided: {path}")
    exit()

# Creating Folder on Drive
if len(files) != 1:
    folderId = createFolder(str(os.path.basename(path)), accessToken, remoteFolderPath, GRAPH_API_ENDPOINT)
else:
    folderName = os.path.splitext(str(os.path.basename(files[0])))[0]
    folderId = createFolder(folderName, accessToken, remoteFolderPath, GRAPH_API_ENDPOINT)

# Uploading all files one by one
print("Total items to upload: "+str(len(files))+"\n")
for file in files:
    print(f"Uploading: {os.path.basename(file)}...", end=" ")
    upload(file, accessToken, folderId, GRAPH_API_ENDPOINT)