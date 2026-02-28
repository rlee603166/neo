import { Handle, Position } from '@xyflow/react'

const TYPE_BORDER = {
  thinking: 'border-purple-400',
  code:     'border-blue-400',
  test:     'border-amber-400',
  synthesize: 'border-teal-400',
}

const STATE_DOT = {
  completed: 'bg-green-500',
  running:   'bg-amber-400 animate-pulse',
  failed:    'bg-coral-500',
  ready:     'bg-cream-400',
}

export default function NodeCard({ data, selected }) {
  const borderColor = TYPE_BORDER[data.node_type] ?? 'border-cream-400'
  const dotColor = STATE_DOT[data.state] ?? 'bg-cream-400'
  const childCount = data.children_ids?.length ?? 0

  return (
    <div
      className={`bg-cream-50 rounded shadow-sm border-l-4 ${borderColor} px-3 py-2 w-44 text-xs ${selected ? 'ring-2 ring-coral-400' : ''}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-cream-300" />

      <div className="flex items-center justify-between mb-1">
        <span className="font-semibold text-stone-700 capitalize">
          {data.node_type}
        </span>
        <div className="flex items-center gap-1">
          {childCount > 0 && (
            <span className="bg-cream-200 text-stone-500 rounded-full px-1.5 py-0.5 text-[10px]">
              {childCount}
            </span>
          )}
          <span className={`w-2.5 h-2.5 rounded-full ${dotColor}`} />
        </div>
      </div>

      <div className="font-mono text-stone-400 truncate">
        {data.node_id?.slice(0, 8)}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-cream-300" />
    </div>
  )
}
