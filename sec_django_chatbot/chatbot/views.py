from django.shortcuts import render, redirect
from django.http import JsonResponse
import openai

from django.contrib import auth
from django.contrib.auth.models import User
from .models import Chat

from django.utils import timezone

from ..secret import openai_api_key

openai.api_key = openai_api_key


def ask_openai(message):
    response = openai.Completion.create(
        model = "text-davinci-003",
        prompt = message,
        max_tokens = 150,
        n=1,
        stop=None,
        temperature=0.7,
    )
    
    answer = response.choices[0].text.strip()
    return answer

# Create your views here.

def chatbot(request):
    #이걸로 chatgpt처럼 이전 채팅이력도 보여줌
    chats = Chat.objects.filter(user=request.user)
    if request.method == "POST":
        message = request.POST.get("message")
        response = ask_openai(message)
        #디비에서 처리할 데이터
        chat = Chat(user=request.user, message=message, response=response, created_at=timezone.now())
        chat.save()
        return JsonResponse({"message": message, "response": response})
    #이걸로 chatgpt처럼 이전 채팅이력도 보여줌: {"chats": chats}
    return render(request, "chatbot.html", {"chats": chats})



def login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        #username check
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
