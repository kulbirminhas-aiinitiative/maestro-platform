import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { toast } from 'react-hot-toast'
import { EyeIcon, EyeOffIcon } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { useLogin } from '@/hooks/useAuth'
import { APP_NAME } from '@/lib/constants'

const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters'),
})

type LoginFormData = z.infer<typeof loginSchema>

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const navigate = useNavigate()
  const loginMutation = useLogin()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginFormData) => {
    try {
      await loginMutation.mutateAsync(data)
      toast.success('Welcome back!')
      navigate('/app/dashboard')
    } catch (error: any) {
      toast.error(error.message || 'Login failed')
    }
  }

  return (
    <div className="container relative min-h-screen flex-col items-center justify-center grid lg:max-w-none lg:grid-cols-2 lg:px-0">
      {/* Left side - Form */}
      <div className="lg:p-8">
        <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col space-y-2 text-center"
          >
            <h1 className="text-2xl font-semibold tracking-tight">
              Welcome back
            </h1>
            <p className="text-sm text-muted-foreground">
              Enter your email and password to sign in to your account
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Card>
              <CardHeader className="space-y-1">
                <CardTitle className="text-2xl text-center">Sign in</CardTitle>
                <CardDescription className="text-center">
                  Enter your credentials below to sign in to your account
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                  <div className="space-y-2">
                    <label htmlFor="email" className="text-sm font-medium">
                      Email
                    </label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="name@example.com"
                      {...register('email')}
                      error={errors.email?.message}
                      disabled={isSubmitting}
                    />
                  </div>

                  <div className="space-y-2">
                    <label htmlFor="password" className="text-sm font-medium">
                      Password
                    </label>
                    <div className="relative">
                      <Input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Enter your password"
                        {...register('password')}
                        error={errors.password?.message}
                        disabled={isSubmitting}
                        rightIcon={
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="text-muted-foreground hover:text-foreground"
                          >
                            {showPassword ? (
                              <EyeOffIcon className="h-4 w-4" />
                            ) : (
                              <EyeIcon className="h-4 w-4" />
                            )}
                          </button>
                        }
                      />
                    </div>
                  </div>

                  <Button
                    type="submit"
                    className="w-full"
                    loading={isSubmitting}
                    disabled={isSubmitting}
                  >
                    Sign In
                  </Button>
                </form>

                <div className="mt-4 text-center text-sm">
                  <Link
                    to="/auth/forgot-password"
                    className="text-primary hover:underline"
                  >
                    Forgot your password?
                  </Link>
                </div>

                <div className="mt-6 text-center text-sm text-muted-foreground">
                  Don&apos;t have an account?{' '}
                  <Link
                    to="/auth/register"
                    className="text-primary hover:underline font-medium"
                  >
                    Sign up
                  </Link>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>

      {/* Right side - Hero */}
      <div className="relative hidden h-full flex-col bg-muted p-10 text-white lg:flex dark:border-r">
        <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary/90 to-primary/70" />
        <div className="relative z-20 flex items-center text-lg font-medium">
          <div className="mr-2 h-6 w-6 rounded bg-white/20 flex items-center justify-center">
            <span className="text-sm font-bold">S</span>
          </div>
          {APP_NAME}
        </div>
        <div className="relative z-20 mt-auto">
          <blockquote className="space-y-2">
            <p className="text-lg">
              &ldquo;Sunday.com has revolutionized how our team collaborates and manages projects.
              The intuitive interface and powerful automation features have increased our productivity by 40%.&rdquo;
            </p>
            <footer className="text-sm opacity-80">Sofia Davis, Product Manager</footer>
          </blockquote>
        </div>
      </div>
    </div>
  )
}