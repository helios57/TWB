package core

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

// BuildingCost represents the resource cost of a building.
type BuildingCost struct {
	Wood      int
	Stone     int
	Iron      int
	Pop       int
	CanBuild  bool
	BuildLink string
}

// GameState represents the game data.
type GameState struct {
	Village struct {
		ID         int               `json:"id"`
		Name       string            `json:"name"`
		Wood       float64           `json:"wood"`
		Stone      float64           `json:"stone"`
		Iron       float64           `json:"iron"`
		Pop        int               `json:"pop"`
		PopMax     int               `json:"pop_max"`
		StorageMax int               `json:"storage_max"`
		Buildings  map[string]string `json:"buildings"`
	} `json:"village"`
}

// Extractor provides methods for parsing HTML.
var Extractor = &extractor{}

// UnitCost represents the resource cost of a unit.
type UnitCost struct {
	Wood            int
	Stone           int
	Iron            int
	Pop             int
	RequirementsMet bool
}

type extractor struct{}

// GameState extracts the game state from the HTML.
func (e *extractor) GameState(html string) (*GameState, error) {
	re := regexp.MustCompile(`(?s)TribalWars\.updateGameData\((.+?)\);`)
	matches := re.FindStringSubmatch(html)
	if len(matches) < 2 {
		return nil, fmt.Errorf("game data not found in HTML")
	}

	var gameState GameState
	err := json.Unmarshal([]byte(matches[1]), &gameState)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal game data: %w", err)
	}

	return &gameState, nil
}

// UnitsInVillage extracts the units in the village from the HTML.
func (e *extractor) UnitsInVillage(html string) (map[string]int, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	units := make(map[string]int)
	doc.Find("#units_home tr").Each(func(i int, s *goquery.Selection) {
		if i == 1 {
			s.Find("td.unit-item").Each(func(j int, s *goquery.Selection) {
				class, _ := s.Attr("class")
				parts := strings.Split(class, " ")
				unit := strings.TrimPrefix(parts[1], "unit-item-")
				count, _ := strconv.Atoi(s.Text())
				units[unit] = count
			})
		}
	})

	return units, nil
}

// VillageIDs extracts the village IDs from the HTML.
func (e *extractor) VillageIDs(html string) ([]string, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	var villageIDs []string
	villageIDMap := make(map[string]bool)
	doc.Find("#menu_row2_village a[href*='village=']").Each(func(i int, s *goquery.Selection) {
		href, _ := s.Attr("href")
		re := regexp.MustCompile(`village=(\d+)`)
		matches := re.FindStringSubmatch(href)
		if len(matches) > 1 {
			if _, ok := villageIDMap[matches[1]]; !ok {
				villageIDs = append(villageIDs, matches[1])
				villageIDMap[matches[1]] = true
			}
		}
	})

	return villageIDs, nil
}

// BuildingCosts extracts the building costs from the HTML.
func (e *extractor) BuildingCosts(html string) (map[string]BuildingCost, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	costs := make(map[string]BuildingCost)
	doc.Find("#building_main tr.row_a, #building_main tr.row_b").Each(func(i int, s *goquery.Selection) {
		buildingNode := s.Find("td:first-child a")
		buildingNameRaw := strings.TrimSpace(buildingNode.Text())
		re := regexp.MustCompile(`\s\s+`)
		buildingNameClean := re.ReplaceAllString(buildingNameRaw, " ")
		re = regexp.MustCompile(`^([a-zA-Z_]+)`)
		buildingMatch := re.FindStringSubmatch(buildingNameClean)
		if len(buildingMatch) < 2 {
			return
		}
		building := strings.ToLower(buildingMatch[1])

		var cost BuildingCost
		s.Find("span.cost_wood, span.cost_stone, span.cost_iron, span.cost_pop").Each(func(j int, s *goquery.Selection) {
			val, _ := strconv.Atoi(s.Text())
			if s.HasClass("cost_wood") {
				cost.Wood = val
			} else if s.HasClass("cost_stone") {
				cost.Stone = val
			} else if s.HasClass("cost_iron") {
				cost.Iron = val
			} else if s.HasClass("cost_pop") {
				cost.Pop = val
			}
		})

		buildLink, exists := s.Find("td:last-child a").Attr("href")
		cost.CanBuild = exists
		if exists {
			cost.BuildLink = buildLink
		}

		costs[building] = cost
	})

	return costs, nil
}

// RecruitData extracts the recruitment data from the HTML of a training building.
func (e *extractor) RecruitData(html string) (map[string]UnitCost, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to create goquery document: %w", err)
	}

	data := make(map[string]UnitCost)
	doc.Find("form#train_form tr.row_a, form#train_form tr.row_b").Each(func(i int, s *goquery.Selection) {
		unitName, exists := s.Find("input[name]").Attr("name")
		if !exists {
			return
		}

		var cost UnitCost
		s.Find("span.cost_wood, span.cost_stone, span.cost_iron, span.cost_pop").Each(func(j int, s *goquery.Selection) {
			val, _ := strconv.Atoi(s.Text())
			if s.HasClass("cost_wood") {
				cost.Wood = val
			} else if s.HasClass("cost_stone") {
				cost.Stone = val
			} else if s.HasClass("cost_iron") {
				cost.Iron = val
			} else if s.HasClass("cost_pop") {
				cost.Pop = val
			}
		})

		cost.RequirementsMet = s.Find("a.btn-recruit").Length() > 0
		data[unitName] = cost
	})

	return data, nil
}

// HToken extracts the h token from the HTML.
func (e *extractor) HToken(html string) (string, error) {
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return "", fmt.Errorf("failed to create goquery document: %w", err)
	}

	h, exists := doc.Find("input[name=h]").Attr("value")
	if !exists {
		return "", fmt.Errorf("h token not found")
	}

	return h, nil
}
