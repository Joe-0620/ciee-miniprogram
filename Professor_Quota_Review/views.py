from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from .models import AdmissionQuotaApproval
from django.utils import timezone
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import AdmissionQuotaApprovalSerializer, DepartmentProfessorSerializer
from rest_framework.permissions import IsAuthenticated
from Professor_Student_Manage.models import Professor
from math import isnan


def approve_action(request, pk):
    approval = get_object_or_404(AdmissionQuotaApproval, pk=pk)

    # 更新审核状态和审核时间
    approval.status = '1'
    approval.reviewed_time = timezone.now()
    approval.save()

    # 更新相关导师（Professor）的 proposed_quota_approved 状态
    professor = approval.professor
    professor.proposed_quota_approved = True
    professor.academic_quota = approval.academic_quota
    professor.professional_quota = approval.professional_quota
    professor.professional_yt_quota = approval.professional_yt_quota
    professor.doctor_quota = approval.doctor_quota
    
    professor.save()

    return HttpResponseRedirect(reverse('admin:Professor_Quota_Review_admissionquotaapproval_changelist'))
    # return HttpResponse('审核成功')

def reject_action(request, pk):
    approval = get_object_or_404(AdmissionQuotaApproval, pk=pk)

    # 更新审核状态和审核时间
    approval.status = '2'
    approval.reviewed_time = timezone.now()
    approval.save()

    return HttpResponseRedirect(reverse('admin:Professor_Quota_Review_admissionquotaapproval_changelist'))


# 获取审核信息
class AdmissionQuotaApprovalView(APIView):
    permission_classes = [IsAuthenticated]  # 添加 IsAuthenticated 权限类

    def get(self, request):
        try:
            # 获取当前导师身份
            professor = request.user.professor

            # 查询该 professor 的 AdmissionQuotaApproval 信息
            approvals = AdmissionQuotaApproval.objects.filter(professor=professor)

            # 序列化查询结果
            serializer = AdmissionQuotaApprovalSerializer(approvals, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# 提交审核信息
class SubmitQuotaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # 获取当前导师身份
            professor = request.user.professor

            # 检查是否已经存在等待审核的信息
            existing_pending_approval = AdmissionQuotaApproval.objects.filter(
                professor=professor, status='0').exists()

            if existing_pending_approval:
                return Response({'error': '您已经有正在等待审核的信息'}, 
                                status=status.HTTP_401_BAD_REQUEST)
            
            existing_approval = AdmissionQuotaApproval.objects.filter(
                professor=professor, status='1').exists()
            
            if existing_approval:
                return Response({'error': '您已经通过审核的信息'}, 
                                status=status.HTTP_400_BAD_REQUEST)

            # 如果没有等待审核的信息，则可以创建新的 AdmissionQuotaApproval 对象
            academic_quota = request.data.get('academic_quota')
            professional_quota = request.data.get('professional_quota')
            professional_yt_quota = request.data.get('professional_yt_quota')
            doctor_quota = request.data.get('doctor_quota')

            # 检查数据是否包含NaN值，如果包含，将其替换为0
            if isnan(academic_quota):
                academic_quota = 0
            if isnan(professional_quota):
                professional_quota = 0
            if isnan(professional_yt_quota):
                professional_yt_quota = 0
            if isnan(doctor_quota):
                doctor_quota = 0

            if (academic_quota != 0 or professional_quota != 0 or professional_yt_quota != 0 or doctor_quota != 0):
                approval = AdmissionQuotaApproval.objects.create(
                    professor=professor,
                    academic_quota=academic_quota,
                    professional_quota=professional_quota,
                    professional_yt_quota=professional_yt_quota,
                    doctor_quota=doctor_quota,
                    status='0'  # 设置为等待审核状态
                )
            # 若已审核，返回400
            return Response({'message': '审核信息已提交'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# 负责人获取审核信息
class DepartmentQuotaApprovalListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # 获取当前导师身份
            professor = request.user.professor

            if professor.department_position in [1, 2]:
                # 获取同属方向的其他导师
                department_professors = Professor.objects.filter(department=professor.department)

                # 获取该方向所提交的等待指标审核名单信息
                wait_approvals = AdmissionQuotaApproval.objects.filter(
                    professor__in=department_professors, status='0')
                
                # 获取该方向所提交的通过指标审核名单信息
                agree_approvals = AdmissionQuotaApproval.objects.filter(
                    professor__in=department_professors, status='1')
                
                # 获取该方向所提交的拒绝指标审核名单信息
                reject_approvals = AdmissionQuotaApproval.objects.filter(
                    professor__in=department_professors, status='2')
                

                # 序列化查询结果
                department_professors_serializer = DepartmentProfessorSerializer(department_professors, many=True)
                wait_serializer = AdmissionQuotaApprovalSerializer(wait_approvals, many=True)
                agree_serializer = AdmissionQuotaApprovalSerializer(agree_approvals, many=True)
                reject_serializer = AdmissionQuotaApprovalSerializer(reject_approvals, many=True)


                return Response({'wait_approvals': wait_serializer.data,
                                'agree_approvals': agree_serializer.data,
                                'reject_approvals': reject_serializer.data,
                                'professor_info': department_professors_serializer.data},
                                status=status.HTTP_200_OK)
            else:
                return Response({'error': '非方向负责人，拒绝访问'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

# 审核操作API接口
class ReviewQuotaApprovalView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # 获取当前导师身份
            professor = request.user.professor

            # 获取请求中的审核操作和审核信息ID
            approval_id = request.data.get('approval_id')
            review_action = request.data.get('review_action')  # 'approve' 或 'reject'

            # 查询要审核的信息
            approval = AdmissionQuotaApproval.objects.get(pk=approval_id)

            # 执行审核操作
            if review_action == 'approve':
                approval.status = '1'  # 设置为已审核通过

                approval.reviewed_by = professor
                approval.reviewed_time = timezone.now()
                approval.save()

                wait_professor = approval.professor
                wait_professor.academic_quota = approval.academic_quota
                wait_professor.professional_quota = approval.professional_quota
                wait_professor.professional_yt_quota = approval.professional_yt_quota
                wait_professor.doctor_quota = approval.doctor_quota
                wait_professor.save()

                
            elif review_action == 'reject':
                approval.status = '2'  # 设置为已审核拒绝
                approval.reviewed_by = professor
                approval.reviewed_time = timezone.now()
                approval.save()
            else:
                return Response({'error': '无效的审核操作'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'message': '审核操作成功'}, status=status.HTTP_200_OK)
        except AdmissionQuotaApproval.DoesNotExist:
            return Response({'error': '审核信息不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)