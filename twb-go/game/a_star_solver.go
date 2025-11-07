package game

import (
	"container/heap"
	"fmt"
	"sort"
	"strings"
)

// AStarSolver is the core A* search algorithm.
type AStarSolver struct {
	ActionGenerator  *ActionGenerator
	VillageSimulator *VillageSimulator
}

// NewAStarSolver creates a new AStarSolver.
func NewAStarSolver(actionGenerator *ActionGenerator, villageSimulator *VillageSimulator) *AStarSolver {
	return &AStarSolver{
		ActionGenerator:  actionGenerator,
		VillageSimulator: villageSimulator,
	}
}

// FindOptimalPlan finds the optimal sequence of actions to reach a goal state.
func (s *AStarSolver) FindOptimalPlan(startState GameState, goalState GameState) ([]Action, error) {
	openSet := &PriorityQueue{}
	heap.Init(openSet)

	startNode := &SearchNode{
		State:     startState,
		Action:    nil,
		Parent:    nil,
		Cost:      0,
		Heuristic: s.Heuristic(startState, goalState),
		Priority:  s.Heuristic(startState, goalState),
	}
	heap.Push(openSet, startNode)

	closedSet := make(map[string]bool)

	for openSet.Len() > 0 {
		currentNode := heap.Pop(openSet).(*SearchNode)
		currentNodeHash := s.hashState(currentNode.State)

		if s.isGoalState(currentNode.State, goalState) {
			return s.reconstructPath(currentNode), nil
		}

		if closedSet[currentNodeHash] {
			continue
		}
		closedSet[currentNodeHash] = true

		actions := s.ActionGenerator.GenerateActionsFromState(currentNode.State)

		for _, action := range actions {
			nextState, timeCost, err := s.VillageSimulator.CalculateNextState(currentNode.State, action)
			if err != nil {
				continue
			}

			if closedSet[s.hashState(nextState)] {
				continue
			}

			newCost := currentNode.Cost + timeCost
			heuristic := s.Heuristic(nextState, goalState)
			newNode := &SearchNode{
				State:     nextState,
				Action:    action,
				Parent:    currentNode,
				Cost:      newCost,
				Heuristic: heuristic,
				Priority:  newCost + heuristic,
			}

			heap.Push(openSet, newNode)
		}
	}

	return nil, fmt.Errorf("no path found")
}

// Heuristic estimates the cost to reach the goal state.
func (s *AStarSolver) Heuristic(state GameState, goal GameState) float64 {
	maxTime := 0.0

	for building, goalLevel := range goal.BuildingLevels {
		currentLevel := state.BuildingLevels[building]
		if currentLevel < goalLevel {
			timeToAfford, err := s.VillageSimulator.calculateTimeToAfford(state, BuildAction{Building: building, Level: goalLevel})
			if err == nil && timeToAfford.Seconds() > maxTime {
				maxTime = timeToAfford.Seconds()
			}
		}
	}

	for unit, goalAmount := range goal.TroopLevels {
		currentAmount := state.TroopLevels[unit]
		if currentAmount < goalAmount {
			timeToAfford, err := s.VillageSimulator.calculateTimeToRecruit(state, RecruitAction{Unit: unit, Amount: goalAmount - currentAmount})
			if err == nil && timeToAfford.Seconds() > maxTime {
				maxTime = timeToAfford.Seconds()
			}
		}
	}

	return maxTime
}

// isGoalState checks if the current state has reached the goal state.
func (s *AStarSolver) isGoalState(current GameState, goal GameState) bool {
	for building, level := range goal.BuildingLevels {
		if current.BuildingLevels[building] < level {
			return false
		}
	}
	for unit, count := range goal.TroopLevels {
		if current.TroopLevels[unit] < count {
			return false
		}
	}
	return true
}

// reconstructPath reconstructs the sequence of actions from the goal node.
func (s *AStarSolver) reconstructPath(node *SearchNode) []Action {
	var path []Action
	for node.Parent != nil {
		path = append([]Action{node.Action}, path...)
		node = node.Parent
	}
	return path
}

// hashState creates a unique, stable hash for a game state.
func (s *AStarSolver) hashState(state GameState) string {
	var b strings.Builder

	// Sort and write building levels
	buildingKeys := make([]string, 0, len(state.BuildingLevels))
	for k := range state.BuildingLevels {
		buildingKeys = append(buildingKeys, k)
	}
	sort.Strings(buildingKeys)
	for _, k := range buildingKeys {
		fmt.Fprintf(&b, "%s:%d;", k, state.BuildingLevels[k])
	}

	b.WriteString("|")

	// Sort and write troop levels
	troopKeys := make([]string, 0, len(state.TroopLevels))
	for k := range state.TroopLevels {
		troopKeys = append(troopKeys, k)
	}
	sort.Strings(troopKeys)
	for _, k := range troopKeys {
		fmt.Fprintf(&b, "%s:%d;", k, state.TroopLevels[k])
	}

	return b.String()
}
