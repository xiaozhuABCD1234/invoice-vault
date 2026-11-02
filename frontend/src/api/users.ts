import { request, toQueryParams } from './client'
import type {
  ItemsResponse,
  Page,
  User,
  UserCreate,
  UserListQuery,
  UserOption,
  UserUpdate,
} from './types'

export function listUsers(query: UserListQuery = {}): Promise<Page<User>> {
  return request<Page<User>>('/users', { query: toQueryParams(query) })
}

export function createUser(body: UserCreate): Promise<User> {
  return request<User>('/users', { method: 'POST', body })
}

export function updateUser(id: number, body: UserUpdate): Promise<User> {
  return request<User>(`/users/${id}`, { method: 'PATCH', body })
}

/** 登录用户可读取的下拉选项。 */
export function listUserOptions(): Promise<ItemsResponse<UserOption>> {
  return request<ItemsResponse<UserOption>>('/users/options')
}
