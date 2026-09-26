import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { createUser, listUsers, updateUser } from '../api/client'
import type { UserRole } from '../types'
import { formatDateTime } from '../utils/format'

const ROLES: UserRole[] = ['admin', 'investigator', 'viewer']

export default function Users() {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('viewer')
  const [formError, setFormError] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['users'],
    queryFn: () => listUsers({ page_size: 100 }),
  })

  const createMutation = useMutation({
    mutationFn: () => createUser({ name, email, password, role }),
    onSuccess: () => {
      setEmail('')
      setName('')
      setPassword('')
      setRole('viewer')
      setFormError(null)
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: () => setFormError('Could not create user.'),
  })

  const roleMutation = useMutation({
    mutationFn: ({ id, newRole }: { id: string; newRole: UserRole }) =>
      updateUser(id, { role: newRole }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    createMutation.mutate()
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-100">Users</h1>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Create user
        </h2>
        {formError && (
          <p className="mb-3 rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
            {formError}
          </p>
        )}
        <form onSubmit={handleCreate} className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <input
            data-testid="user-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            placeholder="Full name"
            className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none"
          />
          <input
            data-testid="user-email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            placeholder="Email"
            className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none"
          />
          <input
            data-testid="user-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            placeholder="Password (min 8)"
            className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none"
          />
          <select
            data-testid="user-role"
            value={role}
            onChange={(event) => setRole(event.target.value as UserRole)}
            className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 focus:border-accent focus:outline-none"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-60"
          >
            {createMutation.isPending ? 'Creating…' : 'Create user'}
          </button>
        </form>
      </section>

      {isLoading ? (
        <p className="text-slate-400">Loading users…</p>
      ) : isError || !data ? (
        <p className="text-bad">Failed to load users.</p>
      ) : (
        <section className="rounded-xl border border-edge bg-panel">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-edge text-xs uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((user) => (
                <tr key={user.id} className="border-b border-edge/60 last:border-0">
                  <td className="px-4 py-3 text-slate-200">{user.name}</td>
                  <td className="px-4 py-3 text-slate-300">{user.email}</td>
                  <td className="px-4 py-3">
                    <select
                      data-testid={`user-role-${user.email}`}
                      value={user.role}
                      onChange={(event) =>
                        roleMutation.mutate({
                          id: user.id,
                          newRole: event.target.value as UserRole,
                        })
                      }
                      className="rounded-md border border-edge bg-surface px-2 py-1 text-sm capitalize text-slate-200"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {formatDateTime(user.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}
