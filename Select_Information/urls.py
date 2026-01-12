# Select_Information/urls.py
from django.urls import path
from .views import SelectInformationView, StudentChooseProfessorView, ProfessorChooseStudentView, StudentCancelView, GetSelectionTimeView
from .views import SubmitSignatureFileView, ReviewerReviewRecordsView, ReviewRecordUpdateView

app_name = 'Select_Information'

urlpatterns = [
    path('get-select-info/', SelectInformationView.as_view(), name='get-select-info'),
    path('get-select-time/', GetSelectionTimeView.as_view(), name='get-select-time'),
    path('select-professor/', StudentChooseProfessorView.as_view(), name='student-select-professor'),
    path('select-student/', ProfessorChooseStudentView.as_view(), name='professor-select-student'),
    path('student-cancel-select/', StudentCancelView.as_view(), name='student-cancel-select'),
    path('submit-pdf-review/', SubmitSignatureFileView.as_view(), name='submit-pdf-review'),
    path('reviewer/review_records/', ReviewerReviewRecordsView.as_view(), name='reviewer-review-records'),
    # path('reviewer/review_records/', ReviewerReviewRecordsView.as_view(), name='reviewer-review-records'),
    path('reviewer/review_record/<int:pk>/', ReviewRecordUpdateView.as_view(), name='review-record-update'),
]
