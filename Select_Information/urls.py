from django.urls import path
from .views import SelectInformationView, StudentChooseProfessorView, ProfessorChooseStudentView, StudentCancelView

app_name = 'Select_Information'

urlpatterns = [
    path('get-select-info/', SelectInformationView.as_view(), name='get-select-info'),
    path('select-professor/', StudentChooseProfessorView.as_view(), name='student-select-professor'),
    path('select-student/', ProfessorChooseStudentView.as_view(), name='professor-select-student'),
    path('student-cancel-select/', StudentCancelView.as_view(), name='student-cancel-select'),
]
