from django.urls import path
from .views import ProfessorAndDepartmentListView, ChangePasswordView, UpdateProfessorView
from .views import LogoutView, UserLoginInfoView, UpdateStudentView, GetStudentResumeListView
from .views import LoginView, ProfessorEnrollInfoView

urlpatterns = [
    # path('userlogin/', UserLoginView.as_view(), name='user-login'),
    # ...其他URL配置...
    path('professors_and_departments/', ProfessorAndDepartmentListView.as_view(), 
         name='professors_and_departments'),
    path('professors-enrollinfo/', ProfessorEnrollInfoView.as_view(), name='professor_enrollinfo'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('update-professor/', UpdateProfessorView.as_view(), name='update_professor'),
    path('update-student/', UpdateStudentView.as_view(), name='update_professor'),
    path('user-logout/', LogoutView.as_view(), name='user_logout'),
    path('user-login/', LoginView.as_view(), name='user_login'),
    # path('upload-avatar/', UploadAvatarView.as_view(), name='upload_avatar'),
    path('user-info/', UserLoginInfoView.as_view(), name='user_info'),
    path('student-resumeinfo/', GetStudentResumeListView.as_view(), name='resumeinfo'),
]
