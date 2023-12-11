from django.urls import path
from . import views
from .views import AdmissionQuotaApprovalView, SubmitQuotaView, DepartmentQuotaApprovalListView, ReviewQuotaApprovalView


app_name = 'Professor_Quota_Review'

urlpatterns = [
    # 添加获取审核信息的 URL
    path('get-admission-approvals/', AdmissionQuotaApprovalView.as_view(), name='get-admission-approvals'),
    path('submit-quota/', SubmitQuotaView.as_view(), name='submit_quota'),
    path('department-quota-approval-list/', DepartmentQuotaApprovalListView.as_view(), 
         name='department-quota-approval-list'),
    path('review-quota-approval/', ReviewQuotaApprovalView.as_view(), name='review-quota-approval'),
    # ... 其他 URL 模式 ...
    path('approve_action/<int:pk>/', views.approve_action, name='approve_action'),
    path('reject_action/<int:pk>/', views.reject_action, name='reject_action'),
]
