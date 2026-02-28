import { useState, useEffect, useCallback } from 'react'
import { fetchTree, fetchNode } from './api'
import TreeCanvas from './components/TreeCanvas'
import DetailPanel from './components/DetailPanel'

const DEFAULT_TREE_ID = 'tree'

export default function App() {
  const [treeId] = useState(DEFAULT_TREE_ID)
  const [treeSummary, setTreeSummary] = useState(null)
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const [nodeDetail, setNodeDetail] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchTree(treeId)
      .then(setTreeSummary)
      .catch(err => setError(err.message))
  }, [treeId])

  const handleSelectNode = useCallback(
    nodeId => {
      setSelectedNodeId(nodeId)
      setNodeDetail(null)
      fetchNode(treeId, nodeId)
        .then(setNodeDetail)
        .catch(err => setError(err.message))
    },
    [treeId],
  )

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen text-coral-500 text-sm">
        Error: {error}
      </div>
    )
  }

  if (!treeSummary) {
    return (
      <div className="flex items-center justify-center h-screen text-cream-400 text-sm">
        Loading tree…
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-cream-100">
      {/* Left panel — canvas */}
      <div className="flex-1 min-w-0">
        <TreeCanvas
          nodes={treeSummary.nodes}
          onSelectNode={handleSelectNode}
          selectedNodeId={selectedNodeId}
        />
      </div>

      {/* Right panel — detail */}
      {selectedNodeId && (
        <div className="w-1/2 shrink-0">
          {nodeDetail ? (
            <DetailPanel node={nodeDetail} treeId={treeId} />
          ) : (
            <div className="flex items-center justify-center h-full text-cream-400 text-sm border-l border-cream-300">
              Loading…
            </div>
          )}
        </div>
      )}
    </div>
  )
}
