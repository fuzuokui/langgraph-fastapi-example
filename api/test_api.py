import requests
import json

user_input = input("请输入：")


url = "http://127.0.0.1:8000/AIchat"

data = {
    "user_input": f"{user_input}"
}

# 发送post请求
response = requests.post(url, json=data)
if response.status_code == 200:
    print("响应成功")
    print(response.json()['ai_reply'])
else:
    print("请求失败")