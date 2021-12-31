# -*- coding: utf-8 -*-
"""
util - fileserver
"""
import os
import copy
import uuid
import hashlib
import logging
import urllib.parse

from django.conf import settings

from util import errcode
from util.genkey import gen_path_key
from util.retrylib import RetryDecor
from util.httpclient import HttpClient
from util.exceptions import ServerError

logger = logging.getLogger(__name__)


class FileServer(object):
    """文件服务器
    """

    class TypeEnum(object):
        TEMPORARY = "server_temp"
        BUSINESS = "server_business"

        @classmethod
        def values(cls):
            l = []
            for v in dir(cls):
                if v.isupper():
                    l.append(getattr(cls, v))
            return l

    OK_STATUS = 200

    def __init__(self, server_conf):
        self._http_client = HttpClient()
        self._server_url = server_conf["URL"]
        self._server_token = server_conf["TOKEN"]
        self._type_prefix = server_conf["TYPE_PREFIX"]
        self._headers = {'Authorization': 'Token %s' % self._server_token}

    @classmethod
    def get_data_md5(cls, data):
        """获取指定数据的md5
        """
        md5_val = hashlib.md5()
        md5_val.update(data.encode("utf-8"))
        return md5_val.hexdigest()

    @classmethod
    def get_data_sha256(cls, data):
        """获取指定数据的sha256
        """
        sha256_val = hashlib.sha256()
        sha256_val.update(data.encode("utf-8"))
        return sha256_val.hexdigest()

    @RetryDecor()
    def put_file(self, data, to_file_url_or_path=None, type=TypeEnum.TEMPORARY):
        """将指定数据存储到文件服务器的指定路径下
        :params data: 需要上传的数据
        :type data: string
        :params to_file_url_or_path: 可以指定上传到指定路径，如已存在，则更新该文件，为空则由系统创建随机命名文件
        :type to_file_url_or_path: string
        :params type: 仅在to_file_url_or_path为路径时有效
        :type type: FileServer.TypeEnum
        :return: file_url：文件服务器指定的路径
        """
        if type not in self.TypeEnum.values():
            raise ValueError("type参数错误。支持的类型：%s" % self.TypeEnum.values())
        if to_file_url_or_path:
            file_url = to_file_url_or_path if to_file_url_or_path.startswith(self._server_url) \
                else urllib.parse.urljoin(self._server_url, "%s_%s/%s" % (self._type_prefix, type, to_file_url_or_path))
        else:
            # 无命名文件默认上传到临时文件夹，数据保留7天
            file_url = urllib.parse.urljoin(self._server_url, "%s_%s/unnamed/%s.file" % (
                self._type_prefix, self.TypeEnum.TEMPORARY, uuid.uuid1().hex))
        headers = copy.copy(self._headers)
        headers.update({"Content-SHA256": self.get_data_sha256(data), "Content-MD5": self.get_data_md5(data)})
        rsp = self._http_client.put(file_url, data=data, headers=headers)
        if rsp.status == self.OK_STATUS:
            return file_url
        else:
            raise ServerError(errcode.E_SERVER_FILE_SERVICE_ERROR,
                              'return code %d when put file to %s' % (rsp.status, file_url))

    @RetryDecor()
    def get_file(self, file_url):
        """获取指定路径文件数据，返回该文件的路径信息"""
        try:
            rsp = self._http_client.get(file_url, headers=self._headers)
        except Exception as err:
            raise ServerError(errcode.E_SERVER_FILE_SERVICE_ERROR, ' get file exception: %s' % err)
        if rsp.status == self.OK_STATUS:
            return rsp.data
        else:
            raise ServerError(errcode.E_SERVER_FILE_SERVICE_ERROR,
                              'return code %d when get file %s' % (rsp.status, file_url))

    def delete_file(self, file_url):
        """删除指定路径文件"""
        rsp = self._http_client.delete(file_url, headers=self._headers)
        if rsp.status == self.OK_STATUS:
            return True
        else:
            raise ServerError(errcode.E_SERVER_FILE_SERVICE_ERROR,
                              'return code %d when delete file %s' % (rsp.status, file_url))

    @RetryDecor()
    def download_file(self, file_url):
        """下载指定路径文件"""
        file_name = os.path.basename(file_url)
        dir_path = os.path.join(settings.BASE_DIR, 'tempdata', gen_path_key(file_url))
        file_path = os.path.join(dir_path, file_name)
        logger.info("Downloading file from %s to %s", file_url, file_path)
        if os.path.exists(file_path):
            logger.info("File already exists, remove...: %s" % file_path)
            os.remove(file_path)
        try:
            rsp = self._http_client.get(file_url, headers=self._headers, stream=True)
        except Exception as err:
            raise ServerError(errcode.E_SERVER_FILE_SERVICE_ERROR, ' download file exception: %s' % err)
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        with open(file_path, 'wb') as to_file:
            while True:
                chunk = rsp.read(2048)
                if not chunk:
                    break
                to_file.write(chunk)
        rsp.release_conn()
        logger.info("Downloaded file from %s to %s", file_url, file_path)
        return file_path


file_server = FileServer(settings.FILE_SERVER)