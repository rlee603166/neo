import { useState, useCallback } from 'react'
import { saveNode } from '../api'

const TYPE_BADGE = {
  thinking:   'bg-purple-100 text-purple-700',
  code:       'bg-blue-100 text-blue-700',
  test:       'bg-amber-100 text-amber-700',
  synthesize: 'bg-teal-100 text-teal-700',
}

const STATE_DOT = {
  completed: 'bg-green-500',
  running:   'bg-amber-400 animate-pulse',
  failed:    'bg-coral-500',
  ready:     'bg-cream-400',
}

/** Build a map of tool_use_id → result content string from all messages. */
function buildToolResultMap(messages) {
  const map = {}
  for (const msg of messages) {
    if (msg.role !== 'user' || !Array.isArray(msg.content)) continue
    for (const block of msg.content) {
      if (block.type === 'tool_result') {
        map[block.tool_use_id] =
          typeof block.content === 'string'
            ? block.content
            : JSON.stringify(block.content, null, 2)
      }
    }
  }
  return map
}

function ToolCallBlock({ block, result }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded border border-cream-300 text-xs mb-1 overflow-hidden">
      <button
        className="w-full flex items-center gap-2 px-3 py-1.5 bg-cream-200 hover:bg-cream-300 text-left transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <span className="font-mono font-semibold text-stone-700 flex-1 truncate">
          {block.name}
        </span>
        <span className="shrink-0 text-[10px] font-medium bg-cream-100 text-stone-400 px-1.5 py-0.5 rounded">
          tool_use
        </span>
        <span className="shrink-0 text-stone-400">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <>
          <div className="bg-cream-50 px-3 py-2 border-t border-cream-300 max-h-48 overflow-y-auto">
            <pre className="text-stone-600 whitespace-pre-wrap break-all">
              {JSON.stringify(block.input, null, 2)}
            </pre>
          </div>
          {result !== undefined && (
            <div className="bg-cream-100 border-t border-cream-300 px-3 py-2 max-h-48 overflow-y-auto">
              <pre className="text-stone-500 whitespace-pre-wrap break-all">
                {result}
              </pre>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function MessageBlock({ message, toolResults }) {
  const { role, content } = message

  const renderBlocks = () => {
    if (typeof content === 'string') {
      return (
        <div
          className={`rounded px-3 py-2 text-xs whitespace-pre-wrap break-words ${
            role === 'assistant'
              ? 'bg-cream-200 text-stone-700'
              : 'bg-cream-50 text-stone-600 border border-cream-300'
          }`}
        >
          {content}
        </div>
      )
    }

    if (!Array.isArray(content)) return null

    const rendered = content.map((block, i) => {
      if (role === 'assistant' && block.type === 'text') {
        return (
          <div
            key={i}
            className="rounded px-3 py-2 text-xs bg-cream-200 text-stone-700 whitespace-pre-wrap break-words mb-1"
          >
            {block.text}
          </div>
        )
      }

      if (role === 'assistant' && block.type === 'tool_use') {
        return <ToolCallBlock key={i} block={block} result={toolResults[block.id]} />
      }

      // tool_result blocks rendered inside their paired tool_use — skip here
      if (role === 'user' && block.type === 'tool_result') {
        return null
      }

      if (role === 'user' && block.type === 'text') {
        return (
          <div
            key={i}
            className="rounded px-3 py-2 text-xs bg-cream-50 text-stone-600 border border-cream-300 whitespace-pre-wrap break-words mb-1"
          >
            {block.text}
          </div>
        )
      }

      return (
        <div key={i} className="text-xs text-stone-400 mb-1">
          [{block.type}]
        </div>
      )
    })

    if (rendered.every(r => r === null)) return null
    return rendered
  }

  const blocks = renderBlocks()
  if (blocks === null) return null

  return (
    <div className="mb-3">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-stone-400 mb-1">
        {role}
      </div>
      {blocks}
    </div>
  )
}

export default function DetailPanel({ node, treeId = 'tree' }) {
  const [saveStatus, setSaveStatus] = useState(null)

  const handleSave = useCallback(() => {
    setSaveStatus('saving')
    saveNode(treeId, node.node_id)
      .then(() => setSaveStatus('saved'))
      .catch(() => setSaveStatus('error'))
      .finally(() => setTimeout(() => setSaveStatus(null), 2000))
  }, [treeId, node.node_id])

  if (!node) return null

  const badgeClass = TYPE_BADGE[node.node_type] ?? 'bg-cream-200 text-stone-600'
  const dotClass = STATE_DOT[node.state] ?? 'bg-cream-400'
  const conversation = node.conversation?.messages ?? []
  const toolResults = buildToolResultMap(conversation)

  return (
    <div className="flex flex-col h-full bg-cream-50 border-l border-cream-300 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cream-300 bg-cream-100 shrink-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs font-semibold px-2 py-0.5 rounded capitalize ${badgeClass}`}>
            {node.node_type}
          </span>
          <span className={`w-2.5 h-2.5 rounded-full ${dotClass}`} />
          <span className="text-xs text-stone-400">{node.state}</span>
        </div>
        <div className="font-mono text-xs text-stone-600 break-all">
          {node.node_id}
        </div>
        <div className="flex items-center justify-between mt-1">
          <div className="text-xs text-stone-400">
            wd: {node.working_directory ?? '.'}
          </div>
          <button
            onClick={handleSave}
            disabled={saveStatus === 'saving'}
            className="text-xs font-medium px-2.5 py-1 rounded bg-cream-200 hover:bg-cream-300 text-stone-600 transition-colors disabled:opacity-50"
          >
            {saveStatus === 'saving' ? 'Saving…' : saveStatus === 'saved' ? 'Saved!' : saveStatus === 'error' ? 'Failed' : 'Save'}
          </button>
        </div>
      </div>

      {/* Conversation */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <div className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-3">
          Conversation ({conversation.length} messages)
        </div>
        {conversation.map((msg, i) => (
          <MessageBlock key={i} message={msg} toolResults={toolResults} />
        ))}
      </div>
    </div>
  )
}
