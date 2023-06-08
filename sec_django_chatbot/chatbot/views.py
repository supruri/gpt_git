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

openai.api_key = openai_api_key


# complementary chat configuration
def ask_openai(message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",


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


# 여러 PDF파일이 보관되어 있는 폴더의 주소를 입력하면 폴더 내 모든 PDF를 읽어오게 하려고 폴더의 주소를 사용자에게 입력받고, 폴더 내에 있는 모든 PDF 파일의 주소를 f_list 에 저장한다.


def save_file_list(path):
    file_list = []
    for root, dirs, files in os.walk(path):
        for file_name in files:
            if file_name[-4:] == '.pdf':
                file_list.append(root+'/'+file_name)
    return file_list

# 이 함수를 사용하여 PDF 파일의 텍스트를 추출하고, 추출한 텍스트를 챗봇으로 전달하여 질문에 대한 답변을 찾을 수 있습니다.


def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as file:
        pdf = PdfReader(file)
        for page in pdf.pages:
            text += page.extract_text()
    return text

# Select GPT Model
# while True:
#     GPT_model = input(
#         "Select a GPT Model\n• text-davinci-003 : Fast, Moderate Quality results\n• gpt-4 : Slow, Great Quality results\n>> ").strip()
#     if GPT_model != 'text-davinci-003' and GPT_model != 'gpt-4':
#         print("Type the name of the model correctly\n")
#     else:
#         break


# Input folder directory
file_path = input("Enter folder directory for PDFs >> ").strip()
f_list = save_file_list(file_path)
print(f'Total of {len(f_list)} PDFs')

for i in range(len(f_list)):
    # Initialize texts string
    texts = ''

    # Initialize answer string
    ans = ''

    # Fetch file directory from file list array
    f_dir = f_list[i]

    # # Set output location, name
    # output = file_path + '/' + \
    #     os.path.splitext(os.path.basename(f_dir))[0] + '_GPTAnswer' + ".txt"

    # # Read PDF and save answer
    # with open(f_dir, "rb") as f:
    #     pdf_reader = PdfReader(f)
    #     for page in pdf_reader.pages:
    #         texts += page.extract_text()

    # print(f'PDF #{i + 1} Solving...')
    # ans = ask_openai(texts)

    # # Write answer to txt file
    # with open(output, "w", encoding='utf-8') as file:
    #     try:
    #         file.write(ans+"\n")
    #     except UnicodeEncodeError:
    #         print(f'PDF #{i+1} Error!')
    #         continue

    # print(f'PDF #{i+1} Complete!')
