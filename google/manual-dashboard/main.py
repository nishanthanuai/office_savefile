import requests
headers = {
    "Security-Password" :"admin@123" 
}
 
# Making a PATCH request
r = requests.patch('https://ndd.roadathena.com/api/surveys/roads/1022', data ={'latitude':1000},headers=headers)
 

 
# print content of request
print(r.content)