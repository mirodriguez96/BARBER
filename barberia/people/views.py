from django.http import HttpResponse


def index(request):
    return HttpResponse("People module ready")
