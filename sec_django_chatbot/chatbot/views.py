from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
import openai

from django.contrib import auth
from django.contrib.auth.models import User
from .models import Chat

from django.utils import timezone

from secret import openai_api_key

from PyPDF2 import PdfReader
import os
import boto3
import requests


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


def process_all_pdfs_in_bucket(bucket_name):
    s3 = boto3.client('s3')
    response = s3.list_objects_v2(Bucket=bucket_name)

    file_list = []
    for obj in response['Contents']:
        file_key = obj['Key']
        if file_key.lower().endswith('.pdf'):
            file_list.append(file_key)

    for file_key in file_list:
        # S3에서 PDF 파일 다운로드
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        pdf_data = response['Body'].read()

        # Textract 호출 및 결과 반환
        textract = boto3.client('textract')
        response = textract.start_document_text_detection(
            Document={'Bytes': pdf_data}
        )
        job_id = response['JobId']

        # Textract 작업 완료 대기
        waiter = textract.get_waiter('text_detection_complete')
        waiter.wait(JobId=job_id)

        # Textract 결과 가져오기
        response = textract.get_document_text_detection(JobId=job_id)
        text = ''
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                text += item['Text'] + '\n'

        # 추출된 텍스트를 사용하여 후속 작업 수행

        # 작업 결과 출력 또는 저장 등 필요한 작업 수행
        print('Processed file:', file_key)
        print('Extracted text:', text)
        print('---')


# S3 버킷 이름 설정
bucket_name = 'joon-chatbot'

# S3 버킷 내 모든 PDF 파일 처리
process_all_pdfs_in_bucket(bucket_name)

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
