from celery import shared_task
from celery.utils.log import get_task_logger
import requests
from django.core.cache import cache

logger = get_task_logger(__name__)

@shared_task
def request_access_token():
    logger.info("Requesting access token...")
    print("请求一次access_token的代码")
    # 例如:

    # 定义请求URL和参数
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": "wxa67ae78c4f1f6275",
        "secret": "7241b1950145a193f15b3584d50f3989"
    }

    # 发送GET请求
    response = requests.get(url, params=params)

    # 检查响应状态码
    if response.status_code == 200:
        # 解析响应内容获取access_token
        data = response.json()
        access_token = data.get('access_token')
        
        if access_token:
            logger.info(f"Received access token: {access_token}")
            
            # 将token保存到缓存中，假设token有效期为3600秒
            cache.set('access_token', access_token, timeout=3600)
        else:
            logger.error(f"Failed to retrieve access token: {data}")
    else:
        logger.error(f"Request failed with status code {response.status_code}")