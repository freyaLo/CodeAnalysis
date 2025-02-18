/**
 * 公共请求
 */
import { get, put, post, del } from './index';

export const MAIN_SERVER = '/server/main/';
export const MAIN_SERVER_API = '/server/main/api/v3';
export const ANALYSIS_SERVER_API = '/server/analysis/api/v3';
export const ANALYSIS_SERVER_CODEDOG_API = '/api/codedog/analysis/v3/';
export const LOGIN_SERVER_API = '/server/credential/api/v3';

export const getBaseURL = (org_sid: string, team_name: string) => `/orgs/${org_sid}/teams/${team_name}`;

export const getMainBaseURL = (org_sid: string, team_name: string) => `${MAIN_SERVER_API}${getBaseURL(org_sid, team_name)}`;

export const getAnalysisBaseURL = (org_sid: string, team_name: string) => `${ANALYSIS_SERVER_API}${getBaseURL(org_sid, team_name)}`;


/**
 * 获取代码库列表
 * @param query
 */
export const getRepos = (org_sid: string, team_name: string, query: any) => get(`${MAIN_SERVER_API}/orgs/${org_sid}/teams/${team_name}/repos/`, { ...query, scope: 'all' });

/**
 * 根据用户UID获取用户信息
 * @param uid
 */
export const getUIDUserInfo = (uid: string) => get(`${LOGIN_SERVER_API}/login/users/${uid}/`);

/*
 * 获取指定代码库下的成员权限
 * @param repoId
 */
export const getMembers = (orgSid: string, teamName: string, repoId: any) => get(`${getMainBaseURL(orgSid, teamName)}/repos/${repoId}/memberconf/`);

/**
 * 获取项目信息
 * @param orgSid
 * @param teamName
 */
export const getProjectTeam = (orgSid: string, teamName: string) => get(`${getMainBaseURL(orgSid, teamName)}/`);

/**
 * 更新项目信息
 * @param orgSid
 * @param teamName
 * @param data
 */
export const putProjectTeam = (orgSid: string, teamName: string, data: any) => put(`${getMainBaseURL(orgSid, teamName)}/`, data);

/**
 * 获取项目成员
 * @param orgSid
 * @param teamName
 */
export const getProjectTeamMembers = (orgSid: string, teamName: string) => get(`${getMainBaseURL(orgSid, teamName)}/memberconf/`);

/**
 * 添加项目成员
 * @param orgSid
 * @param teamName
 * @param data
 */
export const postProjectTeamMembers = (orgSid: string, teamName: string, data: any) => post(`${getMainBaseURL(orgSid, teamName)}/memberconf/`, data);

/**
 * 移除项目成员
 * @param orgSid
 * @param teamName
 * @param role
 * @param username
 * @returns
 */
export const delProjectTeamMember = (orgSid: string, teamName: string, role: number, username: string) => del(`${getMainBaseURL(orgSid, teamName)}/memberconf/${role}/${username}/`);

/**
 * 获取团队成员列表
 * @param orgSid
 */
export const getOrgMembers = (orgSid: string) => get(`${MAIN_SERVER_API}/orgs/${orgSid}/memberconf/`);
