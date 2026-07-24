import type { ButtonHTMLAttributes, PropsWithChildren } from 'react'
import { twMerge } from 'tailwind-merge'

export function Button({ className, children, ...props }: PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>>) {
  return <button className={twMerge('inline-flex items-center justify-center rounded-xl bg-emerald-700 px-4 py-3 font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50', className)} {...props}>{children}</button>
}
