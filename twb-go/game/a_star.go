package game

import "container/heap"

// SearchNode represents a node in the A* search graph.
type SearchNode struct {
	State     GameState   // The state of the village at this node
	Action    Action      // The action that *led* to this state
	Parent    *SearchNode // The node we came from (to reconstruct the path)
	Cost      float64     // "g(n)": Total time (in seconds) from start to this node
	Heuristic float64     // "h(n)": Estimated time *remaining* to reach the goal
	Priority  float64     // "f(n)": Total cost (g + h). This is what the queue sorts by.
	index     int         // The index of the item in the heap.
}

// PriorityQueue implements a min-heap for SearchNodes.
type PriorityQueue []*SearchNode

// Len returns the length of the priority queue.
func (pq PriorityQueue) Len() int { return len(pq) }

// Less compares two SearchNodes based on their priority.
func (pq PriorityQueue) Less(i, j int) bool {
	return pq[i].Priority < pq[j].Priority
}

// Swap swaps two SearchNodes in the priority queue.
func (pq PriorityQueue) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
	pq[i].index = i
	pq[j].index = j
}

// Push adds a SearchNode to the priority queue.
func (pq *PriorityQueue) Push(x interface{}) {
	n := len(*pq)
	item := x.(*SearchNode)
	item.index = n
	*pq = append(*pq, item)
}

// Pop removes and returns the best SearchNode from the priority queue.
func (pq *PriorityQueue) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	old[n-1] = nil  // avoid memory leak
	item.index = -1 // for safety
	*pq = old[0 : n-1]
	return item
}

// update modifies the priority and value of an Item in the queue.
func (pq *PriorityQueue) update(item *SearchNode, state GameState, cost, priority float64) {
	item.State = state
	item.Cost = cost
	item.Priority = priority
	heap.Fix(pq, item.index)
}
