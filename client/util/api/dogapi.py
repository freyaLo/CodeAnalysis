# -*- encoding: utf-8 -*-
""" 与codedog server通信的resful api接口实现
"""

import logging

from urllib.parse import quote
from util.api.httpclient import HttpClient

logger = logging.getLogger(__name__)


class CodeDogHttpClient(HttpClient):
    """封装一层，用来添加特定的http请求头
    """
    def __init__(self, server_url, rel_url, headers=None, data=None, json_data=None, proxies=None):
        HttpClient.__init__(self, server_url, rel_url, headers, data, json_data, proxies)


class CodeDogApiServer(object):
    def __init__(self, token, server_url):

        self._headers = {
            'CONTENT-TYPE': 'application/json',
            'NODE-IDENTITY': '1',
            'Authorization': 'Token %s' % token
        }
        self._server_url = server_url

    def get_data_from_result(self, result):
        """
        Analysis返回格式调整，不具备通用性，需要特殊适配
        """
        if isinstance(result, dict):
            if result.get("data") is not None and result.get("code") is not None \
                    and result.get("status_code") is not None:
                return result["data"]
        return result

    def job_heart_beat(self, job_id):
        """任务心跳上报

        :param job_id: 任务job id
        :return:
        """
        rel_url = "api/jobs/%s/tasksbeat/" % job_id
        CodeDogHttpClient(self._server_url, rel_url, headers=self._headers).post()

    def update_task_progress(self, node_id, job_id, task_id, message, percent):
        """任务进度信息上报

        :param node_id: 节点标识号
        :param job_id: 项目标识号
        :param task_id: 任务标识号
        :param message: str, 进度信息
        :param percent: int, 进度百分比
        :return:
        """
        rel_url = "api/jobs/%s/tasks/%s/progresses/" % (job_id, task_id)
        data = {
            "message": message,
            "progress_rate": percent,
            "task": task_id,
            "node": node_id
        }
        CodeDogHttpClient(self._server_url, rel_url, headers=self._headers, json_data=data).post()

    # ------------------------------------------------------------------------------------- #
    # 格式: ``orgs/<org_sid>/teams/<team_name>/repos/<repo_id>/``
    # ------------------------------------------------------------------------------------- #

    def get_proj_conf(self, org_sid, team_name, repo_id, proj_id):
        """
        获取指定项目的所有任务参数
        :return: 任务参数信息json;无代码更新返回无需扫描
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/projects/{proj_id}/scans/jobconfs/"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers).get()
        return self.get_data_from_result(rsp)

    def init_job(self, repo_id, proj_id, init_data, org_sid, team_name):
        """
        向server初始化一个任务
        :return: {
                    "job": job_id,
                    "scan_id": scan_id,
                    "tasks": {"pylint": task_id1, "cppcheck": task_id2}
                 }
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/projects/{proj_id}/jobs/init/"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers, json_data=init_data).post()
        return self.get_data_from_result(rsp)

    def send_proj_result(self, repo_id, proj_id, job_id, scan_result, org_sid, team_name):
        """
        本地项目扫描完成后,上传结果给server
        :return:
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/projects/{proj_id}/jobs/{job_id}/finish/"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers, json_data=scan_result).post()
        rsp_dict = self.get_data_from_result(rsp)
        try:  # 接口返回值格式修改未上线,先改为兼容模式
            job_id = rsp_dict["job"]
            scan_id = rsp_dict["scan"]
            return job_id, scan_id
        except Exception as err:
            logger.error(f"{rel_url} error: {str(err)}")
            return None, None

    def get_proj_info(self, branch, scan_scheme, repo_id, org_sid, team_name):
        """
        根据扫描方案和scm url查询项目id
        :param scm_url:scm url
        :param scan_scheme:扫描方案
        :param repo_id: 仓库编号
        :param org_sid: 团队编号
        :param team_name: 项目名称
        :return:list,符合条件的项目id列表
        """
        if scan_scheme:
            rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/" \
                      f"projects/?scan_scheme__name={quote(scan_scheme)}&branch={quote(branch)}"
        else:
            rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/" \
                      f"projects/?branch={quote(branch)}&scan_scheme__default_flag=true"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers).get()
        rsp_dict = self.get_data_from_result(rsp)
        if rsp_dict["count"] == 0:
            return []
        else:
            return rsp_dict["results"]

    def create_proj(self, proj_info, org_sid, team_name):
        """
        创建项目
        :param proj_info: dict, 项目信息
        :param org_sid: 团队编号
        :param team_name: 项目名称
        :return: dict, {"project_id": xxx, "project_url": xxx}
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/projects/"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers, json_data=proj_info).post()
        return self.get_data_from_result(rsp)

    def get_default_filtered_paths(self, repo_id, project_id, org_sid, team_name):
        """
        获取项目默认的过滤路径
        :return: 都是exclude过滤，path_type: 1-通配符,2-正则表达式
        """
        path_filters = {
            "inclusion": [],     # 通配符    include
            "exclusion": [],     # 通配符    exclude
            "re_inclusion": [],  # 正则表达式 include
            "re_exclusion": [],  # 正则表达式 exclude
        }
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/defaultpaths/"

        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers).get()
        rsp_list = self.get_data_from_result(rsp)
        for item in rsp_list:
            if item["path_type"] == 1:
                path_filters["exclusion"].append(item["dir_path"])
            elif item["path_type"] == 2:
                path_filters["re_exclusion"].append(item["dir_path"])
        logger.info(f"path_filters: {path_filters}")
        return path_filters

    def get_scan_result(self, project_id, scan_id, repo_id, org_sid, team_name):
        """
        查询scan_id对应的扫描结果
        :return:
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/projects/{project_id}/scans/{scan_id}/"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers).get()
        return self.get_data_from_result(rsp)

    def get_lintscan_result(self, project_id, scan_id=None, scan_revision=None,
                            repo_id=None, org_sid=None, team_name=None):
        """
        通过scan_id或scan_revision获取代码检查的问题统计信息，已根据问题单的实时状态更新
        注意: 只包含按严重级别分类的问题量数据,不包含按问题类型统计的数据(问题类型分类数据暂不统计,以节省server搜索成本,后续需要再加上)
        :return:
        """
        if scan_revision:
            rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/" \
                      f"projects/{project_id}/codelint/issues/summary/?scan_revision={scan_revision}"
        else:
            rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/" \
                      f"projects/{project_id}/codelint/issues/summary/?scan_id={scan_id}"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers).get()
        return self.get_data_from_result(rsp)

    def get_latest_scm_scan(self, proj_id, repo_id, org_sid, team_name):
        """
        获取最新扫描情况(按照scm版本判断的最新一次扫描)
        :return:
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/" \
                  f"projects/{proj_id}/scans/?order_by=-scm_time,result_code&limit=1"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers).get()
        data = self.get_data_from_result(rsp)
        if data["results"]:
            result = data["results"][0]
            return result
        else:
            return None

    # ------------------------------------------------------------------------------------- #
    # 格式: ``orgs/<org_sid>/teams/<team_name>/repos/<repo_id>/projects/<project_id>/``
    # ------------------------------------------------------------------------------------- #

    def get_scan_result_by_revision(self, project_id, revision, repo_id, org_sid, team_name):
        """
        查询当前代码版本对应的扫描结果
        说明: 可能本次扫描没有执行对应的代码检查或代码度量,但是之前扫描过,也会返回结果
        :return:
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/" \
                  f"projects/{project_id}/overview/?scan_revision={revision}"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers).get()
        return self.get_data_from_result(rsp)

    # ------------------------------------------------------------------------------------- #
    # 格式: 其他
    # ------------------------------------------------------------------------------------- #

    def is_repo_existed(self, repo_url, org_sid, team_name):
        """
        判断代码仓库是否存在（即代码库是否在平台上已关联）
        :return:
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/?scm_url={quote(repo_url)}"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers).get()
        # logger.info(f">>>> {type(rsp)} rsp: {rsp}")
        data = self.get_data_from_result(rsp)
        # logger.info(f">>>> {type(data)} rsp: {data}")
        results = data.get("results")
        if results:
            repo_id = results[0]["id"]
            return True, repo_id
        else:
            return False, None

    def create_repo(self, repo_info, org_sid, team_name):
        """
        创建代码库（即在平台上关联代码库）
        :param repo_info:
        :param org_sid:
        :param team_name:
        :return:
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers, json_data=repo_info).post()
        data = self.get_data_from_result(rsp)
        repo_id = data.get("id")
        return repo_id

    def get_repo_schemes(self, repo_id, org_sid, team_name):
        """
        判断分析方案是否存在.(其中，根据 scheme_name 查询分析方案，是模糊匹配)
        scheme_name 和 scheme_template_ids 只能指定一个，如果同时指定，以 scheme_name 为准，忽略 scheme_template_ids
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/schemes/?limit=100"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers).get()
        data = self.get_data_from_result(rsp)
        results = data.get("results")
        return results

    def create_scheme(self, repo_id, scheme_info, org_sid, team_name):
        """
        创建分析方案（即在平台上关联代码库）
        :param repo_id:
        :param scheme_info:
        :param org_sid:
        :param team_name:
        :return:
        """
        rel_url = f"api/orgs/{org_sid}/teams/{team_name}/repos/{repo_id}/schemes/"
        rsp = CodeDogHttpClient(self._server_url, rel_url, headers=self._headers, json_data=scheme_info).post()
        scheme_params = self.get_data_from_result(rsp)
        return scheme_params
