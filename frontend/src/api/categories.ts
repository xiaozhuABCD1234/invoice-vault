import { request, toQueryParams } from './client'
import type {
  Category,
  CategoryCreate,
  CategoryListQuery,
  CategoryUpdate,
  ItemsResponse,
} from './types'

export function listCategories(
  query: CategoryListQuery = {},
): Promise<ItemsResponse<Category>> {
  return request<ItemsResponse<Category>>('/categories', {
    query: toQueryParams(query),
  })
}

export function createCategory(body: CategoryCreate): Promise<Category> {
  return request<Category>('/categories', { method: 'POST', body })
}

export function updateCategory(
  id: number,
  body: CategoryUpdate,
): Promise<Category> {
  return request<Category>(`/categories/${id}`, {
    method: 'PATCH',
    body,
  })
}
