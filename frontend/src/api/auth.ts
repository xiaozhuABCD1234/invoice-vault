import { request } from './client'
import type { LoginRequest, RefreshResponse, TokenResponse, User } from './types'

export function login(body: LoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body,
    skipAuthRefresh: true,
  })
}

/** 读取 HttpOnly refresh cookie，轮换 token。 */
export function refresh(): Promise<RefreshResponse> {
  return request<RefreshResponse>('/auth/refresh', {
    method: 'POST',
    skipAuthRefresh: true,
  })
}

export function logout(): Promise<void> {
  return request<void>('/auth/logout', {
    method: 'POST',
    skipAuthRefresh: true,
  })
}

export function me(): Promise<User> {
  return request<User>('/me')
}
