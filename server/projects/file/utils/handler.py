# -*- coding: utf-8 -*-
"""
通用管理 请求异常处理
"""

import base64
import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.status import HTTP_500_INTERNAL_SERVER_ERROR

from utils.error import QFSRequestError, ERROR_CODE


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, content):
    """自定义异常处理
    """
    logger.exception(exc)
    if isinstance(exc, QFSRequestError):
        err_msg = exc.detail
        logger.exception("[QFSRequestError][Err: %s] msg: %s" % (exc.code, err_msg))
        err_msg = base64.b64encode(str(err_msg).encode("utf-8"))
        response = Response({'Err-type': exc.code, 'Err-msg': err_msg})
        response.status_code = ERROR_CODE.get(exc.code, HTTP_500_INTERNAL_SERVER_ERROR)
        return response
    return exception_handler(exc, content)
