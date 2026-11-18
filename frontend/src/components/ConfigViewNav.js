'use client'

export default function ConfigViewNav({ views = [], value, onChange }) {
  return (
    <div className="admin-subnav" role="group" aria-label="Configuration views">
      {views.map((view) => (
        <button
          key={view.key}
          type="button"
          aria-pressed={value === view.key}
          className={`admin-subnav-btn ${value === view.key ? 'is-active' : ''}`}
          onClick={() => onChange?.(view.key)}
        >
          {view.label}
        </button>
      ))}
    </div>
  )
}
