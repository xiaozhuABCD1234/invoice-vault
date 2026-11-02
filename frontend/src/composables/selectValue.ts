export interface SelectOptionLike {
  value: string
  label: string
  disabled?: boolean
}

/** Reka UI 的 SelectItem 不接受空字符串，空值统一映射为哨兵值。 */
export const UNSET_SELECT_VALUE = '__unset__'

export function toSelectValue(value: string): string {
  return value === '' ? UNSET_SELECT_VALUE : value
}

export function fromSelectValue(value: string): string {
  return value === UNSET_SELECT_VALUE ? '' : value
}

export function withUnsetOption(
  options: SelectOptionLike[],
  label: string,
): SelectOptionLike[] {
  return [{ value: UNSET_SELECT_VALUE, label }, ...options]
}
