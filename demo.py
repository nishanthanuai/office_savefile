with open("element.html","r") as file:
    data = file.read().strip().split("\n")

res=[]

for line in data:
    if "select" in line:
        continue
    # print(line)
    temp = [i.removeprefix('"') for i in line if i not in "<option value = " "></option>"]
    res.append("".join(temp))
final=[]
for i in sorted(list(res)):
    final.append(i[:int(len(i) / 2)]+",")

import json

with open("demo.json","r") as file:
    prev = json.load(file)


for k in prev["pavement"]["anomalies"].keys():
    if k in []:
        print(k)
