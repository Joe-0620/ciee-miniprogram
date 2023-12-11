import json
import logging

from django.http import JsonResponse
from django.shortcuts import render


logger = logging.getLogger('log')

def index(request):
    return render(request, 'index.html')