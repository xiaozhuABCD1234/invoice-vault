import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** 合并条件 class，并用 tailwind-merge 消除同族工具类冲突。 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
