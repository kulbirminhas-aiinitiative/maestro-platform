import React, { ReactNode } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './Dialog'
import { Button } from './Button'
import { X } from 'lucide-react'
import clsx from 'clsx'

interface SheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: ReactNode
}

interface SheetTriggerProps {
  asChild?: boolean
  children: ReactNode
}

interface SheetContentProps {
  side?: 'left' | 'right' | 'top' | 'bottom'
  className?: string
  children: ReactNode
}

interface SheetHeaderProps {
  className?: string
  children: ReactNode
}

interface SheetTitleProps {
  className?: string
  children: ReactNode
}

interface SheetDescriptionProps {
  className?: string
  children: ReactNode
}

const SheetContext = React.createContext<{
  open: boolean
  onOpenChange: (open: boolean) => void
}>({
  open: false,
  onOpenChange: () => {},
})

export const Sheet: React.FC<SheetProps> = ({ open, onOpenChange, children }) => {
  return (
    <SheetContext.Provider value={{ open, onOpenChange }}>
      {children}
    </SheetContext.Provider>
  )
}

export const SheetTrigger: React.FC<SheetTriggerProps> = ({ asChild, children }) => {
  const { onOpenChange } = React.useContext(SheetContext)

  if (asChild) {
    return React.cloneElement(children as React.ReactElement, {
      onClick: () => onOpenChange(true),
    })
  }

  return (
    <button onClick={() => onOpenChange(true)}>
      {children}
    </button>
  )
}

export const SheetContent: React.FC<SheetContentProps> = ({
  side = 'right',
  className,
  children,
}) => {
  const { open, onOpenChange } = React.useContext(SheetContext)

  const slideInClasses = {
    left: 'slide-in-from-left-full',
    right: 'slide-in-from-right-full',
    top: 'slide-in-from-top-full',
    bottom: 'slide-in-from-bottom-full',
  }

  const positionClasses = {
    left: 'left-0 top-0 h-full border-r',
    right: 'right-0 top-0 h-full border-l',
    top: 'top-0 left-0 w-full border-b',
    bottom: 'bottom-0 left-0 w-full border-t',
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={clsx(
          'fixed z-50 gap-4 bg-white p-6 shadow-lg transition ease-in-out',
          'data-[state=open]:animate-in data-[state=closed]:animate-out',
          'data-[state=closed]:duration-300 data-[state=open]:duration-500',
          `data-[state=open]:${slideInClasses[side]}`,
          positionClasses[side],
          side === 'left' || side === 'right' ? 'w-3/4 sm:max-w-sm' : 'h-auto',
          className
        )}
        hideCloseButton
      >
        <Button
          variant="ghost"
          size="sm"
          className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100"
          onClick={() => onOpenChange(false)}
        >
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </Button>
        {children}
      </DialogContent>
    </Dialog>
  )
}

export const SheetHeader: React.FC<SheetHeaderProps> = ({ className, children }) => {
  return (
    <div className={clsx('flex flex-col space-y-2 text-center sm:text-left', className)}>
      {children}
    </div>
  )
}

export const SheetTitle: React.FC<SheetTitleProps> = ({ className, children }) => {
  return (
    <h2 className={clsx('text-lg font-semibold text-foreground', className)}>
      {children}
    </h2>
  )
}

export const SheetDescription: React.FC<SheetDescriptionProps> = ({ className, children }) => {
  return (
    <p className={clsx('text-sm text-muted-foreground', className)}>
      {children}
    </p>
  )
}