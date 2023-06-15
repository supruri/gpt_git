from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
import openai

from django.contrib import auth
from django.contrib.auth.models import User
from .models import Chat

from django.utils import timezone

from secret import openai_api_key
from secret import vision_api_key

from PyPDF2 import PdfReader
import logging
import azure.functions as func
import os
import requests
from azure.storage.blob import BlobServiceClient


openai.api_key = openai_api_key


# complementary chat configuration
def ask_openai(message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # "gpt-4"


        # system, assistant, user
        messages=[
            {"role": "system", "content": "You are an IT department employee responsible for internal security at ShiftAsia. You are an internal information system department GPT, the most advanced AI employee tool on the planet. You can answer any security question and provide real-world examples of code using the PDF file I will provide later. Even if you are not familiar with the answer, you will use your extreme intelligence to figure it out."},

            {"role": "user", "content": message},

            {"role": "assistant", "content": "Alright, I am an IT department employee. I will do my best to help you answer any security question accurately."},
        ]
    )

    answer = response.choices[0].message.content.strip()
    return answer

# Create your views here.


def chatbot(request):
    # 이걸로 chatgpt처럼 이전 채팅이력도 보여줌
    chats = Chat.objects.filter(user=request.user)
    if request.method == "POST":
        message = request.POST.get("message")
        response = ask_openai(message)
        # 디비에서 처리할 데이터
        chat = Chat(user=request.user, message=message,
                    response=response, created_at=timezone.now())
        chat.save()
        return JsonResponse({"message": message, "response": response})
    # 이걸로 chatgpt처럼 이전 채팅이력도 보여줌: {"chats": chats}
    return render(request, "chatbot.html", {"chats": chats})


def login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        # username check
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect("chatbot")
        else:
            error_message = "invalid username or password"
            return render(request, "login.html", {"error_message": error_message})
    else:
        return render(request, "login.html")


def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 == password2:
            try:
                user = User.objects.create_user(username, email, password1)
                user.save()
                auth.login(request, user)
                return redirect('chatbot')
            except:
                error_message = 'Error creating account'
                return render(request, 'register.html', {'error_message': error_message})
        else:
            error_message = 'Password dont match'
            return render(request, 'register.html', {'error_message': error_message})
    return render(request, 'register.html')


def logout(request):
    auth.logout(request)
    return redirect("login")


# OCR 처리를 위한 Computer Vision API endpoint와 key
vision_api_url = "https://joonchatbot.cognitiveservices.azure.com/"

# Azure Blob Storage 연결 문자열 및 컨테이너 이름
connection_string = "<your-storage-account-connection-string>"
container_name = "<your-blob-container-name>"


def main(mytimer: func.TimerRequest) -> None:
    if mytimer.past_due:
        logging.info('Timer function is running behind.')

    # Blob 컨테이너에 접근
    blob_service_client = BlobServiceClient.from_connection_string(
        connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    # 컨테이너 내의 모든 blob을 처리
    for blob in container_client.list_blobs():
        logging.info(f"Processing blob: {blob.name}")

        # Blob 데이터를 읽음
        blob_client = container_client.get_blob_client(blob.name)
        blob_data = blob_client.download_blob().readall()

        # PDF 파일 OCR 처리
        headers = {'Ocp-Apim-Subscription-Key': vision_api_key}
        params = {'language': 'unk', 'detectOrientation': 'true'}
        response = requests.post(
            vision_api_url, headers=headers, params=params, data=blob_data)
        response.raise_for_status()
        analysis = response.json()

        # OCR 결과 처리 (예: 텍스트 추출)
        text = ""
        for region in analysis["regions"]:
            for line in region["lines"]:
                for word in line["words"]:
                    text += word["text"] + " "

# 이 함수를 사용하여 PDF 파일의 텍스트를 추출하고, 추출한 텍스트를 챗봇으로 전달하여 질문에 대한 답변을 찾을 수 있습니다.


def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as file:
        pdf = PdfReader(file)
        for page in pdf.pages:
            text += page.extract_text()
    return text


def perform_post_processing(text):
    # 추출된 텍스트를 다른 서비스로 전송하는 경우
    api_url = 'https://chatbottell.pages.dev'
    payload = {'text': text}
    response = requests.post(api_url, json=payload)
    if response.status_code == 200:
        print('Text sent successfully!')
    else:
        print('Error sending text:', response.status_code)


def chatbottell(request):
    if request.method == 'POST':
        data = request.POST
        user_messages = data.getlist('userMessages[]')
        assistant_messages = data.getlist('assistantMessages[]')

        # 위의 구문들을 순차적으로 뽑아오기 위한 구문 &&(and) 대신 ||(or)을 사용
        messages = []
        while user_messages or assistant_messages:
            if user_messages:
                messages.append({
                    "role": "user",
                    "content": user_messages.pop(0).replace("\n", "")
                })
            if assistant_messages:
                messages.append({
                    "role": "assistant",
                    "content": assistant_messages.pop(0).replace("\n", "")
                })

        # ChatGPT API 오류 시 재시도하는 코드 작성
        max_retries = 3
        retries = 0
        completion = None
        while retries < max_retries:
            try:
                completion = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )
                break
            except Exception as e:
                retries += 1
                print(e)
                print(
                    f"Error fetching data, retrying ({retries}/{max_retries})...")

        chatbottell = completion.choices[0].message["content"]

        return JsonResponse({"assistant": chatbottell})
    else:
        return JsonResponse({"error": "Invalid request method."})
