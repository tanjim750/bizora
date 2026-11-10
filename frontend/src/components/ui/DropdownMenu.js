'use client'

import React from 'react'
import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'
import clsx from 'clsx'

export const DropdownMenu = DropdownMenuPrimitive.Root
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger
export const DropdownMenuGroup = DropdownMenuPrimitive.Group
export const DropdownMenuPortal = DropdownMenuPrimitive.Portal
export const DropdownMenuSub = DropdownMenuPrimitive.Sub
export const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup

export function DropdownMenuContent({ className = '', sideOffset = 4, align = 'start', children, ...props }) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        sideOffset={sideOffset}
        align={align}
        className={clsx('dropdown-content', className)}
        {...props}
      >
        {children}
      </DropdownMenuPrimitive.Content>
    </DropdownMenuPrimitive.Portal>
  )
}

export function DropdownMenuItem({ className = '', inset = false, children, ...props }) {
  return (
    <DropdownMenuPrimitive.Item
      className={clsx('dropdown-item', inset && 'dropdown-item-inset', className)}
      {...props}
    >
      {children}
    </DropdownMenuPrimitive.Item>
  )
}

export function DropdownMenuLabel({ className = '', inset = false, children, ...props }) {
  return (
    <DropdownMenuPrimitive.Label
      className={clsx('dropdown-label', inset && 'dropdown-item-inset', className)}
      {...props}
    >
      {children}
    </DropdownMenuPrimitive.Label>
  )
}

export function DropdownMenuSeparator({ className = '', ...props }) {
  return <DropdownMenuPrimitive.Separator className={clsx('dropdown-separator', className)} {...props} />
}

export default DropdownMenu
