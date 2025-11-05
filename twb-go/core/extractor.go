package core

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

// GameState represents the game data.
type GameState struct {
	Village struct {
		ID        int      `json:"id"`
		Name      string   `json:"name"`
		Wood      float64  `json:"wood"`
		Stone     float64  `json:"stone"`
		Iron      float64  `json:"iron"`
		Pop       int      `json:"pop"`
		PopMax    int      `json:"pop_max"`
		StorageMax int   `json:"storage_max"`
		Buildings map[string]string `json:"buildings"`
	} `json:"village"`
}

// Extractor provides methods for parsing HTML.
var Extractor = &extractor{}

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
	doc.Find("a[href*='village=']").Each(func(i int, s *goquery.Selection) {
		href, _ := s.Attr("href")
		re := regexp.MustCompile(`village=(\d+)`)
		matches := re.FindStringSubmatch(href)
		if len(matches) > 1 {
			villageIDs = append(villageIDs, matches[1])
		}
	})

	return villageIDs, nil
}
