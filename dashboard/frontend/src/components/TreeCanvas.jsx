import { useCallback, useMemo } from 'react'
import { ReactFlow, Background, Controls, MiniMap } from '@xyflow/react'
import dagre from '@dagrejs/dagre'
import NodeCard from './NodeCard'

const nodeTypes = { nodeCard: NodeCard }

function computeLayout(nodes) {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'TB', ranksep: 80, nodesep: 40 })
  g.setDefaultEdgeLabel(() => ({}))

  Object.values(nodes).forEach(n => g.setNode(n.node_id, { width: 180, height: 60 }))
  Object.values(nodes).forEach(n => {
    if (n.parent_id) g.setEdge(n.parent_id, n.node_id)
  })

  dagre.layout(g)

  const rfNodes = Object.values(nodes).map(n => {
    const { x, y } = g.node(n.node_id)
    return {
      id: n.node_id,
      type: 'nodeCard',
      position: { x: x - 90, y: y - 30 },
      data: { ...n },
    }
  })

  const rfEdges = Object.values(nodes)
    .filter(n => n.parent_id)
    .map(n => ({
      id: `${n.parent_id}-${n.node_id}`,
      source: n.parent_id,
      target: n.node_id,
      type: 'smoothstep',
      style: { stroke: '#C4B59E' },
    }))

  return { rfNodes, rfEdges }
}

export default function TreeCanvas({ nodes, onSelectNode, selectedNodeId }) {
  const { rfNodes, rfEdges } = useMemo(
    () => (nodes ? computeLayout(nodes) : { rfNodes: [], rfEdges: [] }),
    [nodes],
  )

  const styledNodes = useMemo(
    () => rfNodes.map(n => ({ ...n, selected: n.id === selectedNodeId })),
    [rfNodes, selectedNodeId],
  )

  const handleNodeClick = useCallback(
    (_, node) => onSelectNode(node.id),
    [onSelectNode],
  )

  return (
    <div className="w-full h-full" style={{ background: '#F5EDE0' }}>
      <ReactFlow
        nodes={styledNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        style={{ background: '#F5EDE0' }}
      >
        <Background color="#DDD0BA" gap={20} />
        <Controls />
        <MiniMap
          nodeStrokeWidth={3}
          zoomable
          pannable
          style={{ background: '#EDE1CE' }}
          maskColor="rgba(245, 237, 224, 0.6)"
        />
      </ReactFlow>
    </div>
  )
}
