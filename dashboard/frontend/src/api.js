const BASE_URL = 'http://127.0.0.1:8000'

export async function fetchTrees() {
  const res = await fetch(`${BASE_URL}/tree`)
  if (!res.ok) throw new Error(`Failed to fetch trees: ${res.status}`)
  return res.json()
}

export async function fetchTree(treeId) {
  const res = await fetch(`${BASE_URL}/tree/${treeId}`)
  if (!res.ok) throw new Error(`Failed to fetch tree ${treeId}: ${res.status}`)
  return res.json()
}

export async function fetchNode(treeId, nodeId) {
  const res = await fetch(`${BASE_URL}/tree/${treeId}/${nodeId}`)
  if (!res.ok) throw new Error(`Failed to fetch node ${nodeId}: ${res.status}`)
  return res.json()
}

export async function saveNode(treeId, nodeId) {
  const res = await fetch(`${BASE_URL}/tree/${treeId}/${nodeId}/save`, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to save node ${nodeId}: ${res.status}`)
  return res.json()
}
