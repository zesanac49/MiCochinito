import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLogin } from '@/hooks/auth'
import { mensajeError } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'

export function Login() {
  const login = useLogin()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    login.mutate({ email, password }, { onSuccess: () => navigate('/') })
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-3">
          <img
            src="/logo.png"
            alt="Mi Cochinito"
            className="h-16 w-16 rounded-nm object-cover shadow-nm"
          />
          <h1 className="text-xl font-bold tracking-tight">Mi Cochinito</h1>
          <p className="text-sm text-text-secondary">Administración de tu fondo</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field
            label="Correo"
            name="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Field
            label="Contraseña"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {login.isError && (
            <p className="text-sm text-danger">{mensajeError(login.error)}</p>
          )}
          <Button
            type="submit"
            variante="primaria"
            cargando={login.isPending}
            className="w-full"
          >
            Ingresar
          </Button>
        </form>
      </Card>
    </div>
  )
}
